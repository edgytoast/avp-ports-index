"""sync-state and reconcile (spec §8.5 steps 1 and 2), shared by build-surfaces, the health
check and the kill switch.

Walk main's commits after the last_synced_sha cursor, replay each merged entry PR, and record
its lifecycle and scan record. Missed, failed or [skip ci] runs are caught up next time.
"""

from __future__ import annotations

import datetime as dt

from . import approvals, blocklist, lifecycle, messages, store, validate
from .checks import controls, linked_head
from .classify import ENTRY_FILE
from .gate import STAGE1, STAGE2, latest_check, parse_external_id, read_marker
from .lifecycle import DECAY, LISTED, PULLED, TAKEN_DOWN, WITHDRAWN, IllegalTransition
from .writer import git, git_bytes


# --- facts about a linked repo -------------------------------------------------------------

def compare_scan(rt, owner: str, name: str, scanned: str | None, head: str | None) -> tuple[int | None, str]:
    """(commits_since_scan, scan_state) from compare scanned...HEAD."""
    if not scanned or not head:
        return None, "unknown"
    if scanned == head:
        return 0, "current"
    data = rt.gh.compare(owner, name, scanned, head)
    if not data:
        return None, "unknown"
    status = data.get("status")
    if status == "identical":
        return 0, "current"
    if status == "ahead":
        return int(data.get("ahead_by") or 0), "behind"
    return None, "unknown"


def repo_facts(rt, entry_id: str, entry: dict, repo: dict, state: store.State) -> None:
    """Record github_verified, curator_own, archived, license and last_commit_date."""
    health = state.health_record(entry_id)
    record = state.lifecycle.get(entry_id) or {}
    owner, name = repo["owner"]["login"], repo["name"]
    dev_login = str((entry.get("developer") or {}).get("github") or "")
    dev_user = rt.gh.user(dev_login) if dev_login else None
    health["github_verified"] = bool(dev_user) and controls(rt.gh, repo, dev_user["id"], dev_user["login"])
    owner_controls = controls(rt.gh, repo, rt.owner_id, rt.owner_login)
    health["curator_own"] = bool(owner_controls or (
        record.get("submitted_by_id") == rt.owner_id and dev_login.lower() == rt.owner_login.lower()))
    health["archived"] = bool(repo.get("archived"))
    head = linked_head(rt.gh, repo, entry)
    if head:
        commit = rt.gh.commit(owner, name, head) or {}
        date = (((commit.get("commit") or {}).get("committer") or {}).get("date"))
        if date:
            health["last_commit_date"] = store.iso(store.parse_iso(date))
    lic = rt.gh.license(owner, name, head) if head else None
    if not lic or not lic.get("license"):
        health["license"] = {"spdx": None, "kind": "none"}
    else:
        spdx = lic["license"].get("spdx_id")
        if spdx in rt.policy.get("license_open_source", []):
            health["license"] = {"spdx": spdx, "kind": "open-source"}
        else:
            health["license"] = {"spdx": None if spdx in (None, "NOASSERTION", "Other") else spdx, "kind": "custom"}
    if head:
        health["commits_since_scan"], health["scan_state"] = compare_scan(
            rt, owner, name, health.get("scanned_commit"), head)


def pin(rt, state: store.State, entry_id: str, sha: str, kind: str, confidence: int | None,
        repo: dict | None, entry: dict | None) -> bool:
    """Move (or confirm) the scan pin. Applies the pin-move rule (spec §5.4). True if it moved."""
    health = state.health_record(entry_id)
    moved = health.get("scanned_commit") != sha
    health["scanned_commit"] = sha
    health["scanned_at"] = store.iso(store.utcnow())
    health["scan_kind"] = kind
    health["scan_confidence"] = confidence if kind == "automated" else None
    if moved:
        health["flagged_commit"] = None
        health["flagged_files"] = []
        health["rescan_after"] = None
        health["rescan_hold"] = False
        health["scan_declines"] = 0
        if repo:
            head = linked_head(rt.gh, repo, entry)
            health["commits_since_scan"], health["scan_state"] = compare_scan(
                rt, repo["owner"]["login"], repo["name"], sha, head)
    return moved


