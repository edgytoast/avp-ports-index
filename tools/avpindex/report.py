"""The stage2-scan report job (spec §8.4, §6.3): apply a scan result in PR or rescan mode.

It runs with if: always(), so a failed, cancelled or timed-out scan job still produces an
`error` here and no PR is left at stage2:scanning.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import blocklist, jules, lifecycle, messages, store, validate
from .gate import STAGE1, STAGE2, WAITING, latest_check, stage2_marker
from .lifecycle import LISTED, PULLED
from .sync import pin


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
    result = data.get("result")
    if result == "deferred":
        return {"result": "deferred", "reason": data.get("reason", "")}
    verdict, problem = jules.check_verdict(json.dumps(data.get("verdict")) if data.get("verdict") else None,
                                           jules.verdict_schema())
    out = {"result": "error", "reason": data.get("reason") or problem, "session_url": data.get("session_url"),
           "minutes": data.get("minutes")}
    if verdict is not None:
        out.update(result=jules.decide(verdict, int(policy["stage2"]["confidence_threshold"])), verdict=verdict,
                   reason="")
    return out


def verdict_summary(outcome: dict, threshold: int) -> str:
    verdict = outcome.get("verdict")
    if not verdict:
        return f"No valid verdict: {validate.md_inline(outcome.get('reason') or 'unknown error', 300)}"
    lines = [f"**Confidence:** {verdict['safe_confidence']} (threshold {threshold})",
             f"**Steering attempt:** {'yes' if verdict['steering_attempt'] else 'no'}", "",
             "Summary from the automated review (untrusted text):", "", validate.fence(verdict.get("summary", "")), ""]
    findings = verdict.get("findings") or []
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


def apply_rescan_flag(rt, state: store.State, inputs: Inputs, outcome: dict, threshold: int) -> None:
    """The rescan-mode flag effects (spec §6.3), also used for a PR flag on a same-repo edit."""
    entry_id = inputs.entry_id
    health = state.health_record(entry_id)
    health["flagged_commit"] = inputs.linked_commit
    health["rescan_hold"] = True
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
    result = outcome["result"]
    if inputs.mode == "rescan":
        rescan(rt, inputs, outcome, threshold)
        return result, []
    return result, pr_mode(rt, inputs, outcome, threshold)


def pr_mode(rt, inputs: Inputs, outcome: dict, threshold: int) -> list[int]:
    number = inputs.pr
    result = outcome["result"]
    pr = rt.gh.pr(number)
    labels = {label["name"] for label in pr.get("labels") or []}
    bot_state = messages.read_state(messages.find_bot_comment(rt, number))
    mine = bot_state.get("scanning") in (None, inputs.external_id)
    increment = 1 if inputs.counted and result in ("pass", "flag", "error") else 0
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
        rt.gh.create_check(head, STAGE2, conclusion="success",
                           title=f"Passed: confidence {confidence} (threshold {threshold})",
                           summary=summary + "\n\n" + stage2_marker(kind="scan", confidence=confidence),
                           external_id=inputs.external_id)
        swap(("stage2:scanning", "stage2:queued"), ("stage2:pass",))
        messages.upsert(rt, number, scans=scans, passed=passed, **clear_scanning)
        return [number]

    if result == "flag":
        rt.gh.create_check(head, STAGE2, conclusion="failure", title=WAITING,
                           summary=summary + "\n\n" + stage2_marker(kind="result", result="flag"),
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
            pin(rt, state, inputs.entry_id, inputs.linked_commit, "automated",
                outcome["verdict"]["safe_confidence"], repo)
        elif result == "flag":
            apply_rescan_flag(rt, state, inputs, outcome, threshold)
        else:
            state.health_record(inputs.entry_id)["rescan_after"] = store.iso(
                store.utcnow() + dt.timedelta(hours=24))
            rt.upsert_triage(inputs.entry_id, triage_body(inputs, outcome, threshold,
                                                          "The automated rescan couldn't finish"))
        state.save()

    rt.commit(mutate, f"stage2: rescan {inputs.entry_id} {result}")
