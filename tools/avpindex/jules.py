"""Stage 2 security review through Google's Jules agent (spec §6.2).

A repoless session is created with the public review prompt; the poller waits for a terminal
state, nudges once if the session stops to ask something, and reads verdict.json from the
session's change set or, failing that, from any message, terminal output or progress note
(decision 39), most recent first.
Only a verdict carrying the session's random review id counts: text from the reviewed repo (a file
Jules prints, say) can't know it, so it can't stand in for the verdict.
If Jules refuses the review, the poller restates the request once; a second refusal is the result
`declined`, which never passes (decision 63). Calibration can render the candidate prompt in
.github/jules/candidate/ instead of the live one; verdicts are always checked against the live schema.

API: https://jules.googleapis.com/v1alpha (sessions, sessions.activities, :sendMessage,
:approvePlan), authenticated with the x-goog-api-key header.
"""

from __future__ import annotations

import json
import re
import secrets
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
REPLY_SECONDS = 600     # how long a follow-up message may go unanswered
EXCERPT_CHARS = 400     # how much of a refusal is kept as the reason
NO_VERDICT = "no verdict.json was found"

# The prompts (decision 63). Live reviews always use LIVE; calibration may render CANDIDATE, whose wording
# differs but whose schema must be structurally identical (only descriptions differ; a test checks it).
LIVE, CANDIDATE = "live", "candidate"
PROMPTS = {LIVE: ".github/jules", CANDIDATE: ".github/jules/candidate"}
SESSION_TITLES = {LIVE: "AVP index review", CANDIDATE: "AVP index safety check"}


class Deferred(Exception):
    """Jules refused the session for quota or rate limits."""


class JulesError(Exception):
    pass


@dataclass
class Outcome:
    result: str                       # pass | flag | error | deferred | declined
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

def verdict_schema(root: Path | None = None, prompt: str = LIVE) -> dict:
    """The verdict schema shown with a prompt. Verdicts are only ever validated against the live one."""
    return store.load_json(f"{PROMPTS[prompt]}/verdict.schema.json", root)


def new_review_id() -> str:
    return secrets.token_hex(16)


def render_prompt(repo_url: str, sha: str, threshold: int, review_id: str, root: Path | None = None,
                  prompt: str = LIVE) -> str:
    root = root or store.ROOT
    template = (root / PROMPTS[prompt] / "security-review.md").read_text(encoding="utf-8")
    schema = json.dumps(verdict_schema(root, prompt), indent=2)
    return jinja2.Environment(undefined=jinja2.StrictUndefined).from_string(template).render(
        repo_url=repo_url, sha=sha, threshold=threshold, review_id=review_id, schema=schema)


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


def find_verdict(activities: list[dict], schema: dict, review_id: str) -> tuple[dict | None, str]:
    """The most recent valid verdict carrying this session's review id, or the first problem seen.
    A valid verdict with any other id didn't come from this session's answer and is skipped."""
    problem = ""
    validator = jsonschema.Draft202012Validator(schema)
    for text in verdict_texts(activities):
        candidates = _json_objects(text)
        if not candidates and text.strip().startswith("{"):
            problem = problem or "verdict.json isn't valid JSON"
        for obj in candidates:
            errors = list(validator.iter_errors(obj))
            if errors:
                problem = problem or f"verdict.json doesn't match the schema: {errors[0].message[:200]}"
            elif obj["review_id"] != review_id:
                problem = problem or "verdict.json doesn't carry this review's id"
            else:
                return obj, ""
    return None, problem or NO_VERDICT


def foreign_verdicts(activities: list[dict], schema: dict, review_id: str) -> int:
    """Valid verdicts in the session that carry another id: planted by the repo, or Jules mistyping the id."""
    validator = jsonschema.Draft202012Validator(schema)
    return sum(1 for text in verdict_texts(activities) for obj in _json_objects(text)
               if validator.is_valid(obj) and obj["review_id"] != review_id)


def agent_messages(activities: list[dict]) -> list[str]:
    """The agent's messages, oldest first."""
    return [m for m in ((a.get("agentMessaged") or {}).get("agentMessage") for a in activities) if m]


