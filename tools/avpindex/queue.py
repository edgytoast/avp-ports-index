"""The Stage 2 dispatcher (spec §8.3): throttle, first-in-first-out order and rescans.

Runs are idempotent. The ledger comes from the Actions API: each stage2-scan run is named
"stage2 <mode> <pr or entry id>", and its report job uploads an empty artifact named
result-<pass|flag|error|deferred|declined>. A declined scan used a Jules session, so it counts like
any other run. A deferral (quota) in the last hour pauses dispatching, and so do DECLINE_PAUSE declines
(any targets): a refusal storm shouldn't burn the caps or the contributors' tries.
Calibration runs (stage2-calibrate.yml, "stage2 calibrate <label>") are a separate workflow, outside
these caps; the ledger never counts or parses them as scans.
"""

from __future__ import annotations

import datetime as dt
import math
import re

from . import blocklist, checks, messages, store, validate
from .checks import PASS, ROUTE, IndexView, Report, Result, Subject
from .gate import (STAGE1, STAGE1_MARKER_RE, STAGE2, entry_bytes_at, entry_pr, latest_check, parse_external_id,
                   post_stage1, read_marker)
from .lifecycle import LISTED

SCAN_WORKFLOW = "stage2-scan.yml"
UPSTREAM_CHECKS = {"S1-06", "S1-07", "S1-11a", "S1-11d"}  # failures fixed in the port's repo
RECHECK_SECONDS = 300  # stop starting new re-checks after this; the workflow step has its own hard limit
DECLINE_PAUSE = 2      # declined scans in the last hour that pause dispatching, as one deferral does
RUN_NAME_RE = re.compile(r"^stage2 (pr|rescan) ([0-9]+|[a-z0-9]+(?:-[a-z0-9]+)*)$")
CALIBRATE_RUN_RE = re.compile(r"^stage2 calibrate\b")


def parse_run_name(name: str | None) -> tuple[str, str] | None:
    match = RUN_NAME_RE.match(name or "")
    return (match.group(1), match.group(2)) if match else None


def ledger(runs: list[dict], now: dt.datetime) -> dict:
    hour_ago, day_ago = now - dt.timedelta(hours=1), now - dt.timedelta(days=1)
    out = {"used_hour": 0, "used_day": 0, "rescans_day": 0, "recent": [], "active_rescans": set()}
    for run in runs:
        created = store.parse_iso(run["created_at"])
        title = run.get("display_title") or run.get("name")
        if created < day_ago or CALIBRATE_RUN_RE.match(title or ""):
            continue
        out["used_day"] += 1
        parsed = parse_run_name(title)
        if parsed and parsed[0] == "rescan":
            out["rescans_day"] += 1
            if run.get("status") != "completed":
                out["active_rescans"].add(parsed[1])  # never dispatch a second rescan of the same entry
        if created >= hour_ago:
            out["used_hour"] += 1
            out["recent"].append(run)
    return out


def slots(policy: dict, enabled: bool, used: dict, deferred_recent: bool) -> int:
    if not enabled or deferred_recent:
        return 0
    stage2 = policy["stage2"]
    return max(0, min(stage2["hourly_cap"] - used["used_hour"], stage2["daily_cap"] - used["used_day"]))


def eta_text(position: int, hourly_cap: int) -> str:
    hours = max(1, math.ceil(position / max(1, hourly_cap)))
    if hours == 1:
        return "an hour or less"
    if hours >= 48:
        return f"{math.ceil(hours / 24)} days"
    return f"{hours} hours"


def first_queued_at(rt, number: int) -> str:
    times = [e["created_at"] for e in rt.gh.issue_events(number)
             if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == "stage2:queued"]
    return min(times) if times else "9999"


def queued_prs(rt) -> list[dict]:
    """Open PRs labeled stage2:queued, first in first out by their first such label."""
    items = [i for i in rt.gh.issues(labels="stage2:queued", state="open") if "pull_request" in i]
    ordered = [{"number": i["number"], "since": first_queued_at(rt, i["number"])} for i in items]
    ordered.sort(key=lambda q: (q["since"], q["number"]))
    return ordered


