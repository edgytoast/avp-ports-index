"""Stage 2 security review through Google's Jules agent (spec §6.2).

A repoless session is created with the public review prompt; the poller waits for a terminal
state, nudges once if the session stops to ask something, and reads verdict.json from the
session's change set or, failing that, from the single fenced JSON block in its last message.

API: https://jules.googleapis.com/v1alpha (sessions, sessions.activities, :sendMessage,
:approvePlan), authenticated with the x-goog-api-key header.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import jinja2
import jsonschema
import requests

from . import store

API = "https://jules.googleapis.com/v1alpha"
DONE_STATES = {"COMPLETED", "FAILED"}
STOPPED_STATES = {"AWAITING_USER_FEEDBACK", "AWAITING_PLAN_APPROVAL", "PAUSED"}
NUDGE = "Please continue without questions and write verdict.json as instructed."
POLL_SECONDS = 30


class Deferred(Exception):
    """Jules refused the session for quota or rate limits."""


class JulesError(Exception):
    pass


@dataclass
class Outcome:
    result: str                       # pass | flag | error | deferred
    verdict: dict | None = None
    session_url: str | None = None
    session_name: str | None = None
    minutes: float = 0.0
    reason: str = ""
    states: list = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"result": self.result, "verdict": self.verdict, "session_url": self.session_url,
                "session_name": self.session_name, "minutes": round(self.minutes, 1),
                "reason": self.reason, "states": self.states, "diagnostics": self.diagnostics}


class Jules:
    def __init__(self, api_key: str, session: requests.Session | None = None, api: str = API):
        self.api = api
        self.http = session or requests.Session()
        self.headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    def _call(self, method: str, path: str, body: dict | None = None, params: dict | None = None,
              *, defer: bool = False) -> dict:
        """One API call. Only session creation turns a quota refusal into Deferred; once a session
        exists, rate limits are waited out, since deferring would start a second task."""
        for attempt in range(6):
            resp = self.http.request(method, f"{self.api}/{path}", json=body, params=params,
                                     headers=self.headers, timeout=60)
            limited = resp.status_code == 429 or (resp.status_code == 403 and _quota(resp))
            if limited and defer:
                raise Deferred(resp.text[:300])
            if (limited or resp.status_code >= 500) and attempt < 5:
                time.sleep(15 * (attempt + 1))
                continue
            if resp.status_code >= 400:
                raise JulesError(f"{method} {path}: {resp.status_code} {resp.text[:300]}")
            return resp.json() if resp.content else {}
        raise JulesError(f"{method} {path}: repeated errors")

    def create_session(self, prompt: str, title: str) -> dict:
        return self._call("POST", "sessions", {"prompt": prompt, "title": title, "requirePlanApproval": False},
                          defer=True)

    def get_session(self, name: str) -> dict:
        return self._call("GET", name)

    def list_sessions(self, page_size: int = 5) -> dict:
        return self._call("GET", "sessions", params={"pageSize": page_size})

    def activities(self, name: str) -> list[dict]:
        out, token = [], None
        while True:
            params = {"pageSize": 100}
            if token:
                params["pageToken"] = token
            data = self._call("GET", f"{name}/activities", params=params)
            out.extend(data.get("activities") or [])
            token = data.get("nextPageToken")
            if not token:
                return out

    def send_message(self, name: str, text: str) -> None:
        self._call("POST", f"{name}:sendMessage", {"prompt": text})

    def approve_plan(self, name: str) -> None:
        self._call("POST", f"{name}:approvePlan", {})


def _quota(resp: requests.Response) -> bool:
    text = resp.text.lower()
    return "resource_exhausted" in text or "quota" in text


# --- verdicts ---------------------------------------------------------------------------

def verdict_schema(root: Path | None = None) -> dict:
    return store.load_json(".github/jules/verdict.schema.json", root)


def render_prompt(repo_url: str, sha: str, threshold: int, root: Path | None = None) -> str:
    root = root or store.ROOT
    template = (root / ".github/jules/security-review.md").read_text(encoding="utf-8")
    schema = json.dumps(verdict_schema(root), indent=2)
    return jinja2.Environment(undefined=jinja2.StrictUndefined).from_string(template).render(
        repo_url=repo_url, sha=sha, threshold=threshold, schema=schema)


def _patch_files(patch: str) -> dict[str, str]:
    """Added lines per file in a unified diff."""
    files: dict[str, list[str]] = {}
    current = None
    for line in patch.splitlines():
        if line.startswith("+++ "):
            current = line[4:].strip()
            current = current[2:] if current.startswith("b/") else current
            files.setdefault(current, [])
        elif line.startswith("--- ") or line.startswith("diff --git"):
            current = None if line.startswith("diff --git") else current
        elif current and line.startswith("+"):
            files[current].append(line[1:])
    return {path: "\n".join(lines) for path, lines in files.items()}


def _json_objects(text: str) -> list[dict]:
    """Every JSON object in a text that looks like a verdict, last first."""
    decoder = json.JSONDecoder()
    found, i = [], 0
    while True:
        i = text.find("{", i)
        if i < 0:
            break
        try:
            obj, end = decoder.raw_decode(text, i)
        except ValueError:
            i += 1
            continue
        if isinstance(obj, dict) and "safe_confidence" in obj:
            found.append(obj)
            i = end
        else:
            i += 1
    return list(reversed(found))


def verdict_texts(activities: list[dict]) -> list[str]:
    """Where a verdict can appear, most trustworthy and most recent first: verdict.json in the
    change set, then the agent's messages, terminal output (`cat verdict.json`) and progress notes."""
    patches, others = [], []
    for activity in reversed(activities):
        for artifact in activity.get("artifacts") or []:
            patch = ((artifact.get("changeSet") or {}).get("gitPatch") or {}).get("unidiffPatch")
            if patch:
                patches.extend(text for path, text in _patch_files(patch).items() if path.endswith("verdict.json"))
            output = (artifact.get("bashOutput") or {}).get("output")
            if output:
                others.append(output)
        message = (activity.get("agentMessaged") or {}).get("agentMessage")
        if message:
            others.append(message)
        progress = activity.get("progressUpdated") or {}
        others.extend(t for t in (progress.get("description"), progress.get("title")) if t)
    return patches + others


