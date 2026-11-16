"""Files the curator has approved, by SHA-256 (decision 62).

When the curator accepts a flagged commit (kill-switch `approve`, or merging a flagged PR), the
SHA-256 of every file the review's findings pointed at, at that commit, goes into
state/approvals.yaml for the entry. A later Stage 2 flag whose every finding above `info` sits on a
file with exactly those bytes is cleared to a pass: the curator has already checked them. A file
that changes, any other finding, a `critical` finding, a steering attempt or a confidence below
`stage2.approved_files_min_confidence` still flags.

Files are read from GitHub at the pinned commit (raw.githubusercontent.com, never with a token)
and only hashed: nothing from the repo is run.
"""

from __future__ import annotations

import hashlib

import requests

from . import media, store

MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 20  # findings on more files than this are never cleared


def flagged_files(verdict: dict | None) -> list[str] | None:
    """The files the findings above `info` point at, or None if one can't be named (no file, a path
    out of the repo, or more than MAX_FILES files)."""
    paths: list[str] = []
    for finding in (verdict or {}).get("findings") or []:
        if finding.get("severity") == "info":
            continue
        path = media.safe_path(str(finding.get("file") or ""))
        if not path:
            return None
        if path not in paths:
            paths.append(path)
    return paths if len(paths) <= MAX_FILES else None


def sha256_at(http, owner: str, name: str, sha: str, path: str) -> tuple[str, int]:
    data = media.download(http, media.raw_url(owner, name, sha, path), limit=MAX_BYTES)
    return hashlib.sha256(data).hexdigest(), len(data)


def approved_hashes(state: store.State, entry_id: str, repo_id: int) -> set[str]:
    record = state.approvals.get(entry_id) or {}
    if record.get("repo_id") != repo_id:
        return set()  # approvals belong to the repo they were made for
    return {f["sha256"] for f in record.get("files") or []}


def record(state: store.State, entry_id: str, repo: dict, sha: str, paths: list | None,
           http=None) -> tuple[list[str], list[str]]:
    """Add the files at `sha` to the entry's approvals. Returns (recorded paths, a note per file that
    couldn't be read): the approval of the commit stands either way; an unrecorded file is just
    reviewed again next time."""
    wanted = [p for p in (media.safe_path(str(p)) for p in (paths or [])[:MAX_FILES]) if p]
    if not wanted:
        return [], []
    http = http or requests.Session()  # a session of its own: no token travels with a file request
    owner, name = repo["owner"]["login"], repo["name"]
    current = state.approvals.get(entry_id) or {}
    files = list(current.get("files") or []) if current.get("repo_id") == repo["id"] else []
    recorded, notes = [], []
    for path in wanted:
        try:
            digest, size = sha256_at(http, owner, name, sha, path)
        except Exception as exc:  # noqa: BLE001 - an unreadable file just isn't recorded
            notes.append(f"`{path}` wasn't recorded ({type(exc).__name__}: {str(exc)[:120]})")
            continue
        recorded.append(path)
        if not any(f["sha256"] == digest and f["path"] == path for f in files):
            files.append({"path": path, "sha256": digest, "bytes": size, "commit": sha,
                          "approved_at": store.iso(store.utcnow())})
    if files:
        state.approvals[entry_id] = {"repo_id": repo["id"], "files": files}
    return recorded, notes


def clearance(state: store.State, entry_id: str | None, repo_id: int, repo_name: str, sha: str,
              verdict: dict | None, policy: dict, http=None) -> list[dict] | None:
    """The approved files that clear a flag, or None if it stands. Never raises: any failure keeps the flag."""
    try:
        if not entry_id or not verdict or verdict.get("steering_attempt"):
            return None
        if any(f.get("severity") == "critical" for f in verdict.get("findings") or []):
            return None
        if verdict["safe_confidence"] < int(policy["stage2"]["approved_files_min_confidence"]):
            return None
        approved = approved_hashes(state, entry_id, repo_id)
        paths = flagged_files(verdict)
        if not approved or not paths:
            return None
        owner, name = repo_name.split("/", 1)
        http = http or requests.Session()
        cleared = []
        for path in paths:
            digest, _size = sha256_at(http, owner, name, sha, path)
            if digest not in approved:
                return None
            cleared.append({"path": path, "sha256": digest})
        return cleared
    except Exception:  # noqa: BLE001 - when in doubt, the flag stands
        return None