def rescan_candidates(state: store.State, now: dt.datetime) -> list[str]:
    unknown, behind = [], []
    for entry_id, record in state.lifecycle.items():
        if record.get("status") != LISTED:
            continue
        health = state.health.get(entry_id) or {}
        if health.get("rescan_hold") or not health.get("scanned_commit"):
            continue
        after = health.get("rescan_after")
        if after and store.parse_iso(after) > now:
            continue
        key = (health.get("scanned_at") or "", entry_id)
        if health.get("scan_state") == "unknown":
            unknown.append(key)
        elif health.get("scan_state") == "behind":
            behind.append(key)
    return [e for _, e in sorted(unknown)] + [e for _, e in sorted(behind)]


def rescan_precheck(rt, entry_id: str, entry: dict, state: store.State) -> tuple[dict, str] | None:
    """S1-06, S1-07 and S1-11a to S1-11c at the linked HEAD. Returns (repo, head) if all pass."""
    index = IndexView(policy=rt.policy, schema=rt.entry_schema(), index_repo=rt.repo)
    ctx = checks.Ctx(Subject(mode="health", entry_id=entry_id), index, rt.gh, None)
    ctx.entry = entry
    for check in (checks.s1_06, checks.s1_07, checks.s1_11a, checks.s1_11b, checks.s1_11c):
        result = check(ctx)
        if result is None or result.outcome != PASS:
            return None
    return ctx.repo, ctx.head


def _pause_reason(rt, recent: list[dict]) -> str:
    """Why dispatching pauses this hour, or "": a deferral, or DECLINE_PAUSE declines (spec §8.3 step 2)."""
    declines = 0
    for run in recent:
        if run.get("status") != "completed":
            continue
        names = {a.get("name") for a in rt.gh.run_artifacts(run["id"])}
        if "result-deferred" in names:
            return "a scan was deferred for quota in the last hour"
        declines += "result-declined" in names
    if declines >= DECLINE_PAUSE:
        return f"Jules declined {declines} scans in the last hour"
    return ""


def recheck_waiting(rt, now: dt.datetime) -> list[str]:
    """Rerun Stage 1 on open entry PRs whose only failures are fixed in the port's own repo, once
    that repo has a new commit (or every `stage1_recheck_hours`), so a fix there moves the PR on
    without a close and reopen. Runs as its own step after the merge sweep (§8.3), so a slow or
    failing re-check never holds up scans or merges."""
    import time
    from .classify import ENTRY_ADD, ENTRY_EDIT, classify
    budget = int(rt.policy.get("stage1_recheck_max_per_run", 10))
    every = dt.timedelta(hours=int(rt.policy.get("stage1_recheck_hours", 24)))
    started = time.monotonic()
    log = []
    for listed in rt.gh.open_prs():
        if budget <= 0 or time.monotonic() - started > RECHECK_SECONDS:
            break
        labels = {label["name"] for label in listed.get("labels") or []}
        if listed.get("draft") or "stage1:fail" not in labels:
            continue
        number = listed["number"]
        try:
            check = latest_check(rt, listed["head"]["sha"], STAGE1)
            failures = set(read_marker(check, STAGE1_MARKER_RE).get("failures") or [])
            if not failures or not failures <= UPSTREAM_CHECKS:
                continue
            ext = parse_external_id((check or {}).get("external_id"))
            due = False
            if ext:
                entry_id, entry, _ = _pr_entry(rt, listed)
                repo = rt.gh.repo_by_id(ext[0]) if entry else None
                due = bool(repo) and checks.linked_head(rt.gh, repo, entry) not in (None, ext[1])
            if not due:
                try:
                    due = now - store.parse_iso((check or {}).get("completed_at") or "") >= every
                except (TypeError, ValueError):
                    due = False
            if not due:
                continue
            pr = rt.gh.pr(number)  # fresh: the PR may have moved on since the list was read
            labels = {label["name"] for label in pr.get("labels") or []}
            if (pr.get("state") != "open" or pr.get("draft") or "stage1:fail" not in labels
                    or pr["head"]["sha"] != listed["head"]["sha"]):
                continue
            cls = classify(rt.gh.pr_files(number), pr["user"]["id"], pr["user"]["login"], rt.owner_id)
            if cls.kind not in (ENTRY_ADD, ENTRY_EDIT):
                continue
            entry_pr(rt, pr, cls, labels)
            budget -= 1
            log.append(f"recheck #{number} ({cls.stem})")
        except Exception as exc:  # one PR never stops the others
            log.append(f"recheck #{number}: skipped ({type(exc).__name__})")
    return log


