"""Stage 1 checks: link errors (U4), authority (U5), repo identity (U2), flag memory (U11),
reclaimed ids (U20) and the tree and release checks."""

from __future__ import annotations

import socket

import pytest
import requests
from conftest import BOT_ID, OWNER_ID, SALT, SHA, STRANGER_ID, FakeGitHub, FakeHTTP, entry_yaml

from avpindex import blocklist, checks, store
from avpindex.checks import FAIL, PASS, ROUTE, IndexView, Subject


@pytest.fixture
def index(root):
    return IndexView(policy=store.load_policy(root), schema=store.load_json("schema/entry.schema.json", root),
                     index_repo="edgytoast/avp-ports-index-staging", salt=SALT)


def run(gh, index, entry_id="good", repo="trevorbilt-bot/good", *, author=BOT_ID, login="trevorbilt-bot",
        change="add", record=None, health=None, old=None, http=None, mode="gate", owner_scan=False, **extra):
    subject = Subject(mode=mode, entry_id=entry_id, raw=entry_yaml(entry_id, repo, **extra), change=change,
                      author_id=author, author_login=login, record=record, health=health, old_entry=old,
                      owner_scan=owner_scan)
    return checks.run(subject, index, gh, http or FakeHTTP({}))


def test_happy_path(index):
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/good", 11)
    report = run(gh, index)
    assert report.overall == PASS, [(r.id, r.outcome, r.detail) for r in report.results]
    assert report.external_id == f"11@{SHA(11)}"
    assert report.license == {"spdx": "MIT", "kind": "open-source"}


def test_source_ref(index):
    """source_ref picks the branch whose HEAD is checked; a bad one never falls back to the default."""
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/good", 11)
    gh.add_branch("trevorbilt-bot/good", "vision-pro", SHA(12))
    assert run(gh, index).external_id == f"11@{SHA(11)}"
    report = run(gh, index, source_ref="vision-pro")
    assert report.overall == PASS and report.external_id == f"11@{SHA(12)}"
    missing = run(gh, index, source_ref="no-such-branch").get("S1-06")
    assert missing.outcome == FAIL and "source_ref" in missing.detail
    assert run(gh, index, source_ref="../main").get("S1-03").outcome == FAIL
    repo = gh.repos["trevorbilt-bot/good"]
    assert checks.linked_head(gh, repo, {"source_ref": "../main"}) is None
    assert checks.linked_head(gh, repo, {"source_ref": ["main"]}) is None
    assert checks.linked_head(gh, repo, {"source_ref": "vision-pro\n"}) is None
    assert checks.linked_head(gh, repo, {}) == SHA(11)


def test_experiences_and_install(index):
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/good", 11)
    assert run(gh, index, experiences=["2d", "6dof-progressive"], install=["build", "sideload"]).overall == PASS
    assert run(gh, index, install=["sideload"]).overall == PASS  # a sideload-only port is fine
    for extra, message in [({"experiences": []}, "at least 1 value"), ({"experiences": ["4d"]}, "must be one of"),
                           ({"experiences": ["2d", "2d"]}, "listed twice"), ({"install": []}, "at least 1 value")]:
        result = run(gh, index, **extra).get("S1-03")
        assert result.outcome == FAIL and message in result.detail, (extra, result.detail)


def test_branch_head_missing_branch():
    """GitHub answers 422 for a ref that doesn't exist; a slash in a branch name stays one segment."""
    class Session:
        def __init__(self):
            self.urls = []

        def request(self, method, url, **kw):
            self.urls.append(url)
            resp = requests.Response()
            resp.status_code, resp._content = (422, b"{}") if "missing" in url else (200, b'{"sha": "abc"}')
            return resp

    session = Session()
    reader = checks.LinkedRepoReader(session=session)
    assert reader.branch_head("o", "r", "missing") is None
    repo = {"owner": {"login": "o"}, "name": "r", "default_branch": "main"}
    assert checks.linked_head(reader, repo, {}) == "abc" and session.urls[-1].endswith("/commits/main")
    # source_ref is looked up only as a branch, so tags, SHAs and pull/N/head refs don't resolve
    assert checks.linked_head(reader, repo, {"source_ref": "feature/vr"}) == "abc"
    assert session.urls[-1].endswith("/commits/refs%2Fheads%2Ffeature%2Fvr")


