"""Entry points used by the workflows: python -m avpindex.cli <command>.

Inputs come only from env: and the event payload file; they are validated before use.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import store, validate


def _outputs(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    line = "\n".join(f"{k}={v}" for k, v in values.items())
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    else:
        print(line)


def _runtime(dry_run: bool = False):
    from .runtime import Runtime
    return Runtime.from_env(dry_run=dry_run)


def cmd_gate(_args) -> int:
    from . import gate
    rt = _runtime()
    prs = gate.run(rt)
    _outputs(merge_prs=" ".join(str(n) for n in prs))
    rt.flush_summary()
    return 0


def cmd_blocklist_label(_args) -> int:
    from . import gate
    rt = _runtime()
    gate.blocklist_label(rt)
    rt.flush_summary()
    return 0


def cmd_merge(args) -> int:
    from . import merge
    rt = _runtime()
    if args.sweep:
        for line in merge.sweep(rt):
            rt.summary(line)
    else:
        for value in (os.environ.get("MERGE_PRS") or "").split():
            number = validate.pr_number(value)
            rt.summary(f"#{number}: {merge.try_merge(rt, number)}")
    rt.flush_summary()
    return 0


def cmd_recheck(_args) -> int:
    from . import queue
    rt = _runtime()
    for line in queue.recheck_waiting(rt, store.utcnow()):
        rt.summary(line)
    rt.flush_summary()
    return 0


def cmd_dispatch(_args) -> int:
    from . import queue
    rt = _runtime()
    for line in queue.dispatch(rt):
        rt.summary(line)
    rt.flush_summary()
    return 0


def _scan_target() -> tuple[str, str]:
    repo = validate.repo_name(os.environ.get("INPUT_LINKED_REPO"))
    sha = validate.sha(os.environ.get("INPUT_LINKED_COMMIT"))
    validate.choice(os.environ.get("INPUT_MODE"), ("pr", "rescan"), "mode")
    if os.environ.get("INPUT_PR"):
        validate.pr_number(os.environ["INPUT_PR"])
    if os.environ.get("INPUT_ENTRY_ID"):
        validate.entry_id(os.environ["INPUT_ENTRY_ID"])
    return repo, sha


def cmd_scan(args) -> int:
    from . import jules
    repo, sha = _scan_target()
    key = os.environ.get("JULES_API_KEY")
    if not key:
        print("JULES_API_KEY is not set", file=sys.stderr)
        return 1
    outcome = jules.review(jules.Jules(key), f"https://github.com/{repo}", sha, store.load_policy())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "outcome.json").write_text(json.dumps(outcome.to_json(), indent=2), encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    line = (f"Scan of {repo}@{sha[:12]}: {outcome.result} after {outcome.minutes:.1f} min; "
            f"states {', '.join(outcome.states) or 'none'}; {outcome.reason}")
    print(line)
    print(f"Session: {outcome.session_url}")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(line + f"\n\nSession: {outcome.session_url}\n")
    return 0


def cmd_report_plan(args) -> int:
    """Whether the report job's token needs contents: write (any rescan, or a PR-mode flag)."""
    from . import report
    mode = validate.choice(os.environ.get("INPUT_MODE"), ("pr", "rescan"), "mode")
    outcome = report.load_outcome(Path(args.outcome), os.environ.get("SCAN_RESULT", ""), store.load_policy())
    writes = mode == "rescan" or outcome["result"] == "flag"
    _outputs(contents="write" if writes else "read")
    return 0


def cmd_report(args) -> int:
    from . import report
    rt = _runtime()
    inputs = report.Inputs.from_env()
    outcome = report.load_outcome(Path(args.outcome), os.environ.get("SCAN_RESULT", ""), rt.policy)
    result, prs = report.run(rt, inputs, outcome)
    marker = Path(args.outcome).parent / "result.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(result + "\n", encoding="utf-8")
    _outputs(result=result, merge_prs=" ".join(str(n) for n in prs))
    rt.summary(f"Result: {result}")
    rt.flush_summary()
    return 0


def cmd_build_surfaces(_args) -> int:
    from .sync import sync_all
    rt = _runtime()

    def mutate() -> None:
        state = store.State.load(rt.root)
        sync_all(rt, state)
        state.save()

    rt.commit(mutate, "build: sync state and regenerate surfaces")
    if rt.health_issue() is None and not rt.dry_run:
        from .runtime import HEALTH_TITLE
        rt.gh.create_issue(HEALTH_TITLE, "The daily health check notes route and warning changes here, and uses "
                           "this issue when a port's repo can't take an outreach issue.", labels=["health-tracking"])
        rt.summary("Created the Health tracking issue.")
    rt.flush_summary()
    return 0


def cmd_health(_args) -> int:
    from . import health
    dry = validate.boolean(os.environ.get("INPUT_DRY_RUN", "false"))
    rt = _runtime(dry_run=dry)
    health.run(rt)
    rt.flush_summary()
    return 0


def cmd_kill_switch(_args) -> int:
    from . import killswitch
    rt = _runtime()
    killswitch.run(rt)
    rt.flush_summary()
    return 0


def cmd_intake(_args) -> int:
    from . import killswitch
    rt = _runtime()
    killswitch.intake(rt)
    return 0