def dispatch(rt) -> list[str]:
    now = store.utcnow()
    policy = rt.policy
    runs = rt.gh.workflow_runs(SCAN_WORKFLOW, store.iso(now - dt.timedelta(days=1)))
    used = ledger(runs, now)
    paused = _pause_reason(rt, used["recent"])
    free = slots(policy, rt.stage2_enabled, used, bool(paused))
    log = [f"ledger: {used['used_hour']} this hour, {used['used_day']} today "
           f"({used['rescans_day']} rescans); {free} slot(s)" + (f"; paused: {paused}" if paused else "")]
    state = store.State.load(rt.root)
    entries, _ = store.load_entries(rt.root)
    max_scans = policy["stage2"]["per_pr_max_scans"]
    waiting = 0
    active_entries: set[str] = set()
    queue = queued_prs(rt)

    for item in queue:
        number = item["number"]
        pr = rt.gh.pr(number)
        if pr.get("state") != "open":
            continue
        labels = {label["name"] for label in pr.get("labels") or []}
        head = pr["head"]["sha"]
        stage1 = latest_check(rt, head, STAGE1)
        ext = parse_external_id((stage1 or {}).get("external_id"))
        entry_id, entry, change = _pr_entry(rt, pr)
        if entry_id:
            active_entries.add(entry_id)
        if pr.get("draft") or "stage2:flagged" in labels:
            continue
        if not stage1 or stage1.get("conclusion") != "success" or not ext or not entry:
            continue
        owner_scan = "owner:scan" in labels
        repo_id, linked = ext
        if not owner_scan and _flag_routes(rt, state, entries, entry_id, entry, change, repo_id, linked):
            report = Report(results=[Result("S1-17", ROUTE, "an earlier automated review of this repo asked "
                                                            "for a closer look")])
            report.repo, report.head = {"id": repo_id}, linked
            post_stage1(rt, head, report, note="Re-checked before the security review started.")
            rt.gh.remove_label(number, "stage2:queued")
            rt.gh.add_labels(number, ["needs-owner", "stage1:route"])
            rt.gh.remove_label(number, "stage1:pass")
            messages.upsert(rt, number, messages.render("route", rt.root, name=entry.get("name", entry_id),
                                                        reasons=messages.route_reasons(["S1-17"])))
            log.append(f"#{number}: S1-17 now routes")
            continue
        bot_state = messages.read_state(messages.find_bot_comment(rt, number))
        if bot_state["scans"] >= max_scans and not owner_scan:
            rt.gh.create_check(head, STAGE2, conclusion="failure", title="Scan limit reached; waiting for the curator",
                               summary=f"This PR has used its {max_scans} automated reviews.")
            rt.gh.remove_label(number, "stage2:queued")
            rt.gh.add_labels(number, ["needs-owner"])
            messages.upsert(rt, number, messages.render("owner-review", rt.root, name=entry.get("name", entry_id)))
            log.append(f"#{number}: scan limit reached")
            continue
        if free <= 0:
            waiting += 1
            continue
        rt.gh.remove_label(number, "stage2:queued")
        rt.gh.add_labels(number, ["stage2:scanning"])
        messages.upsert(rt, number, scanning=f"{repo_id}@{linked}")
        inputs = {"mode": "pr", "pr": str(number), "head_sha": head, "linked_repo": _repo_name(entry),
                  "linked_commit": linked, "entry_id": entry_id, "repo_id": str(repo_id), "base_commit": "",
                  "counted": "false" if owner_scan else "true"}
        if rt.gh.dispatch(SCAN_WORKFLOW, inputs):
            free -= 1
            log.append(f"#{number}: dispatched scan of {linked[:12]}")
        else:
            rt.gh.remove_label(number, "stage2:scanning")
            rt.gh.add_labels(number, ["stage2:queued"])
            log.append(f"#{number}: dispatch failed; back in the queue")

    for item in rt.gh.issues(labels="stage2:scanning", state="open"):
        pr_entry = _pr_entry(rt, rt.gh.pr(item["number"]))[0] if "pull_request" in item else None
        if pr_entry:
            active_entries.add(pr_entry)

    rescans_left = policy["stage2"]["rescan_daily_max"] - used["rescans_day"]
    if waiting == 0:
        for entry_id in rescan_candidates(state, now):
            if free <= 0 or rescans_left <= 0:
                break
            if entry_id in active_entries or entry_id in used["active_rescans"] or entry_id not in entries:
                continue
            record, health = state.lifecycle[entry_id], state.health[entry_id]
            entry = entries[entry_id]
            try:
                owner, name = validate.parse_repo_url(entry["repo"])
            except (validate.InvalidInput, KeyError):
                continue
            repo = rt.gh.repo(owner, name)
            if not repo:
                continue
            head = checks.linked_head(rt.gh, repo, entry)
            if head in (health.get("scanned_commit"), health.get("flagged_commit")) or not head:
                continue
            if repo["id"] != record.get("repo_id"):
                continue  # S1-16: the health check pulls it; the dispatcher never writes state
            pre = rescan_precheck(rt, entry_id, entry, state)
            if pre is None:
                continue
            repo, head = pre
            inputs = {"mode": "rescan", "pr": "", "head_sha": "", "linked_repo": repo["full_name"],
                      "linked_commit": head, "entry_id": entry_id, "repo_id": str(repo["id"]),
                      "base_commit": health["scanned_commit"], "counted": "false"}
            if rt.gh.dispatch(SCAN_WORKFLOW, inputs):
                free -= 1
                rescans_left -= 1
                log.append(f"rescan {entry_id}: dispatched at {head[:12]}")

    for position, item in enumerate([q for q in queued_prs(rt)], start=1):
        pr = rt.gh.pr(item["number"])
        if pr.get("state") != "open" or pr.get("draft"):
            continue
        entry_id, entry, _ = _pr_entry(rt, pr)
        name = (entry or {}).get("name", entry_id or "this port")
        messages.upsert(rt, item["number"], messages.render(
            "queued", rt.root, name=name, n=position, eta=eta_text(position, policy["stage2"]["hourly_cap"])))
    return log