# --- replaying one merged PR -----------------------------------------------------------------

def stage2_kind(check: dict | None) -> tuple[str, int | None, str | None]:
    """Classify a merged PR's gate/stage2: unchanged | scan | result | none."""
    if not check or check.get("status") != "completed":
        return "none", None, None
    marker = read_marker(check)
    parsed = parse_external_id(check.get("external_id"))
    sha = parsed[1] if parsed else None
    if check.get("conclusion") == "success":
        if marker.get("kind") == "unchanged":
            return "unchanged", None, None
        if marker.get("kind") == "scan" and sha:
            return "scan", marker.get("confidence"), sha
        return "none", None, None
    if marker.get("kind") == "result" and sha:
        return "result", None, sha
    return "none", None, None


def replay_entry(rt, state: store.State, pr: dict, entry_id: str, raw: bytes, by: str = "merge") -> None:
    try:
        entry = validate.load_untrusted_yaml(raw)
        owner, name = validate.parse_repo_url(entry["repo"])
    except (validate.YamlError, validate.InvalidInput, KeyError, TypeError):
        rt.owner_issue(f"Merged entry {entry_id} is unreadable",
                       f"PR #{pr['number']} merged an entry file that couldn't be parsed. Please look at it.")
        return
    record = state.lifecycle.get(entry_id)
    previous = record.get("status") if record else None
    if previous in (PULLED, TAKEN_DOWN):
        rt.upsert_triage(entry_id, f"PR #{pr['number']} was merged, but `{entry_id}` is {previous}, so it "
                                   "stays as it is. Use the kill switch if it should come back.")
        return
    head = (pr.get("head") or {}).get("sha")
    s1 = latest_check(rt, head, STAGE1) if head else None
    s2 = latest_check(rt, head, STAGE2) if head else None
    ext1 = parse_external_id((s1 or {}).get("external_id"))
    repo = rt.gh.repo_by_id(ext1[0]) if ext1 else None
    if repo is None:
        repo = rt.gh.repo(owner, name)
    if repo is None:
        rt.owner_issue(f"Merged entry {entry_id}: repo not found",
                       f"PR #{pr['number']} merged `{entry_id}`, but its repo couldn't be resolved.")
        return
    new_listing = previous in (None, WITHDRAWN)
    repo_changed = not new_listing and (record or {}).get("repo_id") != repo["id"]
    kind, confidence, sha = stage2_kind(s2)
    scanned = parse_external_id((s2 or {}).get("external_id"))
    if kind in ("scan", "result") and (not scanned or scanned[0] != repo["id"]):
        kind = "none"  # the check was for another repo (the entry was repointed after the scan)
    curator = False
    if kind == "scan":
        pin(rt, state, entry_id, sha, "automated", confidence, repo, entry)
    elif kind == "result":
        pin(rt, state, entry_id, sha, "curator-reviewed", None, repo, entry)
        # Merging a flagged PR approves the flagged files' exact bytes too (decision 62).
        approvals.record(state, entry_id, repo, sha, read_marker(s2).get("files"), rt.http)
        curator = True
    elif kind == "none" and (new_listing or repo_changed):
        fallback = ext1[1] if ext1 else linked_head(rt.gh, repo, entry)
        pin(rt, state, entry_id, fallback, "curator-reviewed", None, repo, entry)
        curator = True
    if curator:
        blocklist.remove_flag(state, rt.salt, repo["id"])
    fields = {"repo": entry["repo"], "repo_id": repo["id"]}
    if new_listing:
        fields.update(submitted_by=pr["user"]["login"], submitted_by_id=pr["user"]["id"])
    try:
        lifecycle.transition(state, entry_id, LISTED, by, **fields)
    except IllegalTransition as exc:
        rt.upsert_triage(entry_id, f"Couldn't record PR #{pr['number']}: {exc}")
        return
    own = repo["owner"]["id"] == rt.owner_id
    current = state.lifecycle[entry_id]
    if new_listing or repo_changed:
        current["owner_approved"] = bool(curator or own)
    else:
        current["owner_approved"] = bool(current.get("owner_approved") or curator or own)
    repo_facts(rt, entry_id, entry, repo, state)
    if previous != LISTED:
        base_url, _ = rt.urls()
        text = messages.render("merged", rt.root, name=entry.get("name", entry_id),
                               url=f"{base_url}/ports/{entry_id}.md")
        rt.once(f"merged:{pr['number']}", lambda: messages.upsert(rt, pr["number"], text))


