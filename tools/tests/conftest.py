"""Shared fixtures: a temporary index checkout (a real git repo) and an in-memory GitHub."""

from __future__ import annotations

import base64
import copy
import itertools
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from avpindex import store  # noqa: E402
from avpindex.ghapi import GitHub  # noqa: E402
from avpindex.runtime import Runtime  # noqa: E402

INDEX = "edgytoast/avp-ports-index-staging"
OWNER_ID = 146565462
BOT_ID = 5550001
STRANGER_ID = 5550002
APP_ID = 777
SALT = "00" * 32
SHA = lambda n: f"{n:040x}"  # noqa: E731
COPY = ["config", "brand", "schema", "templates", ".github/jules", "tools/avpindex"]


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


class FakeGitHub(GitHub):
    """Just enough of GitHub's REST API, in memory."""

    def __init__(self, repo: str = INDEX):
        super().__init__(repo, token="test", max_wait=0)
        self.ids = itertools.count(1000)
        self.repos: dict[str, dict] = {}
        self.users: dict[str, dict] = {}
        self.members: set[tuple[str, str]] = set()
        self.heads: dict[str, str] = {}
        self.branches: dict[tuple[str, str], str] = {}  # other branches' heads
        self.files: dict[tuple[str, str, str], bytes] = {}
        self.trees: dict[tuple[str, str], dict] = {}
        self.release_assets: dict[str, list[str]] = {}
        self.licenses: dict[str, tuple[str, str]] = {}
        self.compares: dict[tuple[str, str, str], dict] = {}
        self.commit_dates: dict[str, str] = {}
        self.prs: dict[int, dict] = {}
        self.pr_file_list: dict[int, list[dict]] = {}
        self.comment_store: dict[int, list[dict]] = {}
        self.checks: dict[str, list[dict]] = {}
        self.issue_store: dict[int, dict] = {}
        self.events: dict[int, list[dict]] = {}
        self.runs: list[dict] = []
        self.artifacts: dict[int, list[dict]] = {}
        self.dispatched: list[tuple[str, dict]] = []
        self.dispatch_ok = True
        self.merged: list[tuple[int, str, str]] = []
        self.merge_status = 200
        self.pulls_for_commit: dict[str, list[dict]] = {}
        self.external_issues: list[dict] = []
        self.external_comments: list[tuple[str, int, str]] = []
        self.closed_external: list[tuple[str, int]] = []
        self.add_user("edgytoast", OWNER_ID)
        self.add_user("trevorbilt-bot", BOT_ID)
        self.add_user("stranger", STRANGER_ID)

    # --- setup helpers -------------------------------------------------------------
    def add_user(self, login: str, uid: int, kind: str = "User") -> dict:
        user = {"login": login, "id": uid, "type": kind}
        self.users[login.lower()] = user
        return user

    def add_repo(self, full: str, rid: int, *, owner_type: str = "User", head: str | None = None,
                 install: bytes | None = b"# Install\n\nBuild it.\n", license_id: str | None = "MIT",
                 tree: list[dict] | None = None, truncated: bool = False, **extra) -> dict:
        owner_login, name = full.split("/")
        owner = self.users.get(owner_login.lower()) or self.add_user(owner_login, next(self.ids), owner_type)
        repo = {"id": rid, "full_name": full, "name": name, "owner": dict(owner), "private": False,
                "visibility": "public", "disabled": False, "archived": False, "default_branch": "main",
                "has_issues": True, **extra}
        self.repos[full.lower()] = repo
        head = head or SHA(rid)
        self.heads[full.lower()] = head
        if install is not None:
            self.files[(full.lower(), "AVP-INSTALL.md", head)] = install
        if license_id:
            self.licenses[full.lower()] = (license_id, f"{license_id} license text")
        self.trees[(full.lower(), head)] = {"tree": tree or [{"path": "README.md", "type": "blob", "size": 10}],
                                            "truncated": truncated}
        self.commit_dates[head] = "2026-09-01T00:00:00Z"
        return repo

    def move_head(self, full: str, sha: str, *, install: bytes | None = b"# Install\n", tree=None) -> None:
        self.heads[full.lower()] = sha
        if install is not None:
            self.files[(full.lower(), "AVP-INSTALL.md", sha)] = install
        self.trees[(full.lower(), sha)] = {"tree": tree or [{"path": "README.md", "type": "blob", "size": 10}],
                                           "truncated": False}
        self.commit_dates[sha] = "2026-09-15T00:00:00Z"

    def add_branch(self, full: str, branch: str, sha: str) -> None:
        """A branch other than the default one, with a passing tree at `sha`."""
        self.branches[(full.lower(), branch)] = sha
        self.files[(full.lower(), "AVP-INSTALL.md", sha)] = b"# Install\n"
        self.trees[(full.lower(), sha)] = {"tree": [{"path": "README.md", "type": "blob", "size": 10}],
                                           "truncated": False}
        self.commit_dates[sha] = "2026-09-20T00:00:00Z"

    def open_pr(self, number: int, author: str, path: str, status: str, content: bytes | None,
                labels: tuple[str, ...] = (), draft: bool = False, head: str | None = None) -> dict:
        user = self.users[author.lower()]
        head = head or SHA(9_000_000 + number)
        pr = {"number": number, "state": "open", "draft": draft, "user": dict(user), "head": {"sha": head},
              "labels": [{"name": n} for n in labels], "merged_at": None, "merge_commit_sha": None}
        self.prs[number] = pr
        self.pr_file_list[number] = [{"filename": path, "status": status}]
        if content is not None:
            self.files[(self.repo_full.lower(), path, head)] = content
        self.issue_store[number] = {"number": number, "title": f"PR {number}", "state": "open",
                                    "pull_request": {}, "labels": pr["labels"], "user": dict(user),
                                    "updated_at": "2026-10-01T00:00:00Z"}
        for name in labels:
            self.events.setdefault(number, []).append(
                {"event": "labeled", "label": {"name": name}, "created_at": f"2026-10-01T00:{number:02d}:00Z"})
        return pr

    def labels_of(self, number: int) -> set[str]:
        return {label["name"] for label in self.prs.get(number, self.issue_store.get(number, {})).get("labels", [])}

    def latest(self, sha: str, name: str) -> dict | None:
        runs = [c for c in self.checks.get(sha, []) if c["name"] == name]
        return runs[-1] if runs else None

    def bot_comment(self, number: int) -> str:
        comments = [c for c in self.comment_store.get(number, []) if "avp:bot" in c["body"]]
        return comments[-1]["body"] if comments else ""

    # --- reads -----------------------------------------------------------------------
    def repo(self, owner, name):
        return copy.deepcopy(self.repos.get(f"{owner}/{name}".lower()))

    def repo_by_id(self, repo_id):
        found = [r for r in self.repos.values() if r["id"] == repo_id]
        return copy.deepcopy(found[0]) if found else None

    def user_by_id(self, user_id):
        found = [u for u in self.users.values() if u["id"] == user_id]
        return dict(found[0]) if found else None

    def user(self, login):
        return dict(self.users[login.lower()]) if login.lower() in self.users else None

    def get(self, path, params=None, *, allow404=True):
        if path == "/user":
            return dict(self.users["edgytoast"])
        if path.startswith("/repos/") and path.endswith("/readme"):  # media.py; README.md at the ref
            owner, name = path.split("/")[2:4]
            found = self.contents(owner, name, "README.md", (params or {}).get("ref"))
            return {**found, "path": "README.md"} if found else None
        raise AssertionError(f"unexpected GET {path}")

    def is_public_member(self, org, login):
        return (org.lower(), login.lower()) in self.members

    def branch_head(self, owner, name, branch):
        full = f"{owner}/{name}".lower()
        branch = branch.removeprefix("refs/heads/")
        if (full, branch) in self.branches:
            return self.branches[(full, branch)]
        repo = self.repos.get(full)
        return self.heads.get(full) if repo is None or branch == repo["default_branch"] else None

    def commit(self, owner, name, sha):
        date = self.commit_dates.get(sha, "2026-09-01T00:00:00Z")
        return {"sha": sha, "commit": {"committer": {"date": date}}}

    def contents(self, owner, name, path, ref):
        data = self.files.get((f"{owner}/{name}".lower(), path, ref))
        if data is None:
            return None
        return {"type": "file", "name": path.rsplit("/", 1)[-1], "size": len(data), "encoding": "base64",
                "content": base64.b64encode(data).decode()}

    def tree(self, owner, name, sha):
        return copy.deepcopy(self.trees.get((f"{owner}/{name}".lower(), sha)))

    def releases(self, owner, name, count=30):
        return [{"assets": [{"name": n} for n in self.release_assets.get(f"{owner}/{name}".lower(), [])]}]

    def license(self, owner, name, ref):
        found = self.licenses.get(f"{owner}/{name}".lower())
        if not found:
            return None
        spdx, text = found
        return {"license": {"spdx_id": spdx}, "encoding": "base64", "content": base64.b64encode(text.encode()).decode()}

    def compare(self, owner, name, base, head):
        key = (f"{owner}/{name}".lower(), base, head)
        if key in self.compares:
            return self.compares[key]
        return {"status": "ahead", "ahead_by": 1} if base != head else {"status": "identical", "ahead_by": 0}

    # --- index repo ------------------------------------------------------------------
    def pr(self, number):
        return copy.deepcopy(self.prs[number])

    def pr_files(self, number):
        return copy.deepcopy(self.pr_file_list[number])

    def open_prs(self):
        return [copy.deepcopy(p) for p in self.prs.values() if p["state"] == "open"]

    def merge_pr(self, number, sha, title, token):
        if self.merge_status < 300:
            self.merged.append((number, sha, title))
            self.prs[number]["state"] = "closed"
        return self.merge_status

    def close_pr(self, number):
        self.prs[number]["state"] = "closed"

    def commit_pulls(self, sha):
        return copy.deepcopy(self.pulls_for_commit.get(sha, []))

    def issue(self, number, repo=None):
        return copy.deepcopy(self.issue_store.get(number))

    def issue_events(self, number):
        return list(self.events.get(number, []))

    def issues(self, *, labels=None, state="open", creator=None):
        out = []
        for issue in self.issue_store.values():
            names = {label["name"] for label in issue.get("labels", [])}
            if labels and labels not in names:
                continue
            if state != "all" and issue.get("state") != state:
                continue
            out.append(copy.deepcopy(issue))
        return out

    def _labels(self, number):
        target = self.prs.get(number) or self.issue_store.get(number)
        return target.setdefault("labels", [])

    def add_labels(self, number, labels):
        current = self._labels(number)
        for name in labels:
            if name not in {label["name"] for label in current}:
                current.append({"name": name})
                self.events.setdefault(number, []).append(
                    {"event": "labeled", "label": {"name": name}, "created_at": store.iso(store.utcnow())})
        if number in self.issue_store:
            self.issue_store[number]["labels"] = current

    def remove_label(self, number, label):
        current = self._labels(number)
        current[:] = [item for item in current if item["name"] != label]
        if number in self.issue_store:
            self.issue_store[number]["labels"] = current

    def comments(self, number, repo=None):
        return copy.deepcopy(self.comment_store.get(number, []))

    def comment(self, number, body, *, repo=None, token=None):
        if repo and repo.lower() != self.repo_full.lower():
            self.external_comments.append((repo, number, body))
            return {"html_url": f"https://github.com/{repo}/issues/{number}#issuecomment-1"}
        cid = next(self.ids)
        self.comment_store.setdefault(number, []).append(
            {"id": cid, "body": body, "user": {"login": "trevorbilt-index[bot]", "type": "Bot"}})
        return {"html_url": f"https://github.com/{self.repo_full}/issues/{number}#issuecomment-{cid}"}

    def update_comment(self, comment_id, body):
        for comments in self.comment_store.values():
            for c in comments:
                if c["id"] == comment_id:
                    c["body"] = body

    def create_issue(self, title, body, *, labels=None, assignees=None, repo=None, token=None):
        if repo and repo.lower() != self.repo_full.lower():
            target = self.repos.get(repo.lower())
            if target is None or not target.get("has_issues", True):
                return {"_status": 410}
            number = next(self.ids)
            self.external_issues.append({"repo": repo, "number": number, "title": title, "body": body})
            return {"number": number, "html_url": f"https://github.com/{repo}/issues/{number}"}
        number = next(self.ids)
        self.issue_store[number] = {"number": number, "title": title, "body": body, "state": "open",
                                    "labels": [{"name": n} for n in labels or []],
                                    "user": {"login": "trevorbilt-index[bot]"},
                                    "html_url": f"https://github.com/{self.repo_full}/issues/{number}"}
        return copy.deepcopy(self.issue_store[number])

    def close_issue(self, number, *, repo=None, token=None):
        if repo and repo.lower() != self.repo_full.lower():
            self.closed_external.append((repo, number))
            return
        self.issue_store[number]["state"] = "closed"

    def assign(self, number, logins):
        self.issue_store[number]["assignees"] = logins

    def create_check(self, head_sha, name, *, status="completed", conclusion=None, title="", summary="",
                     external_id=None):
        self.checks.setdefault(head_sha, []).append({
            "id": next(self.ids), "name": name, "status": status, "conclusion": conclusion,
            "external_id": external_id, "app": {"id": APP_ID}, "started_at": f"{next(self.ids):012d}",
            "completed_at": store.iso(store.utcnow()) if status == "completed" else None,
            "output": {"title": title, "summary": summary}})

    def check_runs(self, sha, app_id, name=None):
        return [copy.deepcopy(c) for c in self.checks.get(sha, []) if name in (None, c["name"])]

    def workflow_runs(self, workflow, created_since):
        return copy.deepcopy(self.runs)

    def run_artifacts(self, run_id):
        return copy.deepcopy(self.artifacts.get(run_id, []))

    def dispatch(self, workflow, inputs, ref="main"):
        if self.dispatch_ok:
            self.dispatched.append((workflow, dict(inputs)))
        return self.dispatch_ok


