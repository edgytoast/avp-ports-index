"""Delisting a port now, with a reason (decision 70): kill-switch `delist` moves a listed entry to the
Unavailable ports record with a fixed reason, and the README and feed show it with no links."""
from __future__ import annotations

import json

import pytest
from avpindex import generate, health, killswitch, lifecycle, queue, report, store
from conftest import SHA, git, list_entry


@pytest.fixture
def event(tmp_path_factory, monkeypatch):
    folder = tmp_path_factory.mktemp("event")

    def set_event(payload: dict, name: str, **env):
        path = folder / "event.json"
        path.write_text(json.dumps(payload))
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(path))
        monkeypatch.setenv("GITHUB_EVENT_NAME", name)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
    return set_event


def ks(rt, event, entry_id, action, reason=None):
    env = {"INPUT_ENTRY_ID": entry_id, "INPUT_ACTION": action, "INPUT_BLOCKLIST": "false"}
    if reason is not None:
        env["INPUT_REASON"] = reason
    event({}, "workflow_dispatch", **env)
    return killswitch.run(rt)


def test_delist_moves_a_listed_entry_to_the_record_with_its_reason(rt, gh, event):
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    state = store.State.load(rt.root)
    state.health["good"].update(failing_since="2026-11-19T06:30:50Z", health="issues", failures=["S1-06"])
    state.save()
    ks(rt, event, "good", "delist", "legal-451")
    state = store.State.load(rt.root)
    record = state.lifecycle["good"]
    assert record["status"] == "delisted-decay" and record["by"] == "kill-switch" and record["reason"] == "legal-451"
    assert (rt.root / "entries" / "good.yaml").exists()  # the trace keeps its file; nothing is blocklisted
    out = generate.generate(rt.root, rt.repo)  # also validates the feed against its schema
    feed = json.loads(out["feed/v1/index.json"])
    assert feed["schema_version"] == "1.8.0" and not feed["entries"]
    (u,) = feed["unavailable"]
    assert u["reason"] == "legal-451" and u["unavailable_since"] == "2026-11-19T06:30:50Z"
    section = out["README.md"].split("## Unavailable ports", 1)[1]
    assert lifecycle.DELIST_REASONS["legal-451"] in section and "| 2026-11-19 |" in section
    assert "](" not in section.split("##", 1)[0]  # no links on the record
    # A notice turns up: only the reason changes.
    ks(rt, event, "good", "delist", "legal-notice")
    record = store.State.load(rt.root).lifecycle["good"]
    assert record["status"] == "delisted-decay" and record["reason"] == "legal-notice"


def test_delist_needs_a_listed_entry_and_a_known_reason(rt, gh, event):
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    assert "needs one of the listed reasons" in ks(rt, event, "good", "delist", "because I said so")
    assert "needs one of the listed reasons" in ks(rt, event, "good", "delist", "health")  # the health check's own
    assert store.State.load(rt.root).lifecycle["good"]["status"] == "listed"
    ks(rt, event, "good", "pull")
    assert "delist works on listed entries" in ks(rt, event, "good", "delist", "repo-gone")


def test_relisting_drops_the_reason_and_health_delisting_records_one(rt, gh):
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    state = store.State.load(rt.root)
    lifecycle.transition(state, "good", "delisted-decay", "kill-switch", reason="repo-gone")
    lifecycle.transition(state, "good", "listed", "merge")
    assert "reason" not in state.lifecycle["good"]
    lifecycle.transition(state, "good", "delisted-decay", "health", reason="health")
    state.save()
    (u,) = json.loads(generate.generate(rt.root, rt.repo)["feed/v1/index.json"])["unavailable"]
    assert u["reason"] == "health"


def test_reason_is_a_dispatch_choice_matching_the_code():
    import yaml
    from conftest import REPO_ROOT
    flow = yaml.safe_load((REPO_ROOT / ".github/workflows/kill-switch.yml").read_text())
    inputs = flow[True]["workflow_dispatch"]["inputs"]
    assert inputs["action"]["options"] == list(killswitch.ACTIONS)
    assert inputs["reason"]["options"] == list(lifecycle.CURATOR_REASONS)
    schema = json.loads((REPO_ROOT / "schema/state.schema.json").read_text())
    reasons = schema["$defs"]["lifecycle"]["additionalProperties"]["properties"]["reason"]["enum"]
    assert reasons == list(lifecycle.DELIST_REASONS)


@pytest.mark.parametrize("by", ["stage2", "merge"])
def test_only_health_and_the_curator_can_delist(by):
    assert not lifecycle.is_legal("listed", "delisted-decay", by)


# --- the daily health check on HTTP 451, and ports whose repo comes back ----------------------------------------------

