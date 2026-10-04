"""Command-line entry point of the submit skill's preflight script (bundled into
skills/avp-index-submit/scripts/preflight.py by generate.py)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .checks import FAIL, FIXES, PASS, ROUTE, IndexView, LinkedRepoReader, Subject, run


def _policy_and_schema() -> tuple[dict, dict]:
    bundled = globals()
    if "POLICY" in bundled and "SCHEMA" in bundled:
        return bundled["POLICY"], bundled["SCHEMA"]
    from . import store
    return store.load_policy(), store.load_json("schema/entry.schema.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AVP Ports Index Stage 1 checks on an entry file.")
    parser.add_argument("entry", help="path to entries/<id>.yaml")
    parser.add_argument("--as", dest="login", help="GitHub login that will open the PR (default: the GITHUB_TOKEN user)")
    args = parser.parse_args(argv)
    path = Path(args.entry)
    if not path.is_file():
        print(f"{path} not found", file=sys.stderr)
        return 2
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    reader = LinkedRepoReader(token=token)
    author_id = author_login = None
    if args.login:
        user = reader.user(args.login)
        if user:
            author_id, author_login = user["id"], user["login"]
    elif token:
        user = reader.get("/user")
        if user:
            author_id, author_login = user["id"], user["login"]
    policy, schema = _policy_and_schema()
    report = run(Subject(mode="preflight", entry_id=path.stem, raw=path.read_bytes(),
                         author_id=author_id, author_login=author_login),
                 IndexView(policy=policy, schema=schema), reader)
    width = max(len(r.id) for r in report.results) if report.results else 6
    for result in report.results:
        mark = {PASS: "pass ", FAIL: "FAIL ", ROUTE: "route"}[result.outcome]
        line = f"{result.id.ljust(width)}  {mark}  {result.detail}".rstrip()
        print(line)
        if result.outcome == FAIL and result.id in FIXES:
            print(f"{'':{width}}         fix: {FIXES[result.id]}")
    for check_id, text in report.warnings:
        print(f"{check_id.ljust(width)}  warn   {text}")
    if author_id is None:
        print("note: S1-08 (who may submit) was not checked; set GITHUB_TOKEN or pass --as <login>.")
    print("S1-04, S1-05, S1-15, S1-16, S1-17 and S1-18 need the index's own data and run on the PR.")
    overall = report.overall
    if overall == FAIL:
        print("Result: fix the failures above before opening the PR.")
        return 1
    if overall == ROUTE:
        print("Result: ready, but the curator will look at the routed items before it goes further.")
        return 0
    print("Result: ready to submit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