def _repo_name(entry: dict) -> str:
    owner, name = validate.parse_repo_url(entry["repo"])
    return f"{owner}/{name}"


def _pr_entry(rt, pr: dict) -> tuple[str | None, dict | None, str | None]:
    from .classify import ENTRY_ADD, ENTRY_EDIT, classify
    files = rt.gh.pr_files(pr["number"])
    cls = classify(files, pr["user"]["id"], pr["user"]["login"], rt.owner_id)
    if cls.kind not in (ENTRY_ADD, ENTRY_EDIT):
        return None, None, None
    raw = entry_bytes_at(rt, cls.path, pr["head"]["sha"])
    try:
        entry = validate.load_untrusted_yaml(raw or b"")
        validate.parse_repo_url(entry["repo"])
        stem = validate.entry_id(cls.stem)
    except (validate.YamlError, validate.InvalidInput, KeyError, TypeError):
        return None, None, None
    return stem, entry, cls.change


def _flag_routes(rt, state, entries, entry_id, entry, change, repo_id, linked) -> bool:
    if not blocklist.is_flagged(state, rt.salt, repo_id):
        return False
    old_repo = (entries.get(entry_id) or {}).get("repo") or (state.lifecycle.get(entry_id) or {}).get("repo") or ""
    changed = bool(old_repo) and old_repo.lower() != str(entry.get("repo", "")).lower()
    scanned = (state.health.get(entry_id) or {}).get("scanned_commit")
    return checks.needs_scan(change, changed, linked, scanned)
