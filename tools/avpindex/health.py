"""The daily health check (spec §8.6): keep listed entries honest, contact developers when
something breaks, and delist entries that stay broken while keeping a public record.
"""

from __future__ import annotations

import datetime as dt
import re

from . import checks, gate, lifecycle, messages, store, validate
from .checks import GitHubError
from .checks import FIXES, PASS, Subject
from .lifecycle import DECAY, LISTED, PULLED, TAKEN_DOWN, WITHDRAWN
from .sync import repo_facts, sync_all

ISSUE_URL = re.compile(r"^https://github\.com/([A-Za-z0-9-]+/[A-Za-z0-9._-]+)/issues/(\d+)(#issuecomment-\d+)?$")
STALE_NOTE = ("Closing this for now, since it has been quiet for {days} days. Reopening it reruns the checks, "
              "and the curator is happy to help if something is unclear.")


def clear_outreach(health: dict) -> None:
    health["outreach_issue_url"] = None
    health["outreach_opened_at"] = None


class Outreach:
    """Outreach issues live on the contributor's repo (opened with OUTREACH_PAT), or, when that's
    impossible, as a comment on the index's "Health tracking" issue."""

    def __init__(self, rt):
        self.rt = rt

    def is_fallback(self, url: str) -> bool:
        match = ISSUE_URL.match(url or "")
        return bool(match and match.group(1).lower() == self.rt.repo.lower())

    def follow_up(self, url: str, body: str, *, close: bool) -> None:
        if not url:
            return
        if self.is_fallback(url):
            self.rt.health_comment(body)
            return
        match = ISSUE_URL.match(url)
        if not match:
            return
        repo, number = match.group(1), int(match.group(2))
        token = self.rt.outreach_token
        try:
            self.rt.once(f"outreach-comment:{url}:{hash(body)}",
                         lambda: self.rt.gh.comment(number, body, repo=repo, token=token))
            if close:
                self.rt.once(f"outreach-close:{url}", lambda: self.rt.gh.close_issue(number, repo=repo, token=token))
        except GitHubError as exc:
            # The repo was deleted or archived, the issue locked, or the bot blocked: note it here
            # instead, so one unreachable issue never stops the daily check.
            self.rt.health_comment(f"Couldn't update {url} (HTTP {exc.status}); posting here instead.\n\n{body}")

    def open(self, entry_id: str, entry: dict, repo: dict | None, report, state: store.State,
             removal: str) -> str | None:
        rt = self.rt
        items = [{"problem": f"{r.id}: {r.detail or 'failed'}", "fix": FIXES.get(r.id, "")}
                 for r in report.results if r.effective == "fail"]
        name = entry.get("name", entry_id)
        body = messages.render("outreach", rt.root, name=name, items=items, date=removal, owner_login=rt.owner_login)
        title = messages.render("outreach-title.txt", rt.root, name=name)
        if repo and not repo.get("archived") and repo.get("has_issues", True) and rt.outreach_token:
            try:
                created = rt.once(f"outreach:{entry_id}", lambda: rt.gh.create_issue(
                    title, body, repo=repo["full_name"], token=rt.outreach_token))
            except GitHubError:
                created = None  # for example, the repo's owner blocked the bot
            if created and created.get("html_url"):
                return created["html_url"]
            if rt.dry_run:
                return None
        # Fallback: the "Health tracking" issue, mentioning the submitter (and the developer
        # only when the credit is verified, since contributors write that field themselves).
        record = state.lifecycle.get(entry_id) or {}
        mentions = []
        submitter = rt.gh.user_by_id(record["submitted_by_id"]) if record.get("submitted_by_id") else None
        if submitter:
            mentions.append(f"@{submitter['login']}")
        dev = (entry.get("developer") or {}).get("github")
        if dev and (state.health.get(entry_id) or {}).get("github_verified") and f"@{dev}" not in mentions:
            mentions.append(f"@{dev}")
        lead = (" ".join(mentions) + ": " if mentions else "") + \
            f"`{entry_id}` needs attention, and its repo can't take an issue.\n\n"
        return rt.health_comment(lead + body)