def setup_listed(rt, gh):
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    git(rt.root, "add", "-A")
    git(rt.root, "commit", "-qm", "listed")
    return repo


def blocked(gh, full="trevorbilt-bot/good"):
    """GitHub answers 451 for the repo: its metadata is gone, its status says why."""
    gh.legal_blocked.add(full)
    return gh.repos.pop(full)


def test_health_check_delists_a_451_repo_with_reason_legal_451(rt, gh, monkeypatch):
    setup_listed(rt, gh)
    blocked(gh)
    monkeypatch.setenv("AVP_NOW", "2026-11-25T06:17:00Z")
    health.run(rt)
    state = store.State.load(rt.root)
    record = state.lifecycle["good"]
    assert (record["status"], record["by"], record["reason"]) == ("delisted-decay", "health", "legal-451")
    assert (rt.root / "entries" / "good.yaml").exists() and not gh.external_issues  # no outreach, no grace window
    (u,) = json.loads(generate.generate(rt.root, rt.repo)["feed/v1/index.json"])["unavailable"]
    assert u["reason"] == "legal-451"


def test_a_plain_404_still_goes_through_decay_not_straight_to_the_record(rt, gh, monkeypatch):
    setup_listed(rt, gh)
    gh.repos.pop("trevorbilt-bot/good")
    monkeypatch.setenv("AVP_NOW", "2026-11-25T06:17:00Z")
    health.run(rt)
    state = store.State.load(rt.root)
    assert state.lifecycle["good"]["status"] == "listed" and state.health["good"]["failures"] == ["S1-06"]


def test_a_repo_back_at_its_reviewed_commit_is_listed_again(rt, gh, monkeypatch):
    setup_listed(rt, gh)
    repo = blocked(gh)
    monkeypatch.setenv("AVP_NOW", "2026-11-25T06:17:00Z")
    health.run(rt)
    monkeypatch.setenv("AVP_NOW", "2026-11-26T06:17:00Z")
    health.run(rt)  # still 451: stays on the record
    assert store.State.load(rt.root).lifecycle["good"]["status"] == "delisted-decay"
    gh.legal_blocked.clear()
    gh.repos["trevorbilt-bot/good"] = repo
    monkeypatch.setenv("AVP_NOW", "2026-11-27T06:17:00Z")
    health.run(rt)
    state = store.State.load(rt.root)
    record = state.lifecycle["good"]
    assert (record["status"], record["by"]) == ("listed", "health") and "reason" not in record
    assert state.health["good"]["scanned_commit"] == SHA(11) and state.health["good"]["health"] == "ok"


def test_a_repo_back_with_new_commits_is_rescanned_then_listed_on_a_pass(rt, gh, monkeypatch):
    setup_listed(rt, gh)
    repo = blocked(gh)
    monkeypatch.setenv("AVP_NOW", "2026-11-25T06:17:00Z")
    health.run(rt)
    gh.legal_blocked.clear()
    gh.repos["trevorbilt-bot/good"] = repo
    gh.move_head("trevorbilt-bot/good", SHA(12))
    monkeypatch.setenv("AVP_NOW", "2026-11-26T06:17:00Z")
    health.run(rt)
    state = store.State.load(rt.root)
    assert state.lifecycle["good"]["status"] == "delisted-decay" and state.health["good"]["relist_pending"]
    assert queue.rescan_candidates(state, store.utcnow()) == ["good"]  # the dispatcher rescans it as usual
    inputs = report.Inputs(mode="rescan", pr=None, head_sha=None, linked_repo="trevorbilt-bot/good",
                           linked_commit=SHA(12), entry_id="good", repo_id=11, base_commit=SHA(11), counted=False)
    verdict = {"review_id": "ab" * 16, "safe_confidence": 90, "summary": "ok", "findings": [], "steering_attempt": False}
    assert report.run(rt, inputs, {"result": "pass", "verdict": verdict, "session_url": "u"})[0] == "pass"
    state = store.State.load(rt.root)
    assert (state.lifecycle["good"]["status"], state.lifecycle["good"]["by"]) == ("listed", "stage2")
    assert state.health["good"]["scanned_commit"] == SHA(12) and not state.health["good"]["relist_pending"]


def test_a_developer_request_is_never_relisted_by_the_health_check(rt, gh, event, monkeypatch):
    setup_listed(rt, gh)
    ks(rt, event, "good", "delist", "developer-request")
    monkeypatch.setenv("AVP_NOW", "2026-11-25T06:17:00Z")
    health.run(rt)
    assert store.State.load(rt.root).lifecycle["good"]["status"] == "delisted-decay"
