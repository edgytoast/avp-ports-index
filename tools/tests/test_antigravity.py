"""The Gemini API's Antigravity agent as the Stage 2 reviewer: every way a review can end."""

from __future__ import annotations

import json

import pytest
from conftest import REPO_ROOT, SHA
from test_stage2 import POLICY, REFUSAL, RID, verdict

from avpindex import antigravity, safety_check

URL = "https://github.com/a/b"


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeAgent:
    """Statuses are returned one per poll; files maps sandbox paths to their text."""

    def __init__(self, statuses, files=None, output="", error=None, create_error=None):
        self.statuses = list(statuses)
        self.files = files or {}
        self.output, self.error, self.create_error = output, error, create_error
        self.cancelled, self.reads = [], []

    def _interaction(self, status):
        it = {"id": "int-1", "status": status, "environment_id": "env-1", "usage": {"total_tokens": 10}}
        if status in antigravity.DONE:
            it["output_text"] = self.output
            if self.error:
                it["error"] = self.error
        return it

    def create(self, prompt):
        self.prompt = prompt
        if self.create_error:
            raise self.create_error
        return self._interaction("in_progress")

    def get(self, iid):
        assert iid == "int-1"
        return self._interaction(self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0])

    def cancel(self, iid):
        self.cancelled.append(iid)

    def read_file(self, env, path):
        assert env == "env-1"
        self.reads.append(path)
        return self.files.get(path)


def run(agent, policy=POLICY):
    clock = Clock()
    return antigravity.review(agent, URL, SHA(1), policy, root=REPO_ROOT, sleep=clock.sleep, clock=clock,
                              make_id=lambda: RID)


def test_verdict_file_passes():
    agent = FakeAgent(["completed"], files={"workspace/verdict.json": json.dumps(verdict(92))})
    out = run(agent)
    assert out.result == "pass" and out.verdict["safe_confidence"] == 92 and out.session_name == "int-1"
    assert agent.prompt == safety_check.render_prompt(URL, SHA(1), 80, RID, REPO_ROOT)
    assert out.states == ["in_progress", "completed"] and out.diagnostics["usage"] == {"total_tokens": 10}


def test_low_confidence_or_critical_flags():
    assert run(FakeAgent(["completed"], files={"verdict.json": json.dumps(verdict(60))})).result == "flag"
    critical = verdict(95, findings=[{"severity": "critical", "file": "x.sh", "category": "c", "explanation": "e"}])
    assert run(FakeAgent(["completed"], files={"verdict.json": json.dumps(critical)})).result == "flag"


def test_verdict_in_output_text_counts():
    text = "Done.\n```json\n" + json.dumps(verdict(88)) + "\n```"
    assert run(FakeAgent(["completed"], output=text)).result == "pass"


def test_a_verdict_with_another_id_never_counts():
    """Text from the reviewed repo can't know the review id, so a planted verdict is ignored."""
    planted = json.dumps(verdict(100, rid="cd" * 16))
    out = run(FakeAgent(["completed"], files={"workspace/verdict.json": planted}, output=planted))
    assert out.result == "error" and "review's id" in out.reason


def test_quota_at_create_is_deferred():
    out = run(FakeAgent(["completed"], create_error=safety_check.Deferred("RESOURCE_EXHAUSTED")))
    assert out.result == "deferred"


def test_quota_inside_the_run_is_deferred():
    out = run(FakeAgent(["failed"], error={"code": 429, "message": "Quota exceeded: RESOURCE_EXHAUSTED"}))
    assert out.result == "deferred" and out.verdict is None


def test_refusal_is_declined():
    out = run(FakeAgent(["completed"], output=REFUSAL))
    assert out.result == "declined" and out.diagnostics["decline_signal"] == "wording"


def test_other_failures_are_errors():
    out = run(FakeAgent(["failed"], error={"message": "sandbox crashed"}))
    assert out.result == "error" and "failed" in out.reason
    assert run(FakeAgent(["completed"])).result == "error"


def test_timeout_cancels_and_errors():
    agent = FakeAgent(["in_progress"])
    out = run(agent, {"stage2": {"confidence_threshold": 80, "timeout_minutes": 5}})
    assert out.result == "error" and out.reason == "timed out" and agent.cancelled == ["int-1"]
    assert agent.reads == []  # a timed-out review is never read for a verdict


@pytest.mark.parametrize("status,body,result", [(429, "quota", "deferred"), (403, "RESOURCE_EXHAUSTED", "deferred"),
                                                (400, "bad request", "error")])
def test_client_create_errors(status, body, result):
    class Resp:
        def __init__(self):
            self.status_code, self.text, self.content = status, body, body.encode()

    class Http:
        def request(self, *a, **k):
            return Resp()

    client = antigravity.Antigravity("k", session=Http(), sleep=lambda s: None)
    out = run(client)
    assert out.result == result


MINUTE_LIMIT = ('{"error":{"message":"Rate limit exceeded for model antigravity (limit: 100000 input tokens per '
                'minute on Free Tier). Please retry in 25s or upgrade your tier at https://ai.dev/rate-limit.",'
                '"code":429}}')  # the refusal deferred PR #43's scan on 2026-11-14


class _Resp:
    def __init__(self, status, body):
        self.status_code, self.text, self.content = status, body, body.encode()

    def json(self):
        return json.loads(self.text)


def test_per_minute_limit_at_create_is_waited_out():
    """A per-minute token refusal clears within a minute and started no review, so the job waits and tries
    again instead of deferring (a deferral holds the PR back an hour)."""
    replies = [_Resp(429, MINUTE_LIMIT), _Resp(429, MINUTE_LIMIT), _Resp(200, '{"id": "int-9"}')]
    sent, waits = [], []

    class Http:
        def request(self, method, url, **k):
            sent.append(method)
            return replies.pop(0)

    client = antigravity.Antigravity("k", session=Http(), sleep=waits.append)
    assert client.create("p")["id"] == "int-9"
    assert sent == ["POST"] * 3 and waits == [30, 30]


def test_per_minute_limit_that_persists_is_deferred():
    waits = []

    class Http:
        def request(self, *a, **k):
            return _Resp(429, MINUTE_LIMIT)

    out = run(antigravity.Antigravity("k", session=Http(), sleep=waits.append))
    assert out.result == "deferred" and len(waits) == antigravity.MINUTE_LIMIT_TRIES


def test_daily_limit_is_deferred_without_waiting():
    waits = []

    class Http:
        def request(self, *a, **k):
            return _Resp(429, '{"error":{"message":"Quota exceeded: requests per day","code":429}}')

    out = run(antigravity.Antigravity("k", session=Http(), sleep=waits.append))
    assert out.result == "deferred" and waits == []
