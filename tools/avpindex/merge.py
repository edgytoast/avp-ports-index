"""The merge rule, try_merge (spec §8.2 step 9). Called by the gate, the dispatcher's sweep and
the scan report job.

The App can bypass the ruleset, so this code is what enforces the rule: only entry PRs, only
with auto-merge on, only with all three required checks green from the App on the current
head, and only after re-checking duplicates, flags, the blocklist and pulled entries against
the current main.
"""

from __future__ import annotations

from . import blocklist, checks, store, validate
from .checks import FAIL, ROUTE, Report, Result
from .classify import ENTRY_CLASSES, ENTRY_REMOVE, classify
from .gate import REQUIRED, STAGE1, entry_bytes_at, latest_check, parse_external_id, post_stage1
from .writer import git, git_bytes


def main_snapshot(rt) -> tuple[store.State, dict]:
    """State and entries as they are on origin/main right now."""
    try:
        git(rt.root, "fetch", "--quiet", "origin", "main")
        files = {}
        for rel in (store.HEALTH, store.LIFECYCLE, store.FLAGS, store.BLOCKLIST):
            files[rel] = git_bytes(rt.root, "show", f"origin/main:{rel}")
        listing = git(rt.root, "ls-tree", "--name-only", "origin/main", "entries/").split()
    except Exception:  # not a git checkout (tests): read the working tree
        return store.State.load(rt.root), store.load_entries(rt.root)[0]
    import yaml
    state = store.State(root=rt.root)
    state.health = validate.normalize(yaml.safe_load(files[store.HEALTH] or b"{}")) or {}
    state.lifecycle = validate.normalize(yaml.safe_load(files[store.LIFECYCLE] or b"{}")) or {}
    state.flags = yaml.safe_load(files[store.FLAGS] or b"") or dict(store.EMPTY_LIST_FILE)
    state.blocklist = yaml.safe_load(files[store.BLOCKLIST] or b"") or dict(store.EMPTY_LIST_FILE)
    entries = {}
    for path in listing:
        if path.endswith(".yaml"):
            raw = git_bytes(rt.root, "show", f"origin/main:{path}")
            try:
                data = validate.load_untrusted_yaml(raw or b"")
            except validate.YamlError:
                continue
            if isinstance(data, dict):
                entries[path[len("entries/"):-len(".yaml")]] = data
    return state, entries


def checks_green(rt, head: str) -> bool:
    for name in REQUIRED:
        check = latest_check(rt, head, name)
        if not check or check.get("status") != "completed" or check.get("conclusion") != "success":
            return False
    return True


def recheck(rt, pr: dict, cls, state: store.State, entries: dict) -> list[Result]:
    """Re-run S1-04, S1-17 (adds and edits), S1-05 and S1-15 against the current main."""
    stem = cls.stem
    record = state.lifecycle.get(stem) or {}
    problems: list[Result] = []
    if record.get("status") == "pulled":
        problems.append(Result("S1-15", FAIL, "this entry is currently pulled and waiting for the curator"))
    stage1 = latest_check(rt, pr["head"]["sha"], STAGE1)
    ext = parse_external_id((stage1 or {}).get("external_id"))
    repo_id, linked = ext if ext else (None, None)
    entry = None
    if cls.kind != ENTRY_REMOVE:
        raw = entry_bytes_at(rt, cls.path, pr["head"]["sha"])
        try:
            entry = validate.load_untrusted_yaml(raw or b"")
        except validate.YamlError:
            entry = None
    names = []
    source = entry or entries.get(stem) or {}
    try:
        owner, name = validate.parse_repo_url(str(source.get("repo", "")))
        names.append(f"{owner}/{name}")
    except validate.InvalidInput:
        pass
    if blocklist.is_blocked(state, rt.salt, repo_id=repo_id if cls.kind != ENTRY_REMOVE else record.get("repo_id"),
                            repo_names=tuple(names), entry_id=stem):
        problems.append(Result("S1-05", FAIL, "this entry or repo can't be listed"))
    if cls.kind in ENTRY_CLASSES and cls.kind != ENTRY_REMOVE and entry:
        index = checks.IndexView(policy=rt.policy, schema={}, entries=entries, lifecycle=state.lifecycle)
        unique = checks.uniqueness(stem, cls.change, entry.get("repo", ""), repo_id, index)
        if unique.outcome == FAIL:
            problems.append(unique)
        labels = {label["name"] for label in pr.get("labels") or []}
        if "owner:scan" not in labels and repo_id is not None:
            old_repo = (entries.get(stem) or {}).get("repo") or record.get("repo") or ""
            changed = bool(old_repo) and old_repo.lower() != str(entry.get("repo", "")).lower()
            scanned = (state.health.get(stem) or {}).get("scanned_commit")
            if checks.needs_scan(cls.change, changed, linked, scanned) and blocklist.is_flagged(state, rt.salt, repo_id):
                problems.append(Result("S1-17", ROUTE, "an earlier automated review of this repo asked for a closer look"))
    return problems


def try_merge(rt, number: int, *, state: store.State | None = None, entries: dict | None = None) -> str:
    """Apply the merge rule to one PR. Returns what happened, for the run summary."""
    pr = rt.gh.pr(number)
    if pr.get("state") != "open":
        return "closed"
    files = rt.gh.pr_files(number)
    cls = classify(files, pr["user"]["id"], pr["user"]["login"], rt.owner_id)
    if cls.kind not in ENTRY_CLASSES:
        return f"not an entry PR ({cls.kind})"
    if not rt.auto_merge_enabled:
        return "auto-merge is off"
    labels = {label["name"] for label in pr.get("labels") or []}
    if pr.get("draft") or "needs-owner" in labels or "stage2:flagged" in labels:
        return "draft, flagged or waiting for the curator"
    head = pr["head"]["sha"]
    if not checks_green(rt, head):
        return "checks not green"
    if state is None or entries is None:
        state, entries = main_snapshot(rt)
    problems = recheck(rt, pr, cls, state, entries)
    if problems:
        stage1 = latest_check(rt, head, STAGE1)
        report = Report(results=problems)
        ext = (stage1 or {}).get("external_id")
        parsed = parse_external_id(ext)
        if parsed:
            report.repo, report.head = {"id": parsed[0]}, parsed[1]
        post_stage1(rt, head, report, note="Re-checked against the current main just before merging.")
        rt.gh.add_labels(number, ["needs-owner"] if any(p.outcome == ROUTE or p.id == "S1-15" for p in problems)
                         else ["needs-author"])
        return "re-check failed: " + ", ".join(p.id for p in problems)
    if not rt.merge_token and not rt.dry_run:
        return "no merge token"
    entry_id = cls.stem
    status = rt.gh.merge_pr(number, head, f"entry: {entry_id} (#{number})", rt.merge_token or "")
    return "merged" if status < 300 else f"merge refused ({status}); the sweep will retry"


def sweep(rt) -> list[str]:
    """Try every open entry PR whose three checks are green (spec §8.3 step 6)."""
    state, entries = main_snapshot(rt)
    out = []
    for pr in rt.gh.open_prs():
        if pr.get("draft"):
            continue
        labels = {label["name"] for label in pr.get("labels") or []}
        if "needs-owner" in labels or "stage2:flagged" in labels:
            continue
        if not checks_green(rt, pr["head"]["sha"]):
            continue
        out.append(f"#{pr['number']}: {try_merge(rt, pr['number'], state=state, entries=entries)}")
    return out
