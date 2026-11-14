"""The Stage 2 safety check's verdict rules, shared by the agent runner (antigravity.py) and the report job.

The prompt and verdict schema live in .github/safety-check/ (the candidate rewording in its candidate/
folder). Each review gets a random review id; only a verdict carrying it counts, so text from the reviewed
repo can't stand in for the verdict. A verdict passes only at or above the confidence threshold, with no
steering attempt and no critical finding. An agent that refuses the review is `declined`, which never
passes (decision 63). Calibration can render the candidate prompt; verdicts are always checked against the
live schema.

Until 2026-11-11 the agent was Google's Jules (spec decision history); its client was removed after Google
shut Jules down.
"""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path

import jinja2
import jsonschema

from . import store

EXCERPT_CHARS = 400     # how much of a refusal is kept as the reason
NO_VERDICT = "no verdict.json was found"


# The prompts (decision 63). Live reviews always use LIVE; calibration may render CANDIDATE, a proposed
# rewording tried on real repos before it replaces LIVE. Its schema must stay structurally identical (only
# the title and descriptions may differ; a test checks it). Since the 2026-10-10 promotion the candidate
# holds the same files as live, so the next rewording starts from there.
LIVE, CANDIDATE = "live", "candidate"
PROMPTS = {LIVE: ".github/safety-check", CANDIDATE: ".github/safety-check/candidate"}

class Deferred(Exception):
    """The agent refused the review for quota or rate limits."""


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


# --- verdicts ---------------------------------------------------------------------------

def verdict_schema(root: Path | None = None, prompt: str = LIVE) -> dict:
    """The verdict schema shown with a prompt. Verdicts are only ever validated against the live one."""
    return store.load_json(f"{PROMPTS[prompt]}/verdict.schema.json", root)


def new_review_id() -> str:
    return secrets.token_hex(16)


def render_prompt(repo_url: str, sha: str, threshold: int, review_id: str, root: Path | None = None,
                  prompt: str = LIVE) -> str:
    root = root or store.ROOT
    template = (root / PROMPTS[prompt] / "prompt.md").read_text(encoding="utf-8")
    schema = json.dumps(verdict_schema(root, prompt), indent=2)
    return jinja2.Environment(undefined=jinja2.StrictUndefined).from_string(template).render(
        repo_url=repo_url, sha=sha, threshold=threshold, review_id=review_id, schema=schema)

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

# --- declines -----------------------------------------------------------------------------
# An agent sometimes refuses a review outright, intermittently (2026-10-10: "I am programmed to strictly
# refuse any requests to perform security reviews, ..."). A refusal is marked by its wording: an agent
# message in one of the first-person refusal shapes in REFUSAL_PATTERNS ("I can't help with that", "I'm not
# able to provide a security assessment of this repository", "my guidelines prevent me ..."). What's refused
# must be the task itself (the review, the request, the repository, "this" or "that") or nothing named: "I
# decline to rate the binary as safe" or "I must refuse to run the install script" are part of reviewing,
# not refusals. Third-person mentions ("the server will refuse any request") don't match, and a message
# carrying a verdict for this review is never a refusal (that is a format problem; a verdict with another
# id doesn't count).
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


def _plain(text: str) -> str:
    text = re.sub(r"[*_`]", "", text)  # Markdown emphasis and code marks: "**I can't help with that**"
    text = " ".join(text.replace("\u2019", "'").replace("\u2018", "'").lower().split())
    for short, full in _CONTRACTIONS:
        text = text.replace(short, full)
    return text


def looks_like_refusal(text: str | None, review_id: str | None = None) -> bool:
    """Whether an agent message refuses the review (see above). A message holding a verdict-shaped
    object with this review's id is an attempt at the verdict, not a refusal."""
    if not text:
        return False
    if review_id and any(obj.get("review_id") == review_id for obj in _json_objects(text)):
        return False
    plain = _plain(text)
    return any(p.search(plain) for p in REFUSAL_PATTERNS)

def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "\u2026"

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
