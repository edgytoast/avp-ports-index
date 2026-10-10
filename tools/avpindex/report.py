"""The stage2-scan report job (spec §8.4, §6.3): apply a scan result in PR or rescan mode.

It runs with if: always(), so a failed, cancelled or timed-out scan job still produces an
`error` here and no PR is left at stage2:scanning. A `declined` scan (Jules refused to review,
decision 63) never passes: a rescan is retried soon, a PR goes back in the queue until its scans
run out.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import approvals, blocklist, jules, lifecycle, messages, store, validate
from .gate import STAGE1, STAGE2, WAITING, latest_check, stage2_marker
from .lifecycle import LISTED, PULLED
from .sync import pin

DECLINE_RETRY = dt.timedelta(hours=2)    # a declined rescan is tried again this soon,
DECLINE_QUICK_TRIES = 3                  # until it has declined this many times in a row;
ERROR_RETRY = dt.timedelta(hours=24)     # then it waits as long as after an error


@dataclass
class Inputs:
    mode: str
    pr: int | None
    head_sha: str | None
    linked_repo: str
    linked_commit: str
    entry_id: str | None
    repo_id: int
    base_commit: str | None
    counted: bool

    @classmethod
    def from_env(cls) -> "Inputs":
        env = os.environ
        mode = validate.choice(env.get("INPUT_MODE"), ("pr", "rescan"), "mode")
        return cls(
            mode=mode,
            pr=validate.pr_number(env.get("INPUT_PR")) if mode == "pr" else None,
            head_sha=validate.sha(env.get("INPUT_HEAD_SHA")) if mode == "pr" else None,
            linked_repo=validate.repo_name(env.get("INPUT_LINKED_REPO")),
            linked_commit=validate.sha(env.get("INPUT_LINKED_COMMIT")),
            entry_id=validate.entry_id(env.get("INPUT_ENTRY_ID")) if env.get("INPUT_ENTRY_ID") else None,
            repo_id=validate.positive_int(env.get("INPUT_REPO_ID"), "repo id"),
            base_commit=validate.sha(env.get("INPUT_BASE_COMMIT")) if mode == "rescan" else None,
            counted=validate.boolean(env.get("INPUT_COUNTED", "false")),
        )

    @property
    def external_id(self) -> str:
        return f"{self.repo_id}@{self.linked_commit}"

    @property
    def repo_url(self) -> str:
        return f"https://github.com/{self.linked_repo}"


def load_outcome(path: Path, scan_result: str, policy: dict) -> dict:
    """Read the scan artifact. Anything missing or malformed is an error."""
    if scan_result != "success" or not path.is_file():
        return {"result": "error", "reason": f"the scan job ended {scan_result or 'without a result'}"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {"result": "error", "reason": "the scan artifact couldn't be read"}
    if not isinstance(data, dict):
        return {"result": "error", "reason": "the scan artifact couldn't be read"}
    result = data.get("result")
    if result == "deferred":
        return {"result": "deferred", "reason": data.get("reason", "")}
    if result == "declined":
        # Jules refused to review. Whatever else the artifact holds, this is never a verdict or a pass.
        return {"result": "declined", "reason": str(data.get("reason") or "")[:jules.EXCERPT_CHARS],
                "session_url": data.get("session_url"), "minutes": data.get("minutes")}
    verdict, problem = jules.check_verdict(json.dumps(data.get("verdict")) if data.get("verdict") else None,
                                           jules.verdict_schema())
    out = {"result": "error", "reason": data.get("reason") or problem, "session_url": data.get("session_url"),
           "minutes": data.get("minutes")}
    if verdict is not None:
        out.update(result=jules.decide(verdict, int(policy["stage2"]["confidence_threshold"])), verdict=verdict,
                   reason="")
    return out


def decline_summary(outcome: dict) -> str:
    return "\n".join(["Jules declined to review this repository, so there is no verdict. Its reply (untrusted text):",
                      "", validate.fence(outcome.get("reason") or "(no message)")])


def verdict_summary(outcome: dict, threshold: int) -> str:
    if outcome.get("result") == "declined":
        return decline_summary(outcome)
    verdict = outcome.get("verdict")
    if not verdict:
        return f"No valid verdict: {validate.md_inline(outcome.get('reason') or 'unknown error', 300)}"
    lines = [f"**Confidence:** {verdict['safe_confidence']} (threshold {threshold})",
             f"**Steering attempt:** {'yes' if verdict['steering_attempt'] else 'no'}", "",
             "Summary from the automated review (untrusted text):", "", validate.fence(verdict.get("summary", "")), ""]
    findings = verdict.get("findings") or []
    cleared = outcome.get("approved_files") or []
    if cleared:
        files = ", ".join(f"`{validate.md_inline(f['path'], 200)}` (SHA-256 `{f['sha256'][:12]}`)" for f in cleared)
        lines += ["", f"**Passed on approved files:** every finding above info is on a file the curator approved "
                      f"with these exact bytes: {files}.", ""]
    if findings:
        rows = []
        for f in findings[:50]:
            where = f.get("file", "") + (f":{f['line']}" if f.get("line") is not None else "")
            rows.append(f"- [{f.get('severity')}] {where} ({f.get('category', '')}): {f.get('explanation', '')}")
        lines += ["Findings (untrusted text):", "", validate.fence("\n".join(rows))]
    else:
        lines.append("No findings.")
    return "\n".join(lines)


def triage_body(inputs: Inputs, outcome: dict, threshold: int, what: str) -> str:
    session = outcome.get("session_url")
    return "\n".join([
        f"**{what}** for `{inputs.entry_id}` ({inputs.linked_repo} at `{inputs.linked_commit}`).", "",
        verdict_summary(outcome, threshold), "",
        f"Jules session (opens for the owner's account only): {session}" if session else "No Jules session link.",
        "", "Kill switch actions: `restore` (relist or resume rescans at the current pin), "
            "`approve` (accept the flagged commit), `pull`, `takedown`.",
    ])


def decline_body(inputs: Inputs, outcome: dict, declines: int, retry_at: dt.datetime) -> str:
    """The triage note for a declined rescan (spec §6.3)."""
    session = outcome.get("session_url")
    when = store.iso(retry_at)
    if declines < DECLINE_QUICK_TRIES:
        plan = (f"Jules turns a review down now and then. The rescan will try again after {when} "
                f"({declines} decline{'s' if declines > 1 else ''} in a row). The entry stays listed at the commit "
                "already reviewed; nothing to do.")
    else:
        plan = (f"That's {declines} declines in a row, so it now waits a day between tries: the next is after "
                f"{when}. You may want to look: open the session below, or review the commit yourself. The entry "
                "stays listed at the commit already reviewed. Kill switch `rescan` resets the count and tries "
                "again at once; it changes nothing else.")
    return "\n".join([
        (f"**Jules declined to review** the new commit of `{inputs.entry_id}` ({inputs.linked_repo} at "
         f"`{inputs.linked_commit}`)."), "", plan, "", "Jules's reply (untrusted text):", "",
        validate.fence(outcome.get("reason") or "(no message)"), "",
        f"Jules session (opens for the owner's account only): {session}" if session else "No Jules session link.",
    ])


def apply_rescan_flag(rt, state: store.State, inputs: Inputs, outcome: dict, threshold: int) -> None:
    """The rescan-mode flag effects (spec §6.3), also used for a PR flag on a same-repo edit."""
    entry_id = inputs.entry_id
    health = state.health_record(entry_id)
    health["flagged_commit"] = inputs.linked_commit
    health["flagged_files"] = approvals.flagged_files(outcome.get("verdict")) or []
    health["rescan_hold"] = True
    health["scan_declines"] = 0  # Jules did review this commit
    blocklist.add_flag(state, rt.salt, inputs.repo_id)
    record = state.lifecycle[entry_id]
    if not record.get("owner_approved") and record.get("status") == LISTED:
        lifecycle.transition(state, entry_id, PULLED, "stage2")
        what = "Automated review flagged a new commit; the entry was pulled"
    else:
        what = "Automated review flagged a new commit; the entry stays listed at the commit you reviewed"
    rt.upsert_triage(entry_id, triage_body(inputs, outcome, threshold, what))


def run(rt, inputs: Inputs, outcome: dict) -> tuple[str, list[int]]:
    """Apply the result. Returns (result, PR numbers for the merge step)."""
    threshold = int(rt.policy["stage2"]["confidence_threshold"])
    outcome = clear_approved(rt, inputs, outcome)
    result = outcome["result"]
    if inputs.mode == "rescan":
        rescan(rt, inputs, outcome, threshold)
        return result, []
    return result, pr_mode(rt, inputs, outcome, threshold)


def clear_approved(rt, inputs: Inputs, outcome: dict) -> dict:
    """A flag whose findings above info are all on files the curator approved, byte for byte, is a pass
    (decision 62). A changed file, any other finding or any failure to check keeps the flag."""
    if outcome.get("result") != "flag":
        return outcome
    state = store.State.load(rt.root)
    cleared = approvals.clearance(state, inputs.entry_id, inputs.repo_id, inputs.linked_repo, inputs.linked_commit,
                                  outcome.get("verdict"), rt.policy, rt.http)
    if cleared is None:
        return outcome
    rt.summary(f"Flag cleared: {len(cleared)} curator-approved file(s) with unchanged SHA-256.")
    return {**outcome, "result": "pass", "approved_files": cleared}


def pr_mode(rt, inputs: Inputs, outcome: dict, threshold: int) -> list[int]:
    number = inputs.pr
    result = outcome["result"]
    pr = rt.gh.pr(number)
    labels = {label["name"] for label in pr.get("labels") or []}
    bot_state = messages.read_state(messages.find_bot_comment(rt, number))
    mine = bot_state.get("scanning") in (None, inputs.external_id)
    increment = 1 if inputs.counted and result in ("pass", "flag", "error") else 0  # a decline isn't their fault
    scans = int(bot_state.get("scans") or 0) + increment
    clear_scanning = {"scanning": None} if mine else {}

    def swap(remove: tuple[str, ...], add: tuple[str, ...]) -> None:
        for label in remove:
            if label in labels:
                rt.gh.remove_label(number, label)
        rt.gh.add_labels(number, [a for a in add if a not in labels])

    if result == "deferred":
        if pr.get("state") == "open" and mine:
            swap(("stage2:scanning",), ("stage2:queued",))
        return []
    if result == "declined":
        return _pr_declined(rt, inputs, outcome, pr, bot_state, scans, mine, swap)
    if result == "flag":
        _record_flag(rt, inputs, outcome, threshold)
    if pr.get("state") != "open":
        messages.upsert(rt, number, scans=scans, **clear_scanning)
        return []
    head = pr["head"]["sha"]
    current = (latest_check(rt, head, STAGE1) or {}).get("external_id")
    summary = verdict_summary(outcome, threshold)

    if result == "pass":
        confidence = outcome["verdict"]["safe_confidence"]
        passed = dict(bot_state.get("passed") or {})
        passed[inputs.external_id] = confidence
        if current != inputs.external_id:
            if mine:
                swap(("stage2:scanning",), ("stage2:queued",))
            messages.upsert(rt, number, scans=scans, passed=passed, **clear_scanning)
            return []
        title = (f"Passed: confidence {confidence}, findings only on curator-approved files"
                 if outcome.get("approved_files") else f"Passed: confidence {confidence} (threshold {threshold})")
        rt.gh.create_check(head, STAGE2, conclusion="success", title=title,
                           summary=summary + "\n\n" + stage2_marker(kind="scan", confidence=confidence),
                           external_id=inputs.external_id)
        swap(("stage2:scanning", "stage2:queued"), ("stage2:pass",))
        messages.upsert(rt, number, scans=scans, passed=passed, **clear_scanning)
        return [number]

    if result == "flag":
        rt.gh.create_check(head, STAGE2, conclusion="failure", title=WAITING,
                           summary=summary + "\n\n" + stage2_marker(
                               kind="result", result="flag", files=approvals.flagged_files(outcome.get("verdict")) or []),
                           external_id=inputs.external_id)
        swap(("stage2:scanning", "stage2:queued", "stage2:pass"), ("stage2:flagged", "needs-owner"))
        name = _entry_name(rt, inputs)
        pointers = messages.flag_pointers(outcome.get("verdict"))
        text = messages.render("flag", rt.root, name=name, repo=inputs.linked_repo, pointers=pointers, rows=[])
        messages.upsert(rt, number, text, scans=scans, flagged=inputs.external_id, flag_pointers=pointers,
                        flag_repo=inputs.linked_repo, **clear_scanning)
        return []

    if not mine or current != inputs.external_id:
        # A newer scan was dispatched, or the PR now links another commit and is queued again.
        messages.upsert(rt, number, scans=scans, **clear_scanning)
        return []
    rt.gh.create_check(head, STAGE2, conclusion="failure", title="Security review error; waiting for the curator",
                       summary=summary + "\n\n" + stage2_marker(kind="result", result="error"),
                       external_id=inputs.external_id)
    swap(("stage2:scanning", "stage2:queued"), ("needs-owner",))
    messages.upsert(rt, number, messages.render("owner-review", rt.root, name=_entry_name(rt, inputs)),
                    scans=scans, **clear_scanning)
    return []


def _pr_declined(rt, inputs: Inputs, outcome: dict, pr: dict, bot_state: dict, scans: int, mine: bool,
                 swap) -> list[int]:
    """Jules declined to review. That isn't the contributor's doing, so it isn't charged to their scans; the
    PR goes back in the queue while it has had fewer than `per_pr_max_scans` declines (counted on their own,
    `owner:scan` or not, so it can't loop forever), then the curator decides."""
    number = inputs.pr
    max_scans = int(rt.policy["stage2"]["per_pr_max_scans"])
    declines = int(bot_state.get("declines") or 0) + 1
    clear_scanning = {"scanning": None} if mine else {}
    head = pr["head"]["sha"]
    if (pr.get("state") != "open" or not mine
            or (latest_check(rt, head, STAGE1) or {}).get("external_id") != inputs.external_id):
        # Closed, a newer scan was dispatched, or the PR now links another commit and is queued again.
        messages.upsert(rt, number, scans=scans, declines=declines, **clear_scanning)
        return []
    if declines < max_scans:
        swap(("stage2:scanning",), ("stage2:queued",))
        messages.upsert(rt, number, scans=scans, declines=declines, **clear_scanning)
        rt.summary(f"#{number}: Jules declined to review; back in the queue ({declines} decline(s)).")
        return []
    rt.gh.create_check(head, STAGE2, conclusion="failure", title="Jules declined to review; waiting for the curator",
                       summary=decline_summary(outcome) + "\n\n" + stage2_marker(kind="result", result="declined"),
                       external_id=inputs.external_id)
    swap(("stage2:scanning", "stage2:queued"), ("needs-owner",))
    messages.upsert(rt, number, messages.render("owner-review", rt.root, name=_entry_name(rt, inputs)),
                    scans=scans, declines=declines, **clear_scanning)
    return []


def _entry_name(rt, inputs: Inputs) -> str:
    entries, _ = store.load_entries(rt.root)
    if inputs.entry_id and inputs.entry_id in entries:
        return entries[inputs.entry_id].get("name", inputs.entry_id)
    return inputs.entry_id or inputs.linked_repo


def _record_flag(rt, inputs: Inputs, outcome: dict, threshold: int) -> None:
    """PR-mode flag: remember the repo; a same-repo edit of a listed entry gets the rescan effects."""
    def mutate() -> None:
        state = store.State.load(rt.root)
        blocklist.add_flag(state, rt.salt, inputs.repo_id)
        record = state.lifecycle.get(inputs.entry_id or "") or {}
        if record.get("status") == LISTED and record.get("repo_id") == inputs.repo_id:
            apply_rescan_flag(rt, state, inputs, outcome, threshold)
        state.save()
    rt.commit(mutate, f"stage2: flag on PR #{inputs.pr}")


def rescan(rt, inputs: Inputs, outcome: dict, threshold: int) -> None:
    result = outcome["result"]
    if result == "deferred":
        rt.summary(f"Rescan of {inputs.entry_id} deferred; it stays a candidate.")
        return

    def mutate() -> None:
        state = store.State.load(rt.root)
        record = state.lifecycle.get(inputs.entry_id) or {}
        health = state.health.get(inputs.entry_id) or {}
        if (record.get("status") != LISTED or record.get("repo_id") != inputs.repo_id
                or health.get("scanned_commit") != inputs.base_commit or health.get("rescan_hold")):
            rt.summary(f"Rescan result for {inputs.entry_id} discarded: the entry changed during the scan.")
            return
        if result == "pass":
            repo = rt.gh.repo_by_id(inputs.repo_id)
            entries, _ = store.load_entries(rt.root)
            confidence = outcome["verdict"]["safe_confidence"]
            declined_before = int(health.get("scan_declines") or 0)
            pin(rt, state, inputs.entry_id, inputs.linked_commit, "automated", confidence, repo,
                entries.get(inputs.entry_id))
            state.health_record(inputs.entry_id)["scan_declines"] = 0
            if declined_before:
                rt.note_triage(inputs.entry_id, f"Jules reviewed `{inputs.linked_commit}` on a later try and it "
                                                f"passed (confidence {confidence}), so the pin moved there. The "
                                                "declines above need nothing more.")
        elif result == "flag":
            apply_rescan_flag(rt, state, inputs, outcome, threshold)
        elif result == "declined":
            health = state.health_record(inputs.entry_id)
            declines = int(health.get("scan_declines") or 0) + 1
            retry_at = store.utcnow() + (DECLINE_RETRY if declines < DECLINE_QUICK_TRIES else ERROR_RETRY)
            health["scan_declines"] = declines
            health["rescan_after"] = store.iso(retry_at)
            rt.upsert_triage(inputs.entry_id, decline_body(inputs, outcome, declines, retry_at))
        else:
            state.health_record(inputs.entry_id)["rescan_after"] = store.iso(store.utcnow() + ERROR_RETRY)
            rt.upsert_triage(inputs.entry_id, triage_body(inputs, outcome, threshold,
                                                          "The automated rescan couldn't finish"))
        state.save()

    rt.commit(mutate, f"stage2: rescan {inputs.entry_id} {result}")
