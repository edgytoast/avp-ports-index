"""Stage 2 safety check through the Gemini API's managed Antigravity agent (spec §6.2).

Google turned Jules read-only on 2026-11-11 (shut down 2026-12-31); its successor for this job is the
Antigravity agent in the Gemini API's Interactions endpoint. Like Jules, it runs in a Google-hosted Linux
sandbox, clones the repository itself, and works in the background while we poll. The prompt, the verdict
schema, the random review id and the pass rule are the same as for Jules and live in safety_check.py.

One review:
1. Create a background interaction with the live (or candidate) prompt. A quota refusal (429, or a 403
   naming a quota) is `deferred`, so the dispatcher retries later instead of flagging.
2. Poll it until it is completed, failed, cancelled or incomplete, or the timeout passes (then cancel it).
3. Read verdict.json from the sandbox through the Environments files API, or failing that, a verdict printed
   in the agent's output text. Only a verdict carrying this review's id counts.
4. A run that ends on a quota error inside the agent is also `deferred`; a refusal in the output text is
   `declined`; anything else without a verdict is `error`. Nothing but a valid verdict can pass.

API: https://generativelanguage.googleapis.com/v1beta (interactions, environments/{id}/files),
authenticated with the x-goog-api-key header. Free-tier limits seen in AI Studio on 2026-11-13: 60
requests a minute, 100,000 tokens a minute and 100 requests a day for "Antigravity (Agents)". How many of
those one review uses isn't documented, so quota refusals are handled wherever they show up.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

from . import safety_check
from .safety_check import CANDIDATE, LIVE, PROMPTS, Deferred, Outcome  # noqa: F401  (re-exported for the CLI)

API = "https://generativelanguage.googleapis.com/v1beta"
AGENT = "antigravity-preview-09-2026"
POLL_SECONDS = 60          # polls are cheap, but keep them well under the per-minute request limit
MAX_TOTAL_TOKENS = 600_000  # uncached tokens one review may spend (the test review used about 163k)
DONE = {"completed", "failed", "cancelled", "incomplete"}
VERDICT_PATHS = ("workspace/verdict.json", "verdict.json")
MINUTE_LIMIT_TRIES = 4      # waits for a per-minute rate limit at create before giving up and deferring
MINUTE_LIMIT_MAX_WAIT = 90  # seconds per wait; the API asks for under a minute ("Please retry in 25s")


class AgentError(Exception):
    pass


def _minute_wait(resp: requests.Response) -> int | None:
    """Seconds to wait when a refusal is the per-minute rate limit (it clears in under a minute), or None
    for anything else, such as the daily request limit, which waiting in the job can't fix."""
    text = resp.text.lower()
    if "per minute" not in text:
        return None
    match = re.search(r"retry in ([0-9.]+)\s*s", text)
    return min(MINUTE_LIMIT_MAX_WAIT, int(float(match.group(1))) + 5) if match else 60


def _quota(resp: requests.Response) -> bool:
    text = resp.text.lower()
    return "resource_exhausted" in text or "quota" in text


class Antigravity:
    def __init__(self, api_key: str, session: requests.Session | None = None, api: str = API,
                 agent: str = AGENT, sleep=time.sleep):
        self.api, self.agent, self.sleep = api, agent, sleep
        self.http = session or requests.Session()
        self.headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    def _call(self, method: str, path: str, body: dict | None = None, params: dict | None = None,
              *, defer: bool = False, raw: bool = False):
        """One API call. Only creating the interaction turns a quota refusal into Deferred; once it runs,
        rate limits on polls are waited out, since deferring would start a second review."""
        for attempt in range(6):
            resp = self.http.request(method, f"{self.api}/{path}", json=body, params=params,
                                     headers=self.headers, timeout=120)
            limited = resp.status_code == 429 or (resp.status_code == 403 and _quota(resp))
            if limited and defer:
                # Waiting out the per-minute limit is safe here: the refused create started no review.
                wait = _minute_wait(resp)
                if wait is None or attempt >= MINUTE_LIMIT_TRIES:
                    raise Deferred(resp.text[:300])
                self.sleep(wait)
                continue
            if (limited or resp.status_code >= 500) and attempt < 5:
                self.sleep(15 * (attempt + 1))
                continue
            if raw:
                return resp
            if resp.status_code >= 400:
                raise AgentError(f"{method} {path}: {resp.status_code} {resp.text[:300]}")
            return resp.json() if resp.content else {}
        raise AgentError(f"{method} {path}: repeated errors")

    def create(self, prompt: str) -> dict:
        return self._call("POST", "interactions", {
            "agent": self.agent, "input": prompt, "environment": "remote", "background": True, "store": True,
            "agent_config": {"type": "antigravity", "max_total_tokens": MAX_TOTAL_TOKENS}}, defer=True)

    def get(self, interaction_id: str) -> dict:
        return self._call("GET", f"interactions/{interaction_id}")

    def cancel(self, interaction_id: str) -> None:
        self._call("POST", f"interactions/{interaction_id}:cancel", {})

    def read_file(self, environment_id: str, path: str) -> str | None:
        """A file from the interaction's sandbox, or None if it isn't there."""
        resp = self._call("GET", f"environments/{environment_id}/files/{path}", params={"alt": "media"}, raw=True)
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise AgentError(f"GET file {path}: {resp.status_code} {resp.text[:300]}")
        return resp.content.decode("utf-8", "replace")