def test_stage1_outcomes(index):
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/noinstall", 12, install=None)
    gh.add_repo("trevorbilt-bot/gamedata", 13, tree=[{"path": "test.iso", "type": "blob", "size": 0}])
    gh.add_repo("trevorbilt-bot/nolicense", 14, license_id=None)
    gh.add_repo("trevorbilt-bot/denylicense", 15, license_id="NOASSERTION")
    gh.licenses["trevorbilt-bot/denylicense"] = ("NOASSERTION", "Custom. Not for personal use.")
    gh.add_repo("trevorbilt-bot/ipa", 16)
    gh.release_assets["trevorbilt-bot/ipa"] = ["Test.ipa"]
    assert run(gh, index, "noinstall", "trevorbilt-bot/noinstall").get("S1-07").outcome == FAIL
    assert run(gh, index, "gamedata", "trevorbilt-bot/gamedata").get("S1-11a").outcome == FAIL
    nolic = run(gh, index, "nolicense", "trevorbilt-bot/nolicense")
    assert nolic.overall == PASS and nolic.license == {"spdx": None, "kind": "none"}
    deny = run(gh, index, "denylicense", "trevorbilt-bot/denylicense")
    assert deny.overall == ROUTE and deny.routes == ["S1-09"]
    assert run(gh, index, "ipa", "trevorbilt-bot/ipa").routes == ["S1-11d"]


def test_tree_routes(index):
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/big", 20, truncated=True)
    gh.add_repo("trevorbilt-bot/zip", 21, tree=[{"path": "a/b.zip", "type": "blob", "size": 5}])
    gh.add_repo("trevorbilt-bot/lfs", 22, tree=[{"path": ".gitattributes", "type": "blob", "size": 30}])
    gh.files[("trevorbilt-bot/lfs", ".gitattributes", SHA(22))] = b"*.bin filter=lfs diff=lfs\n"
    assert run(gh, index, "big", "trevorbilt-bot/big").routes == ["S1-11b"]
    assert run(gh, index, "zip", "trevorbilt-bot/zip").routes == ["S1-11c"]
    assert run(gh, index, "lfs", "trevorbilt-bot/lfs").routes == ["S1-11c"]


def test_schema_and_id(index):
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/good", 11)
    report = run(gh, index, "good", "trevorbilt-bot/good", owner_verified=True)
    assert report.get("S1-03").outcome == FAIL and "owner_verified" in report.get("S1-03").detail
    subject = Subject(mode="gate", entry_id="other", raw=entry_yaml("good", "trevorbilt-bot/good"))
    assert checks.run(subject, index, gh).get("S1-03").outcome == FAIL
    for url in ("https://a.example/x)[Get](https://evil.example/x.ipa",
                "https://a.example/>[P](https://evil.example)<https://a.example/"):
        sneaky = run(gh, index, credits=[{"name": "n", "role": "r", "url": url}])
        assert sneaky.get("S1-03").outcome == FAIL
        assert run(gh, index, upstream=[url]).get("S1-03").outcome == FAIL
    git_url = Subject(mode="gate", entry_id="good", raw=entry_yaml("good", "trevorbilt-bot/good.git"))
    assert checks.run(git_url, index, gh).get("S1-03").outcome == FAIL