# --- declines -----------------------------------------------------------------------------
# Jules sometimes refuses a review outright, intermittently (2026-10-10: "I am programmed to strictly
# refuse any requests to perform security reviews, ..."). Two signals mark a refusal, both kept here:
#  1. Wording: any agent message since our last follow-up in one of the first-person refusal shapes in
#     REFUSAL_PATTERNS ("I can't help with that", "I'm not able to provide a security assessment of this
#     repository", "my guidelines prevent me ..."). What's refused must be the task itself (the review,
#     the request, the repository, "this" or "that") or nothing named: "I decline to rate the binary as
#     safe" or "I must refuse to run the install script" are part of reviewing, not refusals. Third-person
#     mentions ("the server will refuse any request") don't match, and a message carrying a verdict for this
#     review is never a refusal (that is a format problem; a verdict with another id doesn't count).
#  2. No work: the session finished with no verdict, no attempt at one (nothing verdict-shaped, with any
#     id, and no other problem than "not found"), and no sign it touched the repository (no command output,
#     no change set, no progress note about the clone), whatever it said. That command output shows in
#     working sessions is the premise; calibration runs' diagnostics (artifact_kinds, decline_signal) check it.
# Text is lowercased and contractions spelled out first (_plain), so "I can't" and "I cannot" read the same.

_END = (r"(?:,? (?:again|once more|as well|too|either|here|now|at all|for you|i am afraid))?"
        r"(?=[.!?,;:\u2026]|$)")  # the phrase ends here (give or take "again"): nothing named is refused
_NOT = (r"(?:cannot|will not|must not|do not|would rather not|am not able to|am unable to|am not permitted to|"
        r"am not allowed to|am not in a position to|am not going to|am not designed to|am not built to|"
        r"am not programmed to)(?: be able to)?")
_TASK = (r"(?:perform|carry out|conduct|do|complete|undertake|provide|evaluate|review|analy[sz]e|scan|assess|"
         r"audit|inspect|examine|check|look into|proceed with|continue with|engage in|help with|assist with|"
         r"take on|handle|process)")
_TASKING = (r"(?:performing|carrying out|conducting|doing|completing|undertaking|providing|evaluating|reviewing|"
            r"analy[sz]ing|scanning|assessing|auditing|inspecting|examining|checking|looking into|proceeding with|"
            r"continuing with|engaging in|helping with|assisting with|taking on|handling|processing)")
_WORK = (r"(?:requests?|tasks?|reviews?|scans?|scanning|analys[ie]s|assessments?|evaluations?|audits?|auditing|"
         r"inspections?|checks?|repository|repositories|repos?|codebases?|code base)")
_DET = r"(?:this|that|the|these|those|such|your|any|a|an|its)"
_WORDS = r"(?: (?!(?:of|in|on|from|for|with|at|by|to|and|or|but)\b)[\w-]+){0,2}"  # up to two adjectives
_AFTER = (r"(?!'| by\b| without\b| beyond\b| except\b| other than\b| until\b| unless\b| in depth\b| fully\b|"
          r" further\b| directly\b| yet\b| in full\b| line by line\b| individually\b| separately\b|"
          r" to (?:run|build|install|execute|compile|launch|open|download)\b)")  # "the request to run the build"
# What's refused: the task itself, never a file, script, binary or action within it.
_OBJECT = (rf"(?:{_DET}{_WORDS}(?: (?:kind|type|sort)s? of{_WORDS})? {_WORK}\b{_AFTER}"
           rf"|(?:security|vulnerability|malware|safety)(?: [\w-]+)? {_WORK}\b{_AFTER}"
           rf"|(?:[\w-]+ ){{0,3}}(?:repositories|repos|codebases)\b{_AFTER}"
           rf"|(?:{_DET} )?(?:[\w-]+ )?(?:repositories|repos|codebases|code) for (?:malware|vulnerabilities|security)\b"
           rf"|requests? (?:like|such as) (?:this|that)(?: one)?{_END}"
           rf"|requests? (?:involving|about|regarding|related to|that involve)\b[^.!?]{{0,80}}?"
           rf"\b(?:malware|security|vulnerabilit\w*|safety)\b"
           rf"|(?:this|that) one{_END}"
           rf"|(?:the )?security of {_DET}(?: [\w-]+)? (?:repository|repo|codebase|project|target)\b{_AFTER}"
           rf"|(?:this|that){_END})")