class FakeHTTP:
    """requests.Session stand-in for S1-10: every URL answers 200 unless told otherwise."""

    def __init__(self, outcomes: dict | None = None):
        self.outcomes = outcomes or {}

    def _answer(self, url):
        import requests
        outcome = self.outcomes.get(url, 200)
        if isinstance(outcome, Exception):
            raise outcome
        resp = requests.Response()
        resp.status_code = outcome
        return resp

    def head(self, url, **_):
        return self._answer(url)

    def get(self, url, **_):
        return self._answer(url)


def _copy_tree(root: Path) -> None:
    for rel in COPY:
        shutil.copytree(REPO_ROOT / rel, root / rel, ignore=shutil.ignore_patterns("__pycache__"))
    for rel in ("entries", "ports", "feed/v1", "state", "blocklist", "verification",
                "skills/avp-index-submit/references", "skills/avp-index-submit/scripts"):
        (root / rel).mkdir(parents=True, exist_ok=True)
    (root / "entries/.gitkeep").write_text("")
    (root / "ports/.gitkeep").write_text("")
    store.State(root=root).save()
    (root / store.VERIFIED).write_text("schema_version: 1\nrecords: {}\n")


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("AVP_NOW", "2026-10-03T12:00:00Z")
    _copy_tree(tmp_path)
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.invalid")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "Initial import [skip ci]")
    return tmp_path


