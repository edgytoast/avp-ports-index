"""Public TestFlight betas of listed ports, for the README's TestFlight column.

The daily health check looks for a public invite (https://testflight.apple.com/join/<code>) in the
port's own repo: its description and website, its README on the linked branch, and the bodies of
its five newest releases. A repo that is a GitHub fork (a copy the index lists from) is read only
when the copy itself has none, and then its parent, the developer's own repo, is read the same way.
Nothing else counts: not the game's engine, not the upstream projects the entry credits.

Every link found is opened on Apple's site, without a GitHub token, to see whether the beta is
open, full, closed to new testers or gone. Exactly one open or full beta goes in the table; more
than one is left out as ambiguous and named in the run summary. A failure keeps the old record.
"""

from __future__ import annotations

import html
import re
from urllib.parse import quote

import requests

from .checks import decode_content, linked_head

LINK = re.compile(r"https?://testflight\.apple\.com/join/([A-Za-z0-9]{6,12})(?![A-Za-z0-9])")
TITLE = re.compile(r"<title>\s*Join the (.+?) beta\s*-\s*TestFlight", re.I | re.S)
FULL = "this beta is full"
CLOSED = "accepting any new testers"
LIVE = ("open", "full")
RELEASES = 5


def codes(text: str) -> list[str]:
    """Invite codes in reading order, each once."""
    seen: list[str] = []
    for code in LINK.findall(text or ""):
        if code not in seen:
            seen.append(code)
    return seen


def url(code: str) -> str:
    return f"https://testflight.apple.com/join/{code}"


def classify(status_code: int, page: str) -> tuple[str, str | None]:
    """(status, app name) from Apple's join page: open, full, closed or gone."""
    if status_code == 404:
        return "gone", None
    if status_code >= 400:
        raise requests.HTTPError(f"TestFlight answered HTTP {status_code}")
    match = TITLE.search(page or "")
    if not match:
        return "gone", None  # Apple's "Not Found" page carries no "Join the ... beta" title
    app = re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()[:120]
    text = html.unescape(page).replace("’", "'").lower()
    if FULL in text:
        return "full", app
    if CLOSED in text:
        return "closed", app
    return "open", app


def probe(http, code: str) -> tuple[str, str | None]:
    resp = http.get(url(code), headers={"User-Agent": "Mozilla/5.0 (avp-ports-index health check)"},
                    timeout=30, allow_redirects=True)
    return classify(resp.status_code, resp.text)


def repo_text(reader, repo: dict, ref: str | None) -> list[tuple[str, str]]:
    """(where, text) pairs from one repo: description, website, README at `ref`, newest releases."""
    owner, name = repo["owner"]["login"], repo["name"]
    full = f"{owner}/{name}"
    out = [(f"{full} description", repo.get("description") or ""),
           (f"{full} website", repo.get("homepage") or "")]
    readme = reader.get(f"/repos/{quote(owner)}/{quote(name)}/readme", {"ref": ref} if ref else None)
    if isinstance(readme, dict):
        out.append((f"{full} {readme.get('path') or 'README'}", decode_content(readme).decode("utf-8", "replace")))
    for rel in reader.releases(owner, name, RELEASES):
        if not rel.get("draft"):
            out.append((f"{full} release {rel.get('tag_name') or ''}".rstrip(), rel.get("body") or ""))
    return out


def find(reader, repo: dict, entry: dict) -> list[tuple[str, str]]:
    """(code, where) for every invite in the port's repo, or in its fork parent when the repo has none."""
    def scan(r: dict, ref: str | None) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for where, text in repo_text(reader, r, ref):
            for code in codes(text):
                if code not in [c for c, _ in found]:
                    found.append((code, where))
        return found

    found = scan(repo, linked_head(reader, repo, entry))
    parent = repo.get("parent") if repo.get("fork") else None
    if not found and parent and parent.get("owner") and parent.get("name"):
        found = scan(parent, None)  # the parent's default branch
    return found


def check(reader, http, repo: dict, entry: dict) -> tuple[dict | None, str]:
    """The `testflight` health record for one entry (None if it has no usable beta) and a summary line."""
    found = find(reader, repo, entry)
    if not found:
        return None, "no TestFlight link"
    probed = [(code, where, *probe(http, code)) for code, where in found]
    live = [p for p in probed if p[2] in LIVE]
    notes = "; ".join(f"{url(c)} ({s}{', ' + a if a else ''}) in {w}" for c, w, s, a in probed)
    if len(live) > 1:
        return None, f"TestFlight left out, more than one live beta: {notes}"
    if not live:
        return None, f"TestFlight left out, no live beta: {notes}"
    code, where, status, app = live[0]
    return ({"url": url(code), "status": status, "app": app, "source": where[:200]},
            f"TestFlight {status}: {notes}")


def refresh(rt, health: dict, entry_id: str, entry: dict, repo: dict) -> None:
    """Update health["testflight"] for one listed entry. Errors keep the previous record."""
    http = rt.http or requests.Session()  # Apple's pages get no GitHub token
    try:
        record, line = check(rt.gh, http, repo, entry)
    except Exception as exc:  # noqa: BLE001 - a TestFlight lookup must never stop the health check
        rt.summary(f"{entry_id}: TestFlight not checked ({type(exc).__name__}: {str(exc)[:120]}); "
                   "kept the previous record")
        return
    old = health.get("testflight")
    health["testflight"] = record
    if record != old and (record or old):
        rt.summary(f"{entry_id}: {line}")