# --- reading the result ---------------------------------------------------------------------------

def output_text(interaction: dict) -> str:
    """Everything the agent said, in order (the API's convenience field, or the text outputs)."""
    if interaction.get("output_text"):
        return str(interaction["output_text"])
    texts = []
    for item in interaction.get("outputs") or []:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            texts.append(item["text"])
    return "\n".join(texts)


def find_verdict(texts: list[str | None], schema: dict, review_id: str) -> tuple[dict | None, str]:
    """The first valid verdict with this review's id, from verdict.json first and then the output text."""
    problem = ""
    for text in texts:
        if not text:
            continue
        data, issue = safety_check.check_verdict(text, schema)
        candidates = [data] if data is not None else safety_check._json_objects(text)
        if data is None and not candidates:
            problem = problem or issue
        for obj in candidates:
            checked, issue = safety_check.check_verdict(json.dumps(obj), schema)
            if checked is None:
                problem = problem or issue
            elif checked["review_id"] != review_id:
                problem = problem or "verdict.json doesn't carry this review's id"
            else:
                return checked, ""
    return None, problem or safety_check.NO_VERDICT


def _failure_text(interaction: dict) -> str:
    error = interaction.get("error")
    return json.dumps(error) if isinstance(error, (dict, list)) else str(error or "")


def _quota_failure(interaction: dict) -> bool:
    text = _failure_text(interaction).lower()
    return "resource_exhausted" in text or "quota" in text or "429" in text


# --- one review -----------------------------------------------------------------------------------

def review(client: Antigravity, repo_url: str, sha: str, policy: dict, *, root: Path | None = None,
           prompt: str = LIVE, sleep=time.sleep, clock=time.monotonic, make_id=safety_check.new_review_id) -> Outcome:
    threshold = int(policy["stage2"]["confidence_threshold"])
    timeout = int(policy["stage2"]["timeout_minutes"]) * 60
    schema = safety_check.verdict_schema(root)  # always the live schema, whichever prompt was shown
    review_id = make_id()
    started = clock()
    try:
        interaction = client.create(safety_check.render_prompt(repo_url, sha, threshold, review_id, root, prompt))
    except Deferred as exc:
        return Outcome("deferred", reason=str(exc)[:200])
    except (AgentError, requests.RequestException) as exc:
        return Outcome("error", reason=f"couldn't start the review: {exc}"[:300])
    iid = interaction.get("id") or interaction.get("name", "").rsplit("/", 1)[-1]
    outcome = Outcome("error", session_name=iid)
    env = interaction.get("environment_id")
    try:
        while True:
            status = str(interaction.get("status") or "")
            if status and (not outcome.states or outcome.states[-1] != status):
                outcome.states.append(status)
            if status in DONE:
                break
            if clock() - started > timeout:
                outcome.reason = "timed out"
                try:
                    client.cancel(iid)
                except (AgentError, requests.RequestException):
                    pass
                break
            sleep(POLL_SECONDS)
            interaction = client.get(iid)
            env = env or interaction.get("environment_id")
        said = output_text(interaction)
        outcome.diagnostics = {"usage": interaction.get("usage"), "output_tail": said[-600:],
                               "error": _failure_text(interaction)[:600]}
        if outcome.reason == "timed out":
            pass
        elif status == "failed" and _quota_failure(interaction):
            outcome.result, outcome.reason = "deferred", f"quota: {_failure_text(interaction)}"[:200]
        else:
            files = []
            if env:
                for path in VERDICT_PATHS:
                    text = client.read_file(env, path)
                    if text is not None:
                        files.append(text)
                        break
            verdict, problem = find_verdict([*files, said], schema, review_id)
            if verdict is not None:
                outcome.result, outcome.verdict = safety_check.decide(verdict, threshold), verdict
            elif safety_check.looks_like_refusal(said, review_id):
                outcome.result, outcome.reason = "declined", safety_check.excerpt(said)
                outcome.diagnostics["decline_signal"] = "wording"
            elif status != "completed":
                outcome.reason = f"the review ended {status or 'without a status'}: {_failure_text(interaction)}"[:300]
            else:
                outcome.reason = problem
    except Deferred as exc:
        outcome.result, outcome.reason = "deferred", str(exc)[:200]
    except (AgentError, requests.RequestException) as exc:
        outcome.result, outcome.reason = "error", f"API error: {exc}"[:300]
    outcome.minutes = (clock() - started) / 60
    return outcome