@pytest.fixture
def gh() -> FakeGitHub:
    return FakeGitHub()


@pytest.fixture
def rt(root, gh) -> Runtime:
    commits: list[str] = []

    def committer(mutate, message):
        mutate()
        from avpindex.generate import generate
        generate(root, INDEX)
        commits.append(message)
        git(root, "add", "-A")
        if git(root, "status", "--porcelain").strip():
            git(root, "commit", "-qm", message)
        return "fake"

    runtime = Runtime(repo=INDEX, gh=gh, root=root, owner_id=OWNER_ID, owner_login="edgytoast",
                      app_id=APP_ID, salt_value=SALT, merge_token="merge", outreach_token="outreach",
                      committer=committer, http=FakeHTTP())
    runtime.commits = commits  # type: ignore[attr-defined]
    return runtime


def entry_yaml(entry_id: str, repo: str, dev: str = "trevorbilt-bot", **extra) -> bytes:
    data = {"id": entry_id, "name": f"{entry_id} port", "game": {"title": f"{entry_id} game"},
            "repo": f"https://github.com/{repo}", "developer": {"github": dev}, "status": "working",
            "experiences": ["6dof-immersive"], **extra}
    return json.dumps(data).encode()  # JSON is valid YAML


def write_entry(root: Path, entry_id: str, repo: str, **extra) -> None:
    (root / "entries" / f"{entry_id}.yaml").write_bytes(entry_yaml(entry_id, repo, **extra))


def list_entry(rt, entry_id: str, repo: dict, *, scanned: str | None = None, submitted_by: int = BOT_ID,
               owner_approved: bool = False, write: bool = True) -> None:
    """Put an entry straight into the listed state, as if a merge had been synced."""
    if write:
        write_entry(rt.root, entry_id, repo["full_name"])
    state = store.State.load(rt.root)
    state.lifecycle[entry_id] = {"status": "listed", "repo": f"https://github.com/{repo['full_name']}",
                                 "repo_id": repo["id"], "submitted_by": "trevorbilt-bot",
                                 "submitted_by_id": submitted_by, "owner_approved": owner_approved,
                                 "changed_at": "2026-10-01T00:00:00Z", "listed_at": "2026-10-01T00:00:00Z",
                                 "by": "merge"}
    health = store.default_health()
    health.update(scanned_commit=scanned or SHA(repo["id"]), scanned_at="2026-10-01T00:00:00Z",
                  scan_kind="automated", scan_confidence=90, scan_state="current", commits_since_scan=0,
                  last_commit_date="2026-09-01T00:00:00Z", license={"spdx": "MIT", "kind": "open-source"})
    state.health[entry_id] = health
    state.save()