class TestLinks:
    """U4: 404, 410 and DNS failures fail; 403, 429, timeouts and 5xx are warnings."""

    def test_gate(self, index):
        gh = FakeGitHub()
        gh.add_repo("trevorbilt-bot/good", 11)
        dns = requests.ConnectionError(socket.gaierror(8, "nodename nor servname provided"))
        for outcome, expected in [(404, FAIL), (410, FAIL), (dns, FAIL), (403, PASS), (429, PASS),
                                  (requests.Timeout("slow"), PASS), (503, PASS)]:
            http = FakeHTTP({"https://example.com/dev": outcome})
            report = run(gh, index, http=http, developer={"github": "trevorbilt-bot", "url": "https://example.com/dev"})
            assert report.get("S1-10").outcome == expected, outcome
            if expected == PASS:
                assert report.overall == PASS and report.warnings

    def test_health_mode(self, index):
        gh = FakeGitHub()
        gh.add_repo("trevorbilt-bot/good", 11)
        http = FakeHTTP({"https://example.com/dev": 429})
        report = run(gh, index, mode="health", change="listed", http=http,
                     developer={"github": "trevorbilt-bot", "url": "https://example.com/dev"})
        assert report.failures == [] and report.warnings


class TestAuthority:
    """U5: authority is decided by numeric IDs."""

    def setup_method(self):
        self.gh = FakeGitHub()
        self.repo = self.gh.add_repo("trevorbilt-bot/good", 11)
        self.gh.add_user("someorg", 900, "Organization")
        self.gh.add_repo("someorg/orgport", 12, owner_type="Organization")
        self.gh.members.add(("someorg", "stranger"))
        self.record = {"status": "listed", "repo": "https://github.com/trevorbilt-bot/good", "repo_id": 11,
                       "submitted_by_id": OWNER_ID}

    def test_adds(self, index):
        assert run(self.gh, index).get("S1-08").outcome == PASS
        assert run(self.gh, index, author=STRANGER_ID, login="stranger").get("S1-08").outcome == ROUTE
        assert run(self.gh, index, "orgport", "someorg/orgport", author=STRANGER_ID,
                   login="stranger").get("S1-08").outcome == PASS

    def test_edits_and_deletes(self, index):
        old = {"repo": "https://github.com/trevorbilt-bot/good"}
        for author, login, ok in [(BOT_ID, "trevorbilt-bot", True), (OWNER_ID, "edgytoast", True),
                                  (STRANGER_ID, "stranger", False)]:
            report = run(self.gh, index, change="edit", author=author, login=login, record=self.record, old=old)
            assert (report.get("S1-08").outcome == PASS) is ok, login
            removal = checks.run(Subject(mode="gate", entry_id="good", change="remove", author_id=author,
                                         author_login=login, record=self.record, old_entry=old), index, self.gh)
            assert (removal.get("S1-08").outcome == PASS) is ok, login

    def test_repoint_needs_both_and_a_is_not_waivable(self, index):
        self.gh.add_repo("stranger/mine", 30)
        old = {"repo": "https://github.com/trevorbilt-bot/good"}
        report = run(self.gh, index, "good", "stranger/mine", change="edit", author=STRANGER_ID, login="stranger",
                     record=self.record, old=old, owner_scan=True)
        result = report.get("S1-08")
        assert result.outcome == ROUTE and not result.waivable and not result.waived
        assert report.overall == ROUTE

    def test_reregistered_logins(self, index):
        """A reclaimed login has a different ID, so it fails (a); if the repo is gone only the submitter passes."""
        self.gh.users["trevorbilt-bot"]["id"] = 999999  # someone re-registered the login
        old = {"repo": "https://github.com/trevorbilt-bot/good"}
        report = run(self.gh, index, change="edit", author=999999, login="trevorbilt-bot", record=self.record, old=old)
        assert report.get("S1-08").outcome == ROUTE
        del self.gh.repos["trevorbilt-bot/good"]
        gone = dict(self.record, submitted_by_id=BOT_ID)
        bot = checks.run(Subject(mode="gate", entry_id="good", change="remove", author_id=BOT_ID,
                                 author_login="x", record=gone, old_entry=old), index, self.gh)
        assert bot.get("S1-08").outcome == PASS
        owner = checks.run(Subject(mode="gate", entry_id="good", change="remove", author_id=OWNER_ID,
                                   author_login="edgytoast", record=gone, old_entry=old), index, self.gh)
        assert owner.get("S1-08").outcome == ROUTE


