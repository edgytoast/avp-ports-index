"""Salted-hash blocklist and flag memory (spec §5.7).

Neither file names a repo or gives a reason: each record is sha256(BLOCKLIST_SALT + key).
"""

from __future__ import annotations

import hashlib
import os

from .store import State, today


def salt_from_env() -> str:
    salt = os.environ.get("BLOCKLIST_SALT", "")
    if not salt:
        raise RuntimeError("BLOCKLIST_SALT is not set")
    return salt


def h(salt: str, key: str) -> str:
    return hashlib.sha256((salt + key).encode("utf-8")).hexdigest()


def repo_id_key(repo_id: int) -> str:
    return f"repo_id:{int(repo_id)}"


def repo_name_key(full_name: str) -> str:
    return f"repo_name:{full_name.lower()}"


def slug_key(entry_id: str) -> str:
    return f"slug:{entry_id}"


def hashes(state: State) -> set[str]:
    return {item["h"] for item in state.blocklist.get("entries", [])}


def flag_hashes(state: State) -> set[str]:
    return {item["h"] for item in state.flags.get("entries", [])}


def is_blocked(state: State, salt: str, *, repo_id: int | None = None,
               repo_names: tuple[str, ...] = (), entry_id: str | None = None) -> bool:
    keys = []
    if repo_id is not None:
        keys.append(repo_id_key(repo_id))
    keys.extend(repo_name_key(n) for n in repo_names if n)
    if entry_id:
        keys.append(slug_key(entry_id))
    blocked = hashes(state)
    return any(h(salt, key) in blocked for key in keys)


def _add(state: State, salt: str, key: str, kind: str) -> bool:
    digest = h(salt, key)
    items = state.blocklist.setdefault("entries", [])
    if any(item["h"] == digest for item in items):
        return False
    items.append({"h": digest, "kind": kind, "category": "removed-policy", "added": today()})
    return True


def block(state: State, salt: str, *, repo_id: int | None, repo_name: str | None,
          entry_id: str | None = None) -> None:
    """Block a repo (by ID and name), and the entry id too when the whole entry is blocked."""
    if repo_id is not None:
        _add(state, salt, repo_id_key(repo_id), "repo_id")
    if repo_name:
        _add(state, salt, repo_name_key(repo_name), "repo_name")
    if entry_id:
        _add(state, salt, slug_key(entry_id), "slug")


def unblock(state: State, salt: str, *, repo_id: int | None, repo_names: tuple[str, ...] = (),
            entry_id: str | None = None) -> int:
    keys = set()
    if repo_id is not None:
        keys.add(h(salt, repo_id_key(repo_id)))
    keys.update(h(salt, repo_name_key(n)) for n in repo_names if n)
    if entry_id:
        keys.add(h(salt, slug_key(entry_id)))
    before = len(state.blocklist.get("entries", []))
    state.blocklist["entries"] = [i for i in state.blocklist.get("entries", []) if i["h"] not in keys]
    return before - len(state.blocklist["entries"])


def is_flagged(state: State, salt: str, repo_id: int) -> bool:
    return h(salt, repo_id_key(repo_id)) in flag_hashes(state)


def add_flag(state: State, salt: str, repo_id: int) -> bool:
    digest = h(salt, repo_id_key(repo_id))
    items = state.flags.setdefault("entries", [])
    if any(item["h"] == digest for item in items):
        return False
    items.append({"h": digest, "flagged_at": today()})
    return True


def remove_flag(state: State, salt: str, repo_id: int) -> bool:
    digest = h(salt, repo_id_key(repo_id))
    before = len(state.flags.get("entries", []))
    state.flags["entries"] = [i for i in state.flags.get("entries", []) if i["h"] != digest]
    return len(state.flags["entries"]) != before
