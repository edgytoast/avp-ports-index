"""Job configuration from the environment, plus shared helpers for side effects.

Workflows pass every value through env: (spec §8.0 rule 2); nothing untrusted is ever
interpolated into a shell command.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import store, validate
from .ghapi import GitHub

TRIAGE_PREFIX = "Triage: "
HEALTH_TITLE = "Health tracking"


def _int_env(name: str, default: int | None = None) -> int | None:
    value = os.environ.get(name, "")
    return int(value) if value.isdigit() else default


@dataclass
class Runtime:
    repo: str
    gh: GitHub
    root: Path = store.ROOT
    owner_id: int = 0
    owner_login: str = "edgytoast"
    bot_login: str = "trevorbilt-bot"
    app_id: int | None = None
    app_slug: str = "trevorbilt-index"
    auto_merge_enabled: bool = True
    stage2_enabled: bool = True
    dry_run: bool = False
    merge_token: str | None = None
    outreach_token: str | None = None
    salt_value: str | None = None
    memo: dict = field(default_factory=dict)
    summary_lines: list = field(default_factory=list)
    committer: Callable | None = None   # tests replace the main writer
    http: object = None                 # requests.Session for S1-10 link checks (tests inject a fake)

    @classmethod
    def from_env(cls, *, dry_run: bool = False) -> "Runtime":
        repo = validate.repo_name(os.environ.get("GITHUB_REPOSITORY", ""))
        gh = GitHub(repo, os.environ.get("GH_TOKEN") or None, dry_run=dry_run)
        return cls(
            repo=repo,
            gh=gh,
            owner_id=_int_env("OWNER_ID", 0) or 0,
            owner_login=os.environ.get("OWNER_LOGIN") or "edgytoast",
            bot_login=os.environ.get("BOT_LOGIN") or "trevorbilt-bot",
            app_id=_int_env("APP_ID"),
            app_slug=os.environ.get("APP_SLUG") or "trevorbilt-index",
            auto_merge_enabled=os.environ.get("AUTO_MERGE_ENABLED") == "true",
            stage2_enabled=os.environ.get("STAGE2_ENABLED") == "true",
            dry_run=dry_run,
            merge_token=os.environ.get("MERGE_TOKEN") or None,
            outreach_token=os.environ.get("OUTREACH_PAT") or None,
            salt_value=os.environ.get("BLOCKLIST_SALT") or None,
        )

    # --- config --------------------------------------------------------------------
    @property
    def policy(self) -> dict:
        if "policy" not in self.memo:
            self.memo["policy"] = store.load_policy(self.root)
        return self.memo["policy"]

    @property
    def brand(self) -> dict:
        return store.load_brand(self.root)

    @property
    def salt(self) -> str:
        if not self.salt_value:
            raise RuntimeError("BLOCKLIST_SALT is not set")
        return self.salt_value

    @property
    def app_bot_login(self) -> str:
        return f"{self.app_slug}[bot]"

    def urls(self) -> tuple[str, str]:
        return store.site_urls(self.policy, self.repo)

    def entry_schema(self) -> dict:
        return store.load_json("schema/entry.schema.json", self.root)

    # --- events --------------------------------------------------------------------
    @staticmethod
    def event() -> dict:
        path = os.environ.get("GITHUB_EVENT_PATH")
        if not path or not Path(path).exists():
            return {}
        return json.loads(Path(path).read_text(encoding="utf-8"))

    # --- side effects --------------------------------------------------------------
    def once(self, key: str, fn: Callable):
        """Run a side effect at most once per process, so push retries don't repeat it."""
        if key not in self.memo:
            self.memo[key] = fn()
        return self.memo[key]

    def summary(self, line: str) -> None:
        self.summary_lines.append(line)
        print(line)

    def flush_summary(self) -> None:
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if path and self.summary_lines:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("\n".join(self.summary_lines) + "\n")

    def commit(self, mutate: Callable[[], None], message: str) -> str | None:
        if self.committer is not None:
            return self.committer(mutate, message)
        from .writer import commit_main
        return commit_main(self, mutate, message)

    def is_app_author(self, item: dict) -> bool:
        user = item.get("user") or {}
        app = item.get("performed_via_github_app") or {}
        return user.get("login") == self.app_bot_login or (self.app_id is not None and app.get("id") == self.app_id)

    # --- owner issues --------------------------------------------------------------
    def find_triage(self, entry_id: str) -> dict | None:
        title = TRIAGE_PREFIX + entry_id
        for issue in self.gh.issues(labels="triage", state="open"):
            if issue.get("title") == title and self.is_app_author(issue) and "pull_request" not in issue:
                return issue
        return None

    def upsert_triage(self, entry_id: str, body: str) -> None:
        """One owner triage issue per entry: open it, or comment on the open one."""
        def act():
            issue = self.find_triage(entry_id)
            if issue:
                self.gh.comment(issue["number"], body)
            else:
                self.gh.create_issue(TRIAGE_PREFIX + entry_id, body, labels=["triage"],
                                     assignees=[self.owner_login])
        self.once(f"triage:{entry_id}:{hash(body)}", act)

    def note_triage(self, entry_id: str, body: str) -> None:
        """Comment on the entry's open triage issue, if it has one; never opens one."""
        def act():
            issue = self.find_triage(entry_id)
            if issue:
                self.gh.comment(issue["number"], body)
        self.once(f"note-triage:{entry_id}:{hash(body)}", act)

    def close_triage(self, entry_id: str, note: str) -> None:
        def act():
            issue = self.find_triage(entry_id)
            if issue:
                self.gh.comment(issue["number"], note)
                self.gh.close_issue(issue["number"])
        self.once(f"close-triage:{entry_id}", act)

    def owner_issue(self, title: str, body: str) -> None:
        self.once(f"owner-issue:{title}", lambda: self.gh.create_issue(
            title, body, labels=["triage"], assignees=[self.owner_login]))

    def health_issue(self) -> dict | None:
        for issue in self.gh.issues(labels="health-tracking", state="open"):
            if issue.get("title") == HEALTH_TITLE and "pull_request" not in issue:
                return issue
        return None

    def health_comment(self, body: str) -> str | None:
        """Comment on the pinned "Health tracking" issue. Returns the comment URL."""
        def act():
            issue = self.health_issue()
            if issue is None:
                issue = self.gh.create_issue(HEALTH_TITLE, "Automated health notes for the index.",
                                             labels=["health-tracking"])
            result = self.gh.comment(issue["number"], body) if issue.get("number") else {}
            return result.get("html_url") or issue.get("html_url")
        return self.once(f"health-comment:{hash(body)}", act)


def warn(message: str) -> None:
    print(f"::warning::{_one_line(message)}", file=sys.stderr)


def _one_line(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", text)[:500]