def find_verdict(activities: list[dict], schema: dict) -> tuple[dict | None, str]:
    """The most recent valid verdict anywhere in the session, or the first problem seen."""
    problem = "no verdict.json was found"
    validator = jsonschema.Draft202012Validator(schema)
    for text in verdict_texts(activities):
        candidates = _json_objects(text)
        if not candidates and text.strip().startswith("{"):
            problem = "verdict.json isn't valid JSON"
        for obj in candidates:
            errors = list(validator.iter_errors(obj))
            if not errors:
                return obj, ""
            problem = f"verdict.json doesn't match the schema: {errors[0].message[:200]}"
    return None, problem


def diagnostics(activities: list[dict]) -> dict:
    """What the session produced, for explaining a missing verdict without the API key."""
    kinds: dict[str, int] = {}
    artifacts: dict[str, int] = {}
    last_message = ""
    for activity in activities:
        for key in activity:
            if key not in ("name", "id", "createTime", "description", "originator", "artifacts"):
                kinds[key] = kinds.get(key, 0) + 1
        for artifact in activity.get("artifacts") or []:
            for key in artifact:
                artifacts[key] = artifacts.get(key, 0) + 1
        message = (activity.get("agentMessaged") or {}).get("agentMessage")
        if message:
            last_message = message
    return {"activity_kinds": kinds, "artifact_kinds": artifacts, "last_agent_message_tail": last_message[-600:]}