_REFUSED = rf"(?: {_OBJECT}|{_END})"

REFUSAL_PATTERNS = tuple(re.compile(p) for p in (
    rf"\bi {_NOT} (?:help|assist|comply)(?: you)?(?: with)?{_REFUSED}",       # I can't help with that
    rf"\bi {_NOT} fulfil+{_REFUSED}",                                          # I cannot fulfill your request
    rf"\bi {_NOT} (?:help|assist)(?: you)? (?:to )?{_TASK} {_OBJECT}",        # I cannot help you analyze this repo
    rf"\bi {_NOT} (?:help|assist)(?: you)? with {_TASKING} {_OBJECT}",        # I can't help with analyzing code for ...
    rf"\bi {_NOT} {_TASK} {_OBJECT}",                     # I'm unable to provide a security assessment of this repo
    rf"(?<!which )(?<!that )\bi {_NOT} {_TASK}{_END}",                         # I'd rather not perform...
    rf"\bi {_NOT} do (?:it|so){_END}",                                         # I can't do it.
    (rf"\bi {_NOT} (?:proceed|continue)(?:{_END}| (?:any )?further\b| with (?:this|that|it|the request|"
     r"the task|your request)\b)"),                                            # I cannot proceed.
    (rf"\bi (?:am not comfortable|do not feel comfortable|will not be|am not going to be|would rather not be)"
     rf"(?: with)? {_TASKING}(?: {_OBJECT}|{_END})"),                          # I won't be doing this review
    (r"\bi (?:must |have to |need to |will have to |am going to have to |"
     r"(?:am|have been|was) (?:programmed|designed|built|trained|required) to )?"
     rf"(?:strictly |respectfully |politely |firmly )?(?:refuse|decline)"
     rf"(?:{_REFUSED}| to {_TASK}(?: {_OBJECT}|{_END})| to do (?:it|so){_END})"),  # I must decline this request
    (rf"\bi (?:am|have been|was) (?:programmed|designed|built|trained) (?:not to|never to|to never) "
     rf"{_TASK}(?: {_OBJECT}|{_END})"),                                        # I am programmed not to perform ...
    (r"\b(?:against|violates?|outside(?: of)?) my (?:guidelines|policies|policy|programming|principles|rules|"
     r"safety guidelines|usage policies|capabilities|scope|remit)\b"),       # this goes against my guidelines
    (r"\bmy (?:guidelines|policies|policy|programming|principles|rules|safety guidelines) "
     r"(?:prevent|prohibit|forbid|bar|restrict|stop|do not allow|does not allow|do not permit|does not permit|"
     rf"will not allow|will not let|do not let|does not let) me(?: from {_TASKING}(?: {_OBJECT}|{_END})|"
     rf" to {_TASK}(?: {_OBJECT}|{_END})| to do (?:it|so){_END}|{_END})"),  # my guidelines prevent me from ...
    (r"\bfalls? outside (?:of )?(?:what i (?:can|am able to|am allowed to|am permitted to)\b|my\b|"
     r"the (?:scope|bounds|limits) of what i\b)"),                           # this falls outside what I can do
    r"\boutside (?:of )?the scope of what i (?:can|am able to|am allowed to|am permitted to)\b",
    (r"\bbeyond (?:what i (?:am allowed to|am permitted to|am able to|can) (?:do|help with|assist with)\b|"
     r"my (?:capabilities|abilities|scope|remit|guidelines)\b)"),           # beyond what I'm allowed to do
    (r"\bnot something i (?:can|am able to|am allowed to|am permitted to|will) (?:help|assist|do|provide|perform|"
     r"support|undertake|carry out|engage in)\b"),                           # that's not something I can help with
    (r"\bi (?:can|am able to) only (?:help|assist) with\b[^.!?]*?\bnot\b[^.!?]*?\b(?:reviews?|scans?|scanning|"
     r"analys[ie]s|assessments?|audits?|auditing)\b"),                       # I can only help with coding, not ...
    (rf"\bi {_NOT} (?:assess|evaluate|determine|judge|say|tell|check|verify|confirm) whether (?:this|the|that|your) "
     rf"(?:code|repository|repo|project|codebase) is (?:malicious|safe|harmful|secure|dangerous|benign){_END}"),
))
_CONTRACTIONS = (("can't", "cannot"), ("can not", "cannot"), ("won't", "will not"), ("i'm", "i am"),
                 ("i've", "i have"), ("i'll", "i will"), ("i'd", "i would"), ("n't", " not"))