def cmd_review(args) -> int:
    """Calibration (spec §12 step 4): run one real Jules review and print the verdict."""
    from . import jules
    owner, name = validate.parse_repo_url(args.repo_url)
    sha = validate.sha(args.sha)
    key = os.environ.get("JULES_API_KEY")
    if not key:
        print("JULES_API_KEY is not set", file=sys.stderr)
        return 1
    outcome = jules.review(jules.Jules(key), f"https://github.com/{owner}/{name}", sha, store.load_policy())
    print(json.dumps(outcome.to_json(), indent=2))
    return 0


def cmd_jules_smoke(_args) -> int:
    """Spec §12 step 1: list sessions, run one trivial repoless session, report states and outputs."""
    import time
    from . import jules
    client = jules.Jules(os.environ["JULES_API_KEY"])
    listed = client.list_sessions(1)
    print("list sessions: ok", "(keys: " + ", ".join(sorted(listed)) + ")")
    session = client.create_session("Write a file named hello.txt containing the text hi, then print its "
                                    "contents in a fenced block.", "AVP index smoke test")
    print("session fields:", ", ".join(sorted(session)))
    states, started = [], time.monotonic()
    while time.monotonic() - started < 1200:
        time.sleep(15)
        state = client.get_session(session["name"]).get("state")
        if not states or states[-1] != state:
            states.append(state)
            print("state:", state)
        if state in jules.DONE_STATES | jules.STOPPED_STATES:
            break
    acts = client.activities(session["name"])
    kinds = sorted({k for a in acts for k in a if k not in ("name", "id", "createTime", "description", "originator")})
    print("activity fields:", ", ".join(kinds))
    patches = [art["changeSet"]["gitPatch"].get("unidiffPatch", "") for a in acts for art in a.get("artifacts") or []
               if (art.get("changeSet") or {}).get("gitPatch")]
    print("change set has hello.txt:", any("hello.txt" in p for p in patches))
    print(json.dumps({"states": states, "session_url": session.get("url")}))
    return 0


def cmd_generate(args) -> int:
    from .generate import generate
    generate(store.ROOT, validate.repo_name(args.repo), write=not args.check)
    return 0


def cmd_check_data(_args) -> int:
    """Validate every data file against its schema (used by self-test)."""
    import jsonschema
    import yaml
    root = store.ROOT
    problems = []

    def check(rel: str, schema_rel: str, ref: str | None = None) -> None:
        schema = store.load_json(schema_rel, root)
        if ref:
            schema = {"$ref": f"#/$defs/{ref}", "$defs": schema["$defs"]}
        data = validate.normalize(yaml.safe_load((root / rel).read_text()) or {})
        for err in jsonschema.Draft202012Validator(schema).iter_errors(data):
            problems.append(f"{rel}: {err.message[:200]}")

    check(store.HEALTH, "schema/state.schema.json", "health")
    check(store.LIFECYCLE, "schema/state.schema.json", "lifecycle")
    check(store.SYNC, "schema/state.schema.json", "sync")
    check(store.FLAGS, "schema/state.schema.json", "flags")
    check(store.BLOCKLIST, "schema/blocklist.schema.json")
    check(store.VERIFIED, "schema/owner-verified.schema.json")
    schema = store.load_json("schema/entry.schema.json", root)
    for path in sorted((root / "entries").glob("*.yaml")):
        data = validate.load_untrusted_yaml(path.read_bytes())
        for err in jsonschema.Draft202012Validator(schema).iter_errors(data):
            problems.append(f"{path.name}: {err.message[:200]}")
    feed = json.loads((root / "feed/v1/index.json").read_text())
    for err in jsonschema.Draft202012Validator(store.load_json("schema/feed-v1.schema.json", root)).iter_errors(feed):
        problems.append(f"feed: {err.message[:200]}")
    for line in problems:
        print(line)
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="avpindex")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in [("gate", cmd_gate), ("blocklist-label", cmd_blocklist_label), ("dispatch", cmd_dispatch), ("recheck", cmd_recheck),
                       ("build-surfaces", cmd_build_surfaces), ("health", cmd_health),
                       ("kill-switch", cmd_kill_switch), ("intake", cmd_intake),
                       ("jules-smoke", cmd_jules_smoke), ("check-data", cmd_check_data)]:
        sub.add_parser(name).set_defaults(func=func)
    merge = sub.add_parser("merge")
    merge.add_argument("--sweep", action="store_true")
    merge.set_defaults(func=cmd_merge)
    scan = sub.add_parser("scan")
    scan.add_argument("--out", default="out")
    scan.set_defaults(func=cmd_scan)
    rep = sub.add_parser("report")
    rep.add_argument("--outcome", default="out/outcome.json")
    rep.set_defaults(func=cmd_report)
    plan = sub.add_parser("report-plan")
    plan.add_argument("--outcome", default="out/outcome.json")
    plan.set_defaults(func=cmd_report_plan)
    review = sub.add_parser("review")
    review.add_argument("repo_url")
    review.add_argument("sha")
    review.set_defaults(func=cmd_review)
    gen = sub.add_parser("generate")
    gen.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY") or "edgytoast/avp-ports-index")
    gen.add_argument("--check", action="store_true", help="render without writing")
    gen.set_defaults(func=cmd_generate)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
