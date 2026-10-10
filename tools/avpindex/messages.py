"""Bot messages (spec §11): rendering, plain route reasons, and the single upserted PR comment.

The PR comment also carries hidden machine state that contributors can't edit (only the App
writes it): the counted scan total (spec §8.3) and the scans that passed or were flagged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jinja2

from . import store, validate
from .checks import FIXES

PLAIN_REASONS = {
    "S1-08": "this PR doesn't come from the repo's owner (or the person who first listed it)",
    "S1-11b": "the repo is too large to list automatically",
    "S1-11c": "the repo contains archives or very large files",
    "S1-11d": "the repo's releases include prebuilt apps or archives",
    "S1-16": "the repo at this address isn't the one that was originally listed",
    "S1-17": "an earlier automated review of this repo asked for a closer look",
    "S1-18": "this entry id belonged to a different port before",
    "S1-09": "the license looks like it may not allow personal use",
}
ROUTE_ORDER = ["S1-08", "S1-16", "S1-17", "S1-18", "S1-09", "S1-11b", "S1-11c", "S1-11d"]

BOT_MARK = "<!-- avp:bot -->"
STATE_RE = re.compile(r"<!-- avp:state (\{.*?\}) -->", re.S)
SCANS_RE = re.compile(r"<!-- avp:scans=(\d+) -->")


def _env(root: Path) -> jinja2.Environment:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(root / "templates" / "messages")),
                             autoescape=False, trim_blocks=True, lstrip_blocks=True,
                             undefined=jinja2.StrictUndefined)
    env.filters["u"] = lambda v, limit=300: validate.md_inline(v, limit)
    env.filters["t"] = lambda v: " ".join(str(v).split())[:80]
    return env


def render(template: str, root: Path | None = None, /, **values) -> str:
    filename = f"{template}.j2" if template.endswith(".txt") else f"{template}.md.j2"
    return _env(root or store.ROOT).get_template(filename).render(**values).strip()


def join_clauses(clauses: list[str]) -> str:
    if len(clauses) <= 1:
        return "".join(clauses)
    return ", ".join(clauses[:-1]) + " and " + clauses[-1]


def route_reasons(route_ids: list[str]) -> str:
    ids = [i for i in ROUTE_ORDER if i in route_ids]
    return join_clauses([PLAIN_REASONS[i] for i in ids])


def fail_rows(results) -> list[dict]:
    return [{"id": r.id, "detail": r.detail or "failed", "fix": FIXES.get(r.id, "See the check details.")}
            for r in results if r.effective == "fail"]


def flag_pointers(verdict: dict | None) -> list[dict]:
    findings = (verdict or {}).get("findings") or []
    serious = [f for f in findings if f.get("severity") in ("medium", "high", "critical")]
    chosen = serious or findings
    return [{"file": f.get("file", ""), "category": f.get("category", "")} for f in chosen[:8]]


# --- the single bot comment on a PR ----------------------------------------------------

def find_bot_comment(rt, number: int) -> dict | None:
    for comment in rt.gh.comments(number):
        if BOT_MARK in (comment.get("body") or "") and rt.is_app_author(comment):
            return comment
    return None


def read_state(comment: dict | None) -> dict:
    state = {"scans": 0, "passed": {}, "flagged": None}
    if not comment:
        return state
    body = comment.get("body") or ""
    # The App writes its hidden state after the visible text, so the last marker is the real one.
    found = list(STATE_RE.finditer(body))
    if found:
        try:
            state.update(json.loads(found[-1].group(1)))
        except ValueError:
            pass
    else:
        scans = list(SCANS_RE.finditer(body))
        if scans:
            state["scans"] = int(scans[-1].group(1))
    return state


def visible_text(comment: dict | None) -> str:
    if not comment:
        return ""
    body = comment.get("body") or ""
    return body.split(BOT_MARK)[0].rstrip()


def upsert(rt, number: int, text: str | None = None, **changes) -> dict:
    """Write the PR's single bot comment. text=None keeps the visible message; changes update
    the hidden state (scans, passed, flagged). Returns the new state."""
    comment = find_bot_comment(rt, number)
    state = read_state(comment)
    state.update(changes)
    shown = visible_text(comment) if text is None else text
    encoded = json.dumps(state, sort_keys=True)
    # Jules findings quote attacker-chosen file names: keep "-->" from closing the comment.
    encoded = encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    body = (f"{shown}\n\n{BOT_MARK}\n<!-- avp:scans={int(state['scans'])} -->\n"
            f"<!-- avp:state {encoded} -->")
    if comment is None:
        rt.gh.comment(number, body)
    elif comment.get("body") != body:
        rt.gh.update_comment(comment["id"], body)
    return state
