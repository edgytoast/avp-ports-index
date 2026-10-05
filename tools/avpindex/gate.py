"""The PR gate (spec §8.2). Runs on pull_request_target with base-branch code only; the PR's
files are read as data through the Contents API at the head SHA, never checked out.
"""

from __future__ import annotations

import json
import re

import jsonschema

from . import blocklist, checks, messages, store, validate
from .checks import FAIL, PASS, ROUTE, IndexView, Report, Subject, decode_content
from .classify import (ENTRY_ADD, ENTRY_CLASSES, ENTRY_REMOVE, INVALID, OWNER_ADMIN, OWNER_VERIFY, SKIP,
                       VERIFY_FILE, classify)

POLICY_CHECK, STAGE1, STAGE2 = "gate/policy", "gate/stage1", "gate/stage2"
REQUIRED = (POLICY_CHECK, STAGE1, STAGE2)
WATCHED_LABELS = ("owner:scan", "blocklist", "kill-switch")
PIPELINE_LABELS = ("stage1:pass", "stage1:fail", "stage1:route", "needs-author", "needs-owner")
WAITING = "Waiting for the curator"
MARKER_RE = re.compile(r"<!-- avp:stage2 (\{.*?\}) -->")
STAGE1_MARKER_RE = re.compile(r"<!-- avp:stage1 (\{.*?\}) -->")


# --- check runs ------------------------------------------------------------------------

def stage2_marker(**data) -> str:
    return f"<!-- avp:stage2 {json.dumps(data, sort_keys=True)} -->"


def read_marker(check: dict | None, pattern: re.Pattern = MARKER_RE) -> dict:
    summary = ((check or {}).get("output") or {}).get("summary") or ""
    match = pattern.search(summary)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except ValueError:
        return {}


def results_table(report: Report) -> str:
    lines = ["| Check | Result | Details |", "| --- | --- | --- |"]
    for r in report.results:
        shown = "waived (owner:scan)" if r.waived else r.outcome
        lines.append(f"| {r.id} | {shown} | {validate.md_inline(r.detail, 300)} |")
    if report.warnings:
        lines += ["", "**Warnings** (these never block a PR):", ""]
        lines += [f"- {cid}: {validate.md_inline(text, 300)}" for cid, text in report.warnings]
    if report.waived:
        lines += ["", f"Waived by `owner:scan`: {', '.join(report.waived)}"]
    return "\n".join(lines)


def stage1_title(outcome: str) -> str:
    return {PASS: "Passed", FAIL: "Changes needed", ROUTE: WAITING}[outcome]


def apps_table(apps: list[dict]) -> str:
    """The release assets S1-11d routed, for the curator: sizes, and what's inside zip-format files."""
    if not apps:
        return ""
    lines = ["**Release assets** (sizes from GitHub; file lists read from zip-format files; nothing was "
             "downloaded whole or run):", "", "| Asset | Size | Files | Worth a look |", "| --- | --- | --- | --- |"]
    for app in apps:
        if "more" in app:
            lines.append(f"| …and {app['more']} more | | | |")
            continue
        if not app.get("listable", True):
            ext = app["name"].rsplit(".", 1)[-1] if "." in app["name"] else "?"
            files, review = f"not listed (.{validate.md_inline(ext, 12)})", "n/a"
        else:
            files = "couldn't be listed" if app.get("files") is None else str(app["files"])
            review = ", ".join(validate.md_inline(n, 120) for n in app.get("review") or []) or "none"
        lines.append(f"| {validate.md_inline(app['name'], 120)} | {app['size'] / 1e6:,.1f} MB | {files} | {review} |")
    return "\n".join(lines)


def post_stage1(rt, head: str, report: Report, *, note: str = "") -> None:
    outcome = report.overall
    marker = f"<!-- avp:stage1 {json.dumps({'failures': report.failures, 'routes': report.routes}, sort_keys=True)} -->"
    parts = [note, results_table(report), apps_table(report.apps), marker]
    rt.gh.create_check(head, STAGE1, conclusion="success" if outcome == PASS else "failure",
                       title=stage1_title(outcome), summary="\n\n".join(p for p in parts if p),
                       external_id=report.external_id)


def latest_check(rt, sha: str, name: str) -> dict | None:
    runs = rt.gh.check_runs(sha, rt.app_id, name)
    runs = [r for r in runs if r.get("name") == name]
    runs.sort(key=lambda r: (r.get("started_at") or "", r.get("id") or 0))
    return runs[-1] if runs else None


def parse_external_id(value: str | None) -> tuple[int, str] | None:
    if not value or "@" not in value:
        return None
    repo_id, _, sha = value.partition("@")
    if not repo_id.isdigit():
        return None
    try:
        return int(repo_id), validate.sha(sha)
    except validate.InvalidInput:
        return None