def test_repo_identity_s1_16(index):
    """U2 (gate part): a reclaimed repo URL routes on S1-16, and owner:scan doesn't waive it."""
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/good", 99)  # same URL, new repo
    record = {"status": "listed", "repo": "https://github.com/trevorbilt-bot/good", "repo_id": 11,
              "submitted_by_id": BOT_ID}
    report = run(gh, index, change="edit", record=record, old={"repo": record["repo"]}, owner_scan=True)
    assert report.get("S1-16").outcome == ROUTE and not report.get("S1-16").waived
    health = run(gh, index, mode="health", change="listed", record=record)
    assert health.get("S1-16").outcome == ROUTE


def test_flag_memory_s1_17(index):
    """U11 (gate part)."""
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/good", 11)
    index.flagged = {blocklist.h(SALT, "repo_id:11")}
    assert run(gh, index).routes == ["S1-17"]
    record = {"status": "listed", "repo": "https://github.com/trevorbilt-bot/good", "repo_id": 11, "submitted_by_id": BOT_ID}
    old = {"repo": record["repo"]}
    same = run(gh, index, change="edit", record=record, old=old, health={"scanned_commit": SHA(11)})
    assert same.get("S1-17").outcome == PASS
    newer = run(gh, index, change="edit", record=record, old=old, health={"scanned_commit": SHA(1)})
    assert newer.routes == ["S1-17"]
    waived = run(gh, index, owner_scan=True)
    assert waived.overall == PASS and waived.waived == ["S1-17"]
    flagged_pr = checks.run(Subject(mode="gate", entry_id="good", raw=entry_yaml("good", "trevorbilt-bot/good"),
                                    author_id=BOT_ID, author_login="trevorbilt-bot", flagged_pr=True), index, gh)
    assert flagged_pr.get("S1-17") is None


def test_reclaimed_id_s1_18(index):
    """U20: same repo passes; a different repo routes and owner:scan waives it."""
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/good", 11)
    gh.add_repo("trevorbilt-bot/other", 12)
    record = {"status": "withdrawn", "repo": "https://github.com/trevorbilt-bot/good", "repo_id": 11}
    assert run(gh, index, record=record).overall == PASS
    different = run(gh, index, "good", "trevorbilt-bot/other", record=record)
    assert different.routes == ["S1-18"]
    assert run(gh, index, "good", "trevorbilt-bot/other", record=record, owner_scan=True).overall == PASS


def test_blocklist_and_duplicates(index):
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/good", 11)
    index.blocked = {blocklist.h(SALT, "repo_name:trevorbilt-bot/good")}
    assert run(gh, index).get("S1-05").outcome == FAIL
    index.blocked = set()
    index.entries = {"good": {"repo": "https://github.com/trevorbilt-bot/good"}}
    index.lifecycle = {"good": {"repo_id": 11}}
    dup = run(gh, index, "good-2", "trevorbilt-bot/good")
    assert dup.get("S1-04").outcome == FAIL
    renamed = run(gh, index, "good-3", "trevorbilt-bot/GOOD")
    assert renamed.get("S1-04").outcome == FAIL


def test_pulled_s1_15(index):
    gh = FakeGitHub()
    gh.add_repo("trevorbilt-bot/good", 11)
    record = {"status": "pulled", "repo": "https://github.com/trevorbilt-bot/good", "repo_id": 11, "submitted_by_id": BOT_ID}
    assert run(gh, index, change="edit", record=record, old={"repo": record["repo"]}).get("S1-15").outcome == FAIL