def check_verdict(text: str | None, schema: dict) -> tuple[dict | None, str]:
    if text is None:
        return None, "no verdict.json was found"
    try:
        data = json.loads(text)
    except ValueError as exc:
        return None, f"verdict.json isn't valid JSON ({exc.msg})"
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(data))
    if errors:
        return None, f"verdict.json doesn't match the schema: {errors[0].message[:200]}"
    return data, ""


def decide(verdict: dict, threshold: int) -> str:
    """pass only when confidence >= threshold, no steering attempt and no critical finding."""
    critical = any(f.get("severity") == "critical" for f in verdict.get("findings") or [])
    if verdict["safe_confidence"] >= threshold and not verdict["steering_attempt"] and not critical:
        return "pass"
    return "flag"


# --- one review -------------------------------------------------------------------------

def review(client: Jules, repo_url: str, sha: str, policy: dict, *, root: Path | None = None,
           sleep=time.sleep, clock=time.monotonic) -> Outcome:
    threshold = int(policy["stage2"]["confidence_threshold"])
    timeout = int(policy["stage2"]["jules_timeout_minutes"]) * 60
    schema = verdict_schema(root)
    owner_name = repo_url.removeprefix("https://github.com/")
    title = f"AVP index review: {owner_name}@{sha[:7]}"
    started = clock()
    try:
        session = client.create_session(render_prompt(repo_url, sha, threshold, root), title)
    except Deferred as exc:
        return Outcome("deferred", reason=str(exc)[:200])
    except (JulesError, requests.RequestException) as exc:
        return Outcome("error", reason=f"couldn't start the session: {exc}"[:300])
    name, url = session.get("name"), session.get("url")
    outcome = Outcome("error", session_url=url, session_name=name)
    nudged = fixed = False
    sent_at: float | None = None   # we sent a message and wait for the state to change
    sent_state = ""
    try:
        while True:
            if clock() - started > timeout:
                outcome.reason = "timed out"
                break
            sleep(POLL_SECONDS)
            state = client.get_session(name).get("state", "")
            if not outcome.states or outcome.states[-1] != state:
                outcome.states.append(state)
            if sent_at is not None:
                if state == sent_state:
                    # The session may have finished again within one poll: look for a verdict.
                    verdict, _ = find_verdict(client.activities(name), schema)
                    if verdict is not None:
                        outcome.result, outcome.verdict = decide(verdict, threshold), verdict
                        break
                    if clock() - sent_at > 600:
                        outcome.reason = "the session didn't respond to the follow-up message"
                        break
                    continue
                sent_at = None
            if state not in DONE_STATES | STOPPED_STATES:
                continue
            activities = client.activities(name)
            outcome.diagnostics = diagnostics(activities)
            verdict, problem = find_verdict(activities, schema)
            if verdict is not None:
                outcome.result, outcome.verdict = decide(verdict, threshold), verdict
                break
            if state == "FAILED":
                failed = [a for a in activities if a.get("sessionFailed")]
                outcome.reason = "session failed" + (f": {failed[-1]['sessionFailed'].get('reason', '')}" if failed else "")
                break
            if state in STOPPED_STATES:
                if nudged:
                    outcome.reason = "the session stopped twice"
                    break
                nudged = True
                if state == "AWAITING_PLAN_APPROVAL":
                    client.approve_plan(name)
                client.send_message(name, NUDGE)
            else:
                # COMPLETED without a usable verdict: ask once for a fix.
                if fixed:
                    outcome.reason = problem
                    break
                fixed = True
                client.send_message(name, f"{problem} in your messages: I can't read files from your workspace. "
                                          "Reply with the complete contents of verdict.json, matching the schema in the "
                                          "instructions, as a fenced JSON block in the message itself.")
            sent_at, sent_state = clock(), state
    except Deferred as exc:
        outcome.result, outcome.reason = "deferred", str(exc)[:200]
    except (JulesError, requests.RequestException) as exc:
        outcome.reason = f"API error: {exc}"[:300]
    outcome.minutes = (clock() - started) / 60
    return outcome