# --- labels ----------------------------------------------------------------------------

def pipeline_labels(outcome: str, failures: list[str], flagged: bool) -> set[str]:
    want = {f"stage1:{outcome}"}
    if outcome == FAIL:
        # Failures the contributor can't fix wait for the curator, not the author (S1-15).
        if set(failures) - {"S1-15"}:
            want.add("needs-author")
        if "S1-15" in failures:
            want.add("needs-owner")
    elif outcome == ROUTE:
        want.add("needs-owner")
    if flagged:
        want.add("needs-owner")
    return want


def apply_labels(rt, number: int, current: set[str], want: set[str], managed=PIPELINE_LABELS) -> set[str]:
    add = sorted(want - current)
    rt.gh.add_labels(number, add)
    for label in sorted((current & set(managed)) - want):
        rt.gh.remove_label(number, label)
    return (current - set(managed)) | want


# --- reading the PR --------------------------------------------------------------------

def entry_bytes_at(rt, path: str, ref: str) -> bytes | None:
    owner, name = rt.repo.split("/")
    item = rt.gh.contents(owner, name, path, ref)
    if item is None or item.get("type") != "file":
        return None
    if item.get("content") is None and item.get("download_url"):
        return None
    return decode_content(item)


def index_view(rt, state: store.State, entries: dict) -> IndexView:
    return IndexView(policy=rt.policy, schema=rt.entry_schema(), index_repo=rt.repo, entries=entries,
                     lifecycle=state.lifecycle, blocked=blocklist.hashes(state),
                     flagged=blocklist.flag_hashes(state), salt=rt.salt, owner_id=rt.owner_id)


def stage1_report(rt, pr: dict, cls, labels: set[str], state: store.State | None = None,
                  entries: dict | None = None) -> Report:
    state = state or store.State.load(rt.root)
    if entries is None:
        entries, _ = store.load_entries(rt.root)
    stem = cls.stem or ""
    valid = bool(validate.ENTRY_ID_RE.match(stem)) and len(stem) <= 64
    raw = None if cls.kind == ENTRY_REMOVE else entry_bytes_at(rt, cls.path, pr["head"]["sha"])
    subject = Subject(
        mode="gate", entry_id=stem, raw=raw, change=cls.change,
        author_id=pr["user"]["id"], author_login=pr["user"]["login"],
        old_entry=entries.get(stem) if valid else None,
        record=state.lifecycle.get(stem) if valid else None,
        health=state.health.get(stem) if valid else None,
        flagged_pr="stage2:flagged" in labels, owner_scan="owner:scan" in labels)
    return checks.run(subject, index_view(rt, state, entries), rt.gh, rt.http)


def entry_name(report: Report, fallback: str) -> str:
    entry = report.entry or {}
    return str(entry.get("name") or fallback)


# --- the gate --------------------------------------------------------------------------

def run(rt) -> list[int]:
    """Handle one pull_request_target event. Returns PR numbers for the merge step."""
    event = rt.event()
    pr = event["pull_request"]
    number = validate.pr_number(pr["number"])
    action = event.get("action")
    labels = {label["name"] for label in pr.get("labels") or []}

    if action == "labeled":
        label = (event.get("label") or {}).get("name")
        if label not in WATCHED_LABELS:
            return []
        if (event.get("sender") or {}).get("id") != rt.owner_id:
            rt.gh.remove_label(number, label)
            rt.gh.comment(number, "Only the maintainer can apply this label.")
            return []
        if label != "owner:scan":
            return []  # blocklist has its own job; kill-switch is an issue label
        if "stage2:flagged" in labels:
            rt.gh.remove_label(number, "stage2:flagged")
            labels.discard("stage2:flagged")
    elif action == "synchronize" and "owner:scan" in labels:
        rt.gh.remove_label(number, "owner:scan")
        labels.discard("owner:scan")

    head = pr["head"]["sha"]
    files = rt.gh.pr_files(number)
    cls = classify(files, pr["user"]["id"], pr["user"]["login"], rt.owner_id)
    if cls.kind == SKIP:
        return []
    rt.gh.create_check(head, POLICY_CHECK,
                       conclusion="failure" if cls.kind == INVALID else "success",
                       title="Entry PRs must change exactly one file under entries/ and nothing else."
                       if cls.kind == INVALID else f"Class: {cls.kind}",
                       summary="Entry PRs must change exactly one file under `entries/` and nothing else."
                       if cls.kind == INVALID else f"This PR is classified as `{cls.kind}`.")
    if cls.kind == INVALID:
        for name in (STAGE1, STAGE2):
            rt.gh.create_check(head, name, conclusion="failure", title="Not run (see gate/policy)",
                               summary="Fix gate/policy first.")
        if pr["user"]["id"] != rt.owner_id:
            apply_labels(rt, number, labels, {"needs-author"})
        return []
    if cls.kind == OWNER_ADMIN:
        for name in (STAGE1, STAGE2):
            rt.gh.create_check(head, name, conclusion="success", title="n/a (owner change)",
                               summary="Owner change; the owner merges it.")
        return []
    if cls.kind == OWNER_VERIFY:
        owner_verify(rt, pr, head)
        return []
    return entry_pr(rt, pr, cls, labels)