def withdraw(rt, state: store.State, entry_id: str) -> None:
    if state.status(entry_id) in (LISTED, DECAY):
        lifecycle.transition(state, entry_id, WITHDRAWN, "self-removal")


def commit_files(root, sha: str) -> list[tuple[str, str]]:
    out = git(root, "diff-tree", "--root", "--no-commit-id", "--no-renames", "-r", "--name-status", sha)
    changes = []
    for line in out.splitlines():
        status, _, path = line.partition("\t")
        if ENTRY_FILE.match(path):
            changes.append((status[:1], path))
    return changes


def merged_pr_for(rt, sha: str) -> dict | None:
    for pr in rt.gh.commit_pulls(sha):
        if pr.get("merged_at") and pr.get("merge_commit_sha") == sha:
            return pr
    return None


def replay_commit(rt, state: store.State, sha: str, by: str = "merge") -> bool:
    changes = commit_files(rt.root, sha)
    if not changes:
        return False
    pr = merged_pr_for(rt, sha)
    if pr is None:
        return False  # App commits, the initial import and direct pushes update state themselves
    for status, path in changes:
        stem = ENTRY_FILE.match(path).group(1)
        try:
            entry_id = validate.entry_id(stem)
        except validate.InvalidInput:
            continue
        if status == "D":
            withdraw(rt, state, entry_id)
        else:
            raw = git_bytes(rt.root, "show", f"{sha}:{path}") or b""
            replay_entry(rt, state, pr, entry_id, raw, by)
    return True


def sync_state(rt, state: store.State) -> int:
    """Replay merged entry PRs after the cursor. Returns how many commits were replayed."""
    cursor = state.sync.get("last_synced_sha")
    known = cursor and git(rt.root, "cat-file", "-t", cursor, check=False).strip() == "commit"
    span = f"{cursor}..HEAD" if known else "HEAD"
    commits = git(rt.root, "log", "--reverse", "--format=%H", span).split()
    replayed = 0
    for sha in commits:
        if replay_commit(rt, state, sha):
            replayed += 1
    if commits:
        state.sync["last_synced_sha"] = commits[-1]
    return replayed


def reconcile(rt, state: store.State) -> None:
    """Safety net after the cursor replay: every entry file has a record, every listed record a file."""
    entries, _ = store.load_entries(rt.root)
    for entry_id in sorted(entries):
        status = state.status(entry_id)
        if status is not None and status != WITHDRAWN:
            continue
        added = git(rt.root, "log", "--diff-filter=A", "--format=%H", "--", f"entries/{entry_id}.yaml").split()
        pr = merged_pr_for(rt, added[0]) if added else None
        if pr is None:
            rt.health_comment(f"Reconcile: `entries/{entry_id}.yaml` has no lifecycle record and no merged PR "
                              "to replay. The curator should look at it.")
            continue
        replay_entry(rt, state, pr, entry_id, store.entry_path(entry_id, rt.root).read_bytes(), by="reconcile")
        rt.health_comment(f"Reconcile: recorded `{entry_id}` from PR #{pr['number']}, which the cursor replay "
                          "had missed.")
    for entry_id, record in sorted(state.lifecycle.items()):
        if record.get("status") == LISTED and entry_id not in entries:
            rt.upsert_triage(entry_id, f"`{entry_id}` is listed, but `entries/{entry_id}.yaml` is missing.")


def sync_all(rt, state: store.State) -> None:
    sync_state(rt, state)
    reconcile(rt, state)


def now_plus(hours: int) -> str:
    return store.iso(store.utcnow() + dt.timedelta(hours=hours))
