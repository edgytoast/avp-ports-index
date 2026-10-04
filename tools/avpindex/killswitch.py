"""The kill switch (spec §8.7) and report intake (spec §8.8)."""

from __future__ import annotations

import os
import re

from . import blocklist, lifecycle, store, validate
from .lifecycle import DECAY, LISTED, PULLED, TAKEN_DOWN, WITHDRAWN
from .sync import pin, repo_facts, sync_all
from .writer import git, git_bytes

ACTIONS = ("pull", "restore", "takedown", "approve")
FORM_FIELD = re.compile(r"^###\s*Entry id\s*$\n+(.+?)\s*$", re.M | re.I)

ACKS = {
    "report": "Thanks for letting us know. The curator has been notified, and credible security reports are "
              "pulled first and investigated after.",
    "takedown": "Thanks for getting in touch. The curator has been notified and acts on valid requests promptly. "
                "This issue is public, so please use admin@trevorbilt.com for anything you'd rather keep private.",
    "appeal": "Thanks for the appeal. The curator has been notified and will take another look.",
}


def parse_form_entry_id(body: str | None) -> str | None:
    match = FORM_FIELD.search(body or "")
    return match.group(1).strip() if match else None


def request_from_env(rt) -> tuple[str | None, str, bool, int | None]:
    """(raw entry id, action, blocklist, issue number) from a dispatch or an issue label event."""
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        action = validate.choice(os.environ.get("INPUT_ACTION"), ACTIONS, "action")
        return os.environ.get("INPUT_ENTRY_ID"), action, validate.boolean(os.environ.get("INPUT_BLOCKLIST", "false")), None
    event = rt.event()
    if (event.get("label") or {}).get("name") != "kill-switch" or (event.get("sender") or {}).get("id") != rt.owner_id:
        return None, "", False, None
    issue = event["issue"]
    return parse_form_entry_id(issue.get("body")), "pull", False, validate.issue_number(issue["number"])


def run(rt) -> str:
    raw_id, action, block, issue_number = request_from_env(rt)
    if not action:
        return "ignored"

    def say(text: str) -> str:
        rt.summary(text)
        if issue_number:
            rt.once(f"ks-say:{text}", lambda: rt.gh.comment(issue_number, text))
        return text

    try:
        entry_id = validate.entry_id(raw_id)
    except validate.InvalidInput:
        return say("The kill switch did nothing: that isn't a valid entry id.")
    outcome: dict = {}

    def mutate() -> None:
        outcome.clear()
        state = store.State.load(rt.root)
        sync_all(rt, state)
        status = state.status(entry_id)
        if status is None:
            outcome["note"] = f"The kill switch did nothing: there's no entry `{entry_id}`."
        elif action == "pull":
            pull(rt, state, entry_id, block, outcome)
        elif action == "restore":
            restore(rt, state, entry_id, outcome)
        elif action == "approve":
            approve(rt, state, entry_id, outcome)
        elif action == "takedown":
            takedown(rt, state, entry_id, outcome)
        state.save()

    rt.commit(mutate, f"kill-switch: {action} {entry_id}")
    for side in outcome.get("after", []):
        side()
    return say(outcome.get("note") or f"Kill switch: {action} `{entry_id}` done.")


def _repo(rt, state: store.State, entry_id: str, entry: dict | None) -> dict | None:
    if entry and entry.get("repo"):
        try:
            owner, name = validate.parse_repo_url(entry["repo"])
            found = rt.gh.repo(owner, name)
            if found:
                return found
        except validate.InvalidInput:
            pass
    repo_id = (state.lifecycle.get(entry_id) or {}).get("repo_id")
    return rt.gh.repo_by_id(repo_id) if repo_id else None


def _entry(rt, entry_id: str) -> dict | None:
    path = store.entry_path(entry_id, rt.root)
    if not path.exists():
        return None
    try:
        data = validate.load_untrusted_yaml(path.read_bytes())
    except validate.YamlError:
        return None
    return data if isinstance(data, dict) else None


def _names(state: store.State, entry_id: str, entry: dict | None, repo: dict | None) -> tuple[str, ...]:
    names = set()
    for url in ((entry or {}).get("repo"), (state.lifecycle.get(entry_id) or {}).get("repo")):
        if url:
            try:
                owner, name = validate.parse_repo_url(url)
                names.add(f"{owner}/{name}")
            except validate.InvalidInput:
                pass
    if repo:
        names.add(repo["full_name"])
    return tuple(sorted(names))


def pull(rt, state: store.State, entry_id: str, block: bool, outcome: dict) -> None:
    status = state.status(entry_id)
    if status not in (LISTED, DECAY):
        outcome["note"] = f"The kill switch did nothing: `{entry_id}` is {status}."
        return
    lifecycle.transition(state, entry_id, PULLED, "kill-switch")
    if block:
        entry = _entry(rt, entry_id)
        repo = _repo(rt, state, entry_id, entry)
        _block_all(rt, state, entry_id, entry, repo)