def entry_pr(rt, pr: dict, cls, labels: set[str]) -> list[int]:
    number, head = pr["number"], pr["head"]["sha"]
    state = store.State.load(rt.root)
    entries, _ = store.load_entries(rt.root)
    report = stage1_report(rt, pr, cls, labels, state, entries)
    name = entry_name(report, cls.stem or "this port")
    flagged = "stage2:flagged" in labels
    outcome = report.overall

    if cls.kind == ENTRY_REMOVE:
        if outcome == PASS:
            for check in (STAGE1, STAGE2):
                rt.gh.create_check(head, check, conclusion="success", title="Not required: self-removal",
                                   summary=results_table(report) if check == STAGE1 else "Self-removal needs no scan.")
            apply_labels(rt, number, labels, {"stage1:pass"})
            return [number]
        post_stage1(rt, head, report)
        apply_labels(rt, number, labels, pipeline_labels(outcome, report.failures, False))
        _render_stage1(rt, number, name, report)
        return []

    post_stage1(rt, head, report)
    labels = apply_labels(rt, number, labels, pipeline_labels(outcome, report.failures, flagged))
    bot = messages.find_bot_comment(rt, number)
    bot_state = messages.read_state(bot)

    if flagged:
        # §8.2 step 2: keep the flag on the new head; no new scan until the owner acts.
        scanned = bot_state.get("flagged")
        rt.gh.create_check(head, STAGE2, conclusion="failure", title=WAITING,
                           summary="The automated security review asked for a closer look. The curator "
                                   "decides; new pushes don't start another review.\n\n"
                                   + stage2_marker(kind="result", result="flag"),
                           external_id=scanned)
        text = messages.render("flag", rt.root, name=name, repo=bot_state.get("flag_repo") or "this repo",
                               pointers=bot_state.get("flag_pointers") or [],
                               rows=messages.fail_rows(report.results))
        messages.upsert(rt, number, text)
        return []

    if outcome != PASS:
        for label in ("stage2:queued",):
            if label in labels:
                rt.gh.remove_label(number, label)
        _render_stage1(rt, number, name, report)
        return []

    ext = report.external_id
    sha12 = (report.head or "")[:12]
    record_health = state.health.get(cls.stem) or {}
    repo_changed = bool(report.repo and (state.lifecycle.get(cls.stem) or {}).get("repo_id") not in (None, report.repo["id"]))
    if "stage2:scanning" in labels and bot_state.get("scanning") == ext:
        rt.gh.create_check(head, STAGE2, status="in_progress", title="Security review in progress",
                           summary="The automated security review of this commit is running.", external_id=ext)
        return []
    if cls.kind != ENTRY_ADD and not repo_changed and report.head == record_health.get("scanned_commit"):
        _clear(rt, number, labels, ("stage2:queued",))
        rt.gh.create_check(head, STAGE2, conclusion="success",
                           title=f"Not required: unchanged since last scan ({sha12})",
                           summary="The linked repo hasn't changed since its last scan.\n\n"
                                   + stage2_marker(kind="unchanged"), external_id=ext)
        return [number]
    passed = bot_state.get("passed") or {}
    if ext in passed:
        _clear(rt, number, labels, ("stage2:queued",))
        rt.gh.add_labels(number, ["stage2:pass"] if "stage2:pass" not in labels else [])
        rt.gh.create_check(head, STAGE2, conclusion="success", title=f"Carried forward from {sha12}",
                           summary="An earlier review on this PR passed this exact commit.\n\n"
                                   + stage2_marker(kind="scan", confidence=passed[ext]), external_id=ext)
        return [number]
    if pr.get("draft"):
        rt.gh.create_check(head, STAGE2, status="in_progress", title="Waiting until the PR is marked ready",
                           summary="Draft PRs run Stage 1 but aren't queued for the security review.")
        return []
    if "stage2:queued" not in labels:
        rt.gh.add_labels(number, ["stage2:queued"])
    _clear(rt, number, labels, ("stage2:pass",))
    rt.gh.create_check(head, STAGE2, status="in_progress", title="Queued for the security review",
                       summary="Queued, first come, first served.", external_id=ext)
    position, eta = queue_position(rt, number)
    messages.upsert(rt, number, messages.render("queued", rt.root, name=name, n=position, eta=eta))
    return []


def _clear(rt, number: int, labels: set[str], names: tuple[str, ...]) -> None:
    for label in names:
        if label in labels:
            rt.gh.remove_label(number, label)