def run(rt) -> None:
    policy = rt.policy["health"]
    outreach = Outreach(rt)

    def mutate() -> None:
        state = store.State.load(rt.root)
        sync_all(rt, state)
        entries, parse_errors = store.load_entries(rt.root)
        index = gate.index_view(rt, state, entries)
        now = store.utcnow()
        budget = int(policy["outreach_max_per_run"])
        for entry_id, record in sorted(state.lifecycle.items()):
            if record.get("status") != LISTED:
                continue
            path = store.entry_path(entry_id, rt.root)
            if not path.exists():
                continue  # reconcile opened a triage issue
            subject = Subject(mode="health", entry_id=entry_id, raw=path.read_bytes(), change="listed",
                              record=record, health=state.health.get(entry_id))
            report = checks.run(subject, index, rt.gh, rt.http)
            health = state.health_record(entry_id)
            health["last_checked"] = store.iso(now)
            hard = [r for r in report.results if r.id in ("S1-05", "S1-16") and r.outcome != PASS]
            if hard:
                lifecycle.transition(state, entry_id, PULLED, "health")
                rt.upsert_triage(entry_id, f"The health check pulled `{entry_id}`: "
                                           + "; ".join(f"{r.id} {r.detail}" for r in hard)
                                           + ". `restore` re-records the repo if it's legitimate.")
                rt.summary(f"{entry_id}: pulled ({', '.join(r.id for r in hard)})")
                continue
            entry = report.entry or entries.get(entry_id) or {}
            if report.repo and report.head:
                repo_facts(rt, entry_id, entry, report.repo, state)
            if report.license:
                health["license"] = report.license
            routes = sorted(report.routes)
            warnings = sorted({cid for cid, _ in report.warnings})
            if routes != sorted(health.get("routes") or []) or warnings != sorted(health.get("warnings") or []):
                if routes or warnings:
                    lines = [f"`{entry_id}`: routes {', '.join(routes) or 'none'}; warnings {', '.join(warnings) or 'none'}."]
                    lines += [f"- {cid}: {validate.md_inline(text, 300)}" for cid, text in report.warnings]
                    rt.health_comment("\n".join(lines))
            health["routes"], health["warnings"] = routes, warnings
            failures = report.failures
            if failures:
                budget -= decay(rt, outreach, state, entry_id, entry, report, now, policy, budget)
            else:
                recover(rt, outreach, health, entry.get("name", entry_id), entry_id)
            rt.summary(f"{entry_id}: {'failing ' + ', '.join(failures) if failures else 'ok'}"
                       f"{'; routes ' + ', '.join(routes) if routes else ''}")
        for entry_id, record in sorted(state.lifecycle.items()):
            health = state.health.get(entry_id) or {}
            if record.get("status") in (PULLED, TAKEN_DOWN, WITHDRAWN) and health.get("outreach_issue_url"):
                name = (entries.get(entry_id) or {}).get("name", entry_id)
                outreach.follow_up(health["outreach_issue_url"],
                                   messages.render("outreach-closed", rt.root, name=name), close=True)
                clear_outreach(health)
        for stem, error in parse_errors.items():
            rt.summary(f"entries/{stem}.yaml can't be parsed: {error}")
        state.save()

    rt.commit(mutate, "health: daily check")
    close_stale_prs(rt)


def decay(rt, outreach: Outreach, state: store.State, entry_id: str, entry: dict, report, now: dt.datetime,
          policy: dict, budget: int) -> int:
    """Stages A to C. Returns how many outreach issues it opened (0 or 1)."""
    health = state.health_record(entry_id)
    health["consecutive_failures"] = int(health.get("consecutive_failures") or 0) + 1
    health["failures"] = report.failures
    health["health"] = "issues"
    health["failing_since"] = health.get("failing_since") or store.iso(now)
    confirm = int(policy["confirm_runs_before_outreach"])
    if health["consecutive_failures"] < confirm:
        return 0
    if not health.get("outreach_issue_url"):
        if budget <= 0:
            return 0
        removal = (now + dt.timedelta(days=int(policy["grace_days"]))).date().isoformat()
        url = outreach.open(entry_id, entry, report.repo, report, state, removal)
        if url:
            health["outreach_issue_url"] = url
            health["outreach_opened_at"] = store.iso(now)
        return 1
    start = store.parse_iso(health["outreach_opened_at"]) if health.get("outreach_opened_at") else now
    if health.get("decay_reset_at"):
        start = max(start, store.parse_iso(health["decay_reset_at"]))
    if start >= now:
        return 0  # Stage C only in a run after the one that reached Stage B
    if now >= start + dt.timedelta(days=int(policy["grace_days"])):
        lifecycle.transition(state, entry_id, DECAY, "health")
        outreach.follow_up(health["outreach_issue_url"],
                           messages.render("delisted", rt.root, name=entry.get("name", entry_id)), close=True)
        clear_outreach(health)
    return 0


def recover(rt, outreach: Outreach, health: dict, name: str, entry_id: str) -> None:
    health.update({"health": "ok", "failing_since": None, "consecutive_failures": 0, "failures": []})
    if health.get("outreach_issue_url"):
        outreach.follow_up(health["outreach_issue_url"], messages.render("outreach-resolved", rt.root), close=True)
        clear_outreach(health)


def close_stale_prs(rt) -> None:
    days = int(rt.policy["stale_pr_close_days"])
    cutoff = store.utcnow() - dt.timedelta(days=days)
    for issue in rt.gh.issues(labels="needs-author", state="open"):
        if "pull_request" not in issue:
            continue
        labels = {label["name"] for label in issue.get("labels") or []}
        if labels & {"needs-owner", "stage2:flagged"}:
            continue  # waiting for the curator, not the author
        if store.parse_iso(issue["updated_at"]) < cutoff:
            rt.gh.comment(issue["number"], STALE_NOTE.format(days=days))
            rt.gh.close_pr(issue["number"])
            rt.summary(f"closed stale PR #{issue['number']}")