def _block_all(rt, state, entry_id, entry, repo) -> None:
    repo_id = repo["id"] if repo else (state.lifecycle.get(entry_id) or {}).get("repo_id")
    blocklist.block(state, rt.salt, repo_id=repo_id, repo_name=None, entry_id=entry_id)
    for name in _names(state, entry_id, entry, repo):
        blocklist.block(state, rt.salt, repo_id=None, repo_name=name)


def _restore_file(rt, entry_id: str) -> bool:
    rel = f"entries/{entry_id}.yaml"
    deleted = git(rt.root, "log", "--diff-filter=D", "--format=%H", "-1", "--", rel).strip()
    if not deleted:
        return False
    data = git_bytes(rt.root, "show", f"{deleted}^:{rel}")
    if data is None:
        return False
    (rt.root / rel).write_bytes(data)
    return True


def restore(rt, state: store.State, entry_id: str, outcome: dict) -> None:
    status = state.status(entry_id)
    health = state.health_record(entry_id)
    if status == LISTED:
        health["rescan_hold"] = False
        health["rescan_after"] = None  # the owner asked for rescans to resume
        state.lifecycle[entry_id]["owner_approved"] = True
    elif status in (PULLED, TAKEN_DOWN):
        if status == TAKEN_DOWN and not _restore_file(rt, entry_id):
            outcome["note"] = f"The kill switch couldn't find `{entry_id}`'s file in history."
            return
        entry = _entry(rt, entry_id)
        repo = _repo(rt, state, entry_id, entry)
        blocklist.unblock(state, rt.salt, repo_id=repo["id"] if repo else state.lifecycle[entry_id].get("repo_id"),
                          repo_names=_names(state, entry_id, entry, repo), entry_id=entry_id)
        fields = {"owner_approved": True}
        if repo:
            fields["repo_id"] = repo["id"]
        lifecycle.transition(state, entry_id, LISTED, "kill-switch", **fields)
        health["rescan_hold"] = False
        health["rescan_after"] = None
        if repo and entry:
            repo_facts(rt, entry_id, entry, repo, state)
    else:
        outcome["note"] = f"The kill switch did nothing: `{entry_id}` is {status}; restore works on pulled, " \
                          "taken-down or held entries."
        return
    rt.close_triage(entry_id, "Restored by the curator.")


def approve(rt, state: store.State, entry_id: str, outcome: dict) -> None:
    status = state.status(entry_id)
    if status == PULLED:
        restore(rt, state, entry_id, outcome)
        if outcome.get("note"):
            return
        status = state.status(entry_id)
    if status != LISTED:
        outcome["note"] = f"The kill switch did nothing: `{entry_id}` is {status}."
        return
    health = state.health_record(entry_id)
    record = state.lifecycle[entry_id]
    repo_id = record.get("repo_id")
    flagged_commit = health.get("flagged_commit")
    has_flag = bool(repo_id) and blocklist.is_flagged(state, rt.salt, repo_id)
    if not flagged_commit and not has_flag:
        outcome["note"] = f"The kill switch did nothing: `{entry_id}` has no flagged commit or flag record."
        return
    if flagged_commit:
        repo = rt.gh.repo_by_id(repo_id) if repo_id else None
        pin(rt, state, entry_id, flagged_commit, "curator-reviewed", None, repo)
    if repo_id:
        blocklist.remove_flag(state, rt.salt, repo_id)
    record["owner_approved"] = True
    rt.close_triage(entry_id, "Approved by the curator.")


def takedown(rt, state: store.State, entry_id: str, outcome: dict) -> None:
    status = state.status(entry_id)
    if status == TAKEN_DOWN:
        outcome["note"] = f"The kill switch did nothing: `{entry_id}` is already taken down."
        return
    entry = _entry(rt, entry_id)
    repo = _repo(rt, state, entry_id, entry)
    lifecycle.transition(state, entry_id, TAKEN_DOWN, "kill-switch")
    _block_all(rt, state, entry_id, entry, repo)
    path = store.entry_path(entry_id, rt.root)
    if path.exists():
        path.unlink()


def intake(rt) -> None:
    """Acknowledge a report, takedown request or appeal; label it triage; assign the curator."""
    event = rt.event()
    issue = event.get("issue") or {}
    number = validate.issue_number(issue.get("number"))
    labels = {label["name"] for label in issue.get("labels") or []}
    kind = next((k for k in ("report", "takedown", "appeal") if k in labels), None)
    if kind is None:
        return
    rt.gh.comment(number, ACKS[kind])
    rt.gh.add_labels(number, ["triage"])
    rt.gh.assign(number, [rt.owner_login])


__all__ = ["run", "intake", "parse_form_entry_id", "WITHDRAWN"]