def _render_stage1(rt, number: int, name: str, report: Report) -> None:
    if report.overall == FAIL:
        text = messages.render("stage1-fail", rt.root, name=name, rows=messages.fail_rows(report.results))
    else:
        text = messages.render("route", rt.root, name=name, reasons=messages.route_reasons(report.routes),
                               apps=apps_table(report.apps))
    messages.upsert(rt, number, text)


def queue_position(rt, number: int) -> tuple[int, str]:
    from .queue import eta_text, queued_prs
    order = [p["number"] for p in queued_prs(rt)]
    if number not in order:
        order.append(number)
    position = order.index(number) + 1
    return position, eta_text(position, rt.policy["stage2"]["hourly_cap"])


# --- owner verification ------------------------------------------------------------------

def owner_verify(rt, pr: dict, head: str) -> None:
    raw = entry_bytes_at(rt, VERIFY_FILE, head)
    problems: list[str] = []
    try:
        new = validate.load_untrusted_yaml(raw or b"", max_bytes=256 * 1024) if raw is not None else None
        schema = store.load_json("schema/owner-verified.schema.json", rt.root)
        jsonschema.Draft202012Validator(schema).validate(new)
    except validate.YamlError as exc:
        problems.append(str(exc))
        new = None
    except jsonschema.ValidationError as exc:
        problems.append(exc.message[:300])
        new = None
    state = store.State.load(rt.root)
    if new is not None:
        old_records = (state.verified.get("records") or {})
        for entry_id, rec in sorted((new.get("records") or {}).items()):
            if old_records.get(entry_id) == rec:
                continue
            problems.extend(verify_problems(state, entry_id, rec))
    if problems:
        rt.gh.create_check(head, STAGE1, conclusion="failure", title="Verification record problem",
                           summary="\n".join(f"- {validate.md_inline(p, 400)}" for p in problems))
    else:
        rt.gh.create_check(head, STAGE1, conclusion="success", title="Verification records check out",
                           summary="Every added or changed record matches its entry.")
    rt.gh.create_check(head, STAGE2, conclusion="success", title="Skipped: owner verification",
                       summary="Owner verification needs no scan.")


def verify_problems(state: store.State, entry_id: str, rec: dict) -> list[str]:
    record = state.lifecycle.get(entry_id) or {}
    if record.get("status") != "listed":
        return [f"{entry_id} isn't currently listed, so it can't be verified."]
    out = []
    if rec.get("repo_id") != record.get("repo_id"):
        out.append(f"repo_id for {entry_id} doesn't match the repo it currently links. "
                   "Verify the repo users are pointed at.")
    scanned = (state.health.get(entry_id) or {}).get("scanned_commit")
    if rec.get("verified_commit") != scanned:
        out.append(f"verified_commit for {entry_id} doesn't match its scanned commit {scanned}. "
                   "Verify the commit users are pointed at.")
    return out


# --- the blocklist label -----------------------------------------------------------------

def blocklist_label(rt) -> None:
    """The owner applied `blocklist` to an entry PR: block the linked repo, close, explain."""
    event = rt.event()
    if (event.get("label") or {}).get("name") != "blocklist" or (event.get("sender") or {}).get("id") != rt.owner_id:
        return
    pr = event["pull_request"]
    number = validate.pr_number(pr["number"])
    files = rt.gh.pr_files(number)
    cls = classify(files, pr["user"]["id"], pr["user"]["login"], rt.owner_id)
    repo = None
    url_name = None
    if cls.kind in ENTRY_CLASSES and cls.kind != ENTRY_REMOVE:
        raw = entry_bytes_at(rt, cls.path, pr["head"]["sha"])
        try:
            entry = validate.load_untrusted_yaml(raw or b"")
            owner, name = validate.parse_repo_url(entry["repo"])
            url_name = f"{owner}/{name}"
            repo = rt.gh.repo(owner, name)
        except (validate.YamlError, validate.InvalidInput, KeyError, TypeError):
            entry = None
    slug = cls.stem if cls.kind == ENTRY_ADD and cls.stem and validate.ENTRY_ID_RE.match(cls.stem) else None

    def mutate() -> None:
        state = store.State.load(rt.root)
        blocklist.block(state, rt.salt, repo_id=repo["id"] if repo else None,
                        repo_name=None, entry_id=slug)
        for full_name in {n for n in (url_name, repo["full_name"] if repo else None) if n}:
            blocklist.block(state, rt.salt, repo_id=None, repo_name=full_name)
        state.save()

    if repo or url_name or slug:
        rt.commit(mutate, f"blocklist: PR #{number}")
    rt.gh.close_pr(number)
    link = f"https://github.com/{rt.repo}/issues/new?template=appeal.yml"
    messages.upsert(rt, number, messages.render("blocklisted", rt.root, link=link))