WORK_HINTS = ("clone", "cloning", "/tmp/target")  # progress notes that show the session got to the repository


def _plain(text: str) -> str:
    text = re.sub(r"[*_`]", "", text)  # Markdown emphasis and code marks: "**I can't help with that**"
    text = " ".join(text.replace("\u2019", "'").replace("\u2018", "'").lower().split())
    for short, full in _CONTRACTIONS:
        text = text.replace(short, full)
    return text


def looks_like_refusal(text: str | None, review_id: str | None = None) -> bool:
    """Whether an agent message refuses the review (signal 1 above). A message holding a verdict-shaped
    object with this review's id is an attempt at the verdict, not a refusal."""
    if not text:
        return False
    if review_id and any(obj.get("review_id") == review_id for obj in _json_objects(text)):
        return False
    plain = _plain(text)
    return any(p.search(plain) for p in REFUSAL_PATTERNS)


def worked_on_repo(activities: list[dict], repo_url: str, problem: str = NO_VERDICT) -> bool:
    """Signal 2's evidence of work: an attempt at a verdict (anything verdict-shaped, with any id, or any
    problem with one other than not finding it), command output, a change set, or a progress note about
    the clone or the repo."""
    if problem != NO_VERDICT or any(_json_objects(text) for text in verdict_texts(activities)):
        return True
    name = repo_url.removeprefix("https://github.com/").lower()
    for activity in activities:
        for artifact in activity.get("artifacts") or []:
            if artifact.get("bashOutput") or artifact.get("changeSet"):
                return True
        progress = activity.get("progressUpdated") or {}
        text = " ".join(str(progress.get(key) or "") for key in ("title", "description")).lower()
        if any(hint in text for hint in (*WORK_HINTS, name)):
            return True
    return False


def restate_message(review_id: str, problem: str = NO_VERDICT) -> str:
    """The one follow-up sent when Jules refuses: what the check is, plainly; the instructions are unchanged.
    If Jules had already tried a verdict, the problem with it is named too, as the format fix would."""
    fix = f" The verdict so far has a problem to fix: {problem}." if problem != NO_VERDICT else ""
    return ("To explain the request: this is the AVP Ports Index's routine safety check, run before the index "
            "recommends an open-source repository to the public, and requested by the index's owner. The "
            "instructions are public. Nothing is attacked, built or run: the task is to read the repository's "
            "files and describe what they do, as the instructions above set out. Please continue with the "
            f"instructions above and write verdict.json with review_id {review_id}, matching the schema in the "
            f"instructions, then print its contents as a fenced JSON block in your message.{fix}")


def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "\u2026"


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
        return None, NO_VERDICT
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

def review(client: Jules, repo_url: str, sha: str, policy: dict, *, root: Path | None = None, prompt: str = LIVE,
           sleep=time.sleep, clock=time.monotonic, make_id=new_review_id) -> Outcome:
    threshold = int(policy["stage2"]["confidence_threshold"])
    timeout = int(policy["stage2"]["jules_timeout_minutes"]) * 60
    schema = verdict_schema(root)  # always the live schema, whichever prompt was shown
    owner_name = repo_url.removeprefix("https://github.com/")
    title = f"{SESSION_TITLES[prompt]}: {owner_name}@{sha[:7]}"
    review_id = make_id()
    started = clock()
    try:
        session = client.create_session(render_prompt(repo_url, sha, threshold, review_id, root, prompt), title)
    except Deferred as exc:
        return Outcome("deferred", reason=str(exc)[:200])
    except (JulesError, requests.RequestException) as exc:
        return Outcome("error", reason=f"couldn't start the session: {exc}"[:300])
    name, url = session.get("name"), session.get("url")
    outcome = Outcome("error", session_url=url, session_name=name)
    follow_ups: list[str] = []     # nudge, restate, fix: each sent at most once
    sent_at: float | None = None   # we sent a message and wait for the state to change
    sent_state = ""
    seen = 0                       # agent messages in the session when we sent it: only later ones are judged
    settled = -1                   # while waiting: the message count at the previous poll
    refusal = ""                   # what the restatement answered

    def declined(text: str, signal: str) -> None:
        outcome.result, outcome.reason = "declined", excerpt(text)
        outcome.diagnostics["decline_signal"] = signal

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
                    # The session may have answered within one poll, so its state looks unchanged.
                    activities = client.activities(name)
                    verdict, _ = find_verdict(activities, schema, review_id)
                    if verdict is not None:
                        outcome.result, outcome.verdict = decide(verdict, threshold), verdict
                        break
                    count = len(agent_messages(activities))
                    late = clock() - sent_at > REPLY_SECONDS
                    if count > seen and (count == settled or late):
                        pass  # it answered and has stopped writing: judge the answer now, below
                    elif late:
                        if follow_ups[-1] == "restate":
                            declined(refusal, outcome.diagnostics.get("decline_signal", "wording"))
                        else:
                            outcome.reason = "the session didn't respond to the follow-up message"
                        break
                    else:
                        settled = count if count > seen else -1
                        continue
                sent_at, settled = None, -1
            if state not in DONE_STATES | STOPPED_STATES:
                continue
            activities = client.activities(name)
            outcome.diagnostics = diagnostics(activities)
            outcome.diagnostics["foreign_verdicts"] = foreign_verdicts(activities, schema, review_id)
            verdict, problem = find_verdict(activities, schema, review_id)
            if verdict is not None:
                outcome.result, outcome.verdict = decide(verdict, threshold), verdict
                break
            said = agent_messages(activities)
            # Only what Jules said since our last follow-up counts, so an old refusal isn't judged twice.
            found = next((text for text in reversed(said[seen:]) if looks_like_refusal(text, review_id)), None)
            signal = "wording" if found is not None else ""
            if found is None and state == "COMPLETED" and not worked_on_repo(activities, repo_url, problem):
                found, signal = (said[-1] if said else ""), "no work"
            if state == "FAILED":
                if signal == "wording":
                    declined(found, signal)
                else:
                    failed = [a for a in activities if a.get("sessionFailed")]
                    outcome.reason = "session failed" + (
                        f": {failed[-1]['sessionFailed'].get('reason', '')}" if failed else "")
                break
            if signal:
                # Jules refused the review: say plainly what it is, once. A second refusal is `declined`.
                if "restate" in follow_ups:
                    declined(found, signal)
                    break
                follow_ups.append("restate")
                refusal = found
                outcome.diagnostics["decline_signal"] = signal
                if state == "AWAITING_PLAN_APPROVAL":
                    client.approve_plan(name)
                client.send_message(name, restate_message(review_id, problem))
            elif state in STOPPED_STATES:
                if "nudge" in follow_ups:
                    outcome.reason = "the session stopped twice"
                    break
                follow_ups.append("nudge")
                if state == "AWAITING_PLAN_APPROVAL":
                    client.approve_plan(name)
                client.send_message(name, NUDGE)
            else:
                # COMPLETED without a usable verdict: ask once for a fix.
                if "fix" in follow_ups:
                    outcome.reason = problem
                    break
                follow_ups.append("fix")
                client.send_message(name, f"{problem} in your messages: I can't read files from your workspace. "
                                          f"Reply with the complete contents of verdict.json, with review_id {review_id}, "
                                          "matching the schema in the instructions, as a fenced JSON block in the message itself.")
            sent_at, sent_state, seen = clock(), state, len(said)
    except Deferred as exc:
        outcome.result, outcome.reason = "deferred", str(exc)[:200]
    except (JulesError, requests.RequestException) as exc:
        outcome.result, outcome.reason = "error", f"API error: {exc}"[:300]
    if outcome.diagnostics or follow_ups:
        outcome.diagnostics["follow_ups"] = follow_ups  # which follow-up messages were sent, in order
    outcome.minutes = (clock() - started) / 60
    return outcome
