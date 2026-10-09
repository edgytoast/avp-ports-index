"""approvals.py: files the curator approved stay approved, by SHA-256, across commits (decision 62)."""

from __future__ import annotations

import hashlib

from conftest import SHA, entry_yaml, list_entry

from avpindex import approvals, blocklist, killswitch, media, report, store, sync
from avpindex.gate import STAGE1, STAGE2, read_marker, stage2_marker

REPO = "trevorbilt-bot/good"
WASM = "web/vendor/libarchive.wasm"
POLICY = {"stage2": {"confidence_threshold": 80, "approved_files_min_confidence": 50}}


def verdict(conf=75, findings=None, steering=False):
    findings = [{"severity": "high", "file": WASM, "category": "opaque-executable", "explanation": "binary"},
                {"severity": "info", "file": "setup.sh", "category": "download", "explanation": "pinned"}] \
        if findings is None else findings
    return {"review_id": "ab" * 16, "safe_confidence": conf, "summary": "ok", "findings": findings,
            "steering_attempt": steering}


class Resp:
    def __init__(self, data):
        self.data, self.is_redirect = data, False
        self.status_code = 200 if data is not None else 404
        self.headers = {"Content-Length": str(len(data or b""))}

    def iter_content(self, _n):
        yield self.data

    def close(self):
        pass


class Files:
    """raw.githubusercontent.com: bytes per (commit, path)."""

    def __init__(self, files=None):
        self.files, self.urls = dict(files or {}), []

    def put(self, sha, path, data):
        self.files[media.raw_url("trevorbilt-bot", "good", sha, path)] = data

    def get(self, url, **_kw):
        self.urls.append(url)
        return Resp(self.files.get(url))


def approve_wasm(state, data=b"wasm v1", repo_id=11):
    state.approvals["good"] = {"repo_id": repo_id, "files": [
        {"path": WASM, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "commit": SHA(5),
         "approved_at": "2026-10-01T00:00:00Z"}]}


def test_flagged_files():
    assert approvals.flagged_files(verdict()) == [WASM]  # info findings never need clearing
    assert approvals.flagged_files(verdict(findings=[])) == []
    twice = [{"severity": "low", "file": f"./{WASM}", "category": "c", "explanation": "e"}] * 2
    assert approvals.flagged_files(verdict(findings=twice)) == [WASM]
    for bad in ("", "../outside", "/"):
        assert approvals.flagged_files(verdict(findings=[{"severity": "low", "file": bad, "category": "c",
                                                          "explanation": "e"}])) is None
    many = [{"severity": "low", "file": f"f{i}", "category": "c", "explanation": "e"} for i in range(21)]
    assert approvals.flagged_files(verdict(findings=many)) is None


def test_clearance_needs_the_same_bytes_and_nothing_else(tmp_path):
    state = store.State(root=tmp_path)
    approve_wasm(state)
    http = Files()
    http.put(SHA(11), WASM, b"wasm v1")
    clear = lambda v, **kw: approvals.clearance(state, kw.get("entry", "good"), kw.get("rid", 11), REPO, SHA(11),
                                                v, POLICY, http)
    assert clear(verdict()) == [{"path": WASM, "sha256": hashlib.sha256(b"wasm v1").hexdigest()}]
    assert clear(verdict(), rid=12) is None and clear(verdict(), entry="other") is None
    assert clear(verdict(steering=True)) is None
    assert clear(verdict(findings=[{"severity": "critical", "file": WASM, "category": "c", "explanation": "e"}])) is None
    assert clear(verdict(conf=49)) is None and clear(verdict(conf=50)) is not None
    assert clear(verdict(findings=[])) is None  # a flag on confidence alone has nothing to clear
    other = verdict()["findings"] + [{"severity": "medium", "file": "app/net.swift", "category": "c", "explanation": "e"}]
    http.put(SHA(11), "app/net.swift", b"code")
    assert clear(verdict(findings=other)) is None  # a finding on any other file stands
    http.put(SHA(11), WASM, b"wasm v2")
    assert clear(verdict()) is None  # changed bytes are reviewed again
    http.files.clear()
    assert clear(verdict()) is None  # unreadable: the flag stands


def setup_rescan(rt, gh, *, approved_bytes=b"wasm v1", head_bytes=b"wasm v1"):
    repo = gh.add_repo(REPO, 11)
    list_entry(rt, "good", repo, scanned=SHA(5), owner_approved=True)
    gh.move_head(REPO, SHA(11))
    state = store.State.load(rt.root)
    approve_wasm(state, approved_bytes)
    state.save()
    rt.http = Files()
    rt.http.put(SHA(11), WASM, head_bytes)
    return repo


def rescan(rt, conf=75):
    inputs = report.Inputs(mode="rescan", pr=None, head_sha=None, linked_repo=REPO, linked_commit=SHA(11),
                           entry_id="good", repo_id=11, base_commit=SHA(5), counted=False)
    return report.run(rt, inputs, {"result": "flag", "verdict": verdict(conf), "session_url": "u"})


def test_rescan_flag_on_approved_bytes_passes(rt, gh):
    setup_rescan(rt, gh)
    assert rescan(rt)[0] == "pass"
    health = store.State.load(rt.root).health["good"]
    assert (health["scanned_commit"], health["scan_kind"], health["scan_confidence"]) == (SHA(11), "automated", 75)
    assert health["flagged_commit"] is None and not health["rescan_hold"]
    assert not any(i["title"] == "Triage: good" for i in gh.issue_store.values())


def test_rescan_flag_on_changed_bytes_flags_and_names_the_files(rt, gh):
    setup_rescan(rt, gh, head_bytes=b"wasm v2")
    assert rescan(rt)[0] == "flag"
    state = store.State.load(rt.root)
    health = state.health["good"]
    assert health["scanned_commit"] == SHA(5) and health["flagged_commit"] == SHA(11)
    assert health["flagged_files"] == [WASM] and blocklist.is_flagged(state, rt.salt, 11)


def test_pr_pass_on_approved_files_and_flag_marker_carries_files(rt, gh):
    setup_rescan(rt, gh)
    gh.open_pr(7, "trevorbilt-bot", "entries/good.yaml", "modified", entry_yaml("good", REPO),
               labels=("stage2:scanning",), head=SHA(70))
    gh.create_check(SHA(70), STAGE1, conclusion="success", external_id=f"11@{SHA(11)}")
    inputs = report.Inputs(mode="pr", pr=7, head_sha=SHA(70), linked_repo=REPO, linked_commit=SHA(11),
                           entry_id="good", repo_id=11, base_commit=None, counted=True)
    result, prs = report.run(rt, inputs, {"result": "flag", "verdict": verdict()})
    check = gh.latest(SHA(70), STAGE2)
    assert (result, prs, check["conclusion"]) == ("pass", [7], "success")
    assert "curator-approved" in check["output"]["title"] and WASM in check["output"]["summary"]
    rt.http.put(SHA(11), WASM, b"wasm v2")
    gh.add_labels(7, ["stage2:scanning"])
    assert report.run(rt, inputs, {"result": "flag", "verdict": verdict()})[0] == "flag"
    assert read_marker(gh.latest(SHA(70), STAGE2))["files"] == [WASM]


def approve(rt, monkeypatch):
    for key, value in (("GITHUB_EVENT_NAME", "workflow_dispatch"), ("INPUT_ENTRY_ID", "good"),
                       ("INPUT_ACTION", "approve"), ("INPUT_BLOCKLIST", "false")):
        monkeypatch.setenv(key, value)
    return killswitch.run(rt)


def test_approve_records_the_flagged_files_then_rescans_pass(rt, gh, monkeypatch):
    setup_rescan(rt, gh, approved_bytes=b"something else", head_bytes=b"wasm v1")
    assert rescan(rt)[0] == "flag"
    note = approve(rt, monkeypatch)
    assert WASM in note and "won't be flagged again unless they change" in note
    state = store.State.load(rt.root)
    files = state.approvals["good"]["files"]
    assert files[-1] == {"path": WASM, "sha256": hashlib.sha256(b"wasm v1").hexdigest(), "bytes": 7,
                         "commit": SHA(11), "approved_at": "2026-10-03T12:00:00Z"}
    assert state.health["good"]["scanned_commit"] == SHA(11) and state.health["good"]["flagged_files"] == []
    # A later commit with the same wasm passes on its own.
    gh.move_head(REPO, SHA(12))
    rt.http.put(SHA(12), WASM, b"wasm v1")
    inputs = report.Inputs(mode="rescan", pr=None, head_sha=None, linked_repo=REPO, linked_commit=SHA(12),
                           entry_id="good", repo_id=11, base_commit=SHA(11), counted=False)
    assert report.run(rt, inputs, {"result": "flag", "verdict": verdict(), "session_url": "u"})[0] == "pass"
    assert store.State.load(rt.root).health["good"]["scanned_commit"] == SHA(12)


def test_approve_notes_a_file_it_could_not_read(rt, gh, monkeypatch):
    setup_rescan(rt, gh, approved_bytes=b"something else", head_bytes=b"wasm v1")
    rescan(rt)
    rt.http.files.clear()
    assert "wasn't recorded" in approve(rt, monkeypatch)
    state = store.State.load(rt.root)
    assert state.health["good"]["scanned_commit"] == SHA(11)  # the commit is approved all the same
    assert len(state.approvals["good"]["files"]) == 1


def test_merging_a_flagged_pr_approves_its_files(rt, gh):
    repo = gh.add_repo(REPO, 11)
    gh.move_head(REPO, SHA(11))
    gh.open_pr(3, "trevorbilt-bot", "entries/good.yaml", "added", entry_yaml("good", REPO), head=SHA(103))
    gh.create_check(SHA(103), STAGE1, conclusion="success", external_id=f"11@{SHA(11)}")
    gh.create_check(SHA(103), STAGE2, conclusion="failure", external_id=f"11@{SHA(11)}",
                    summary=stage2_marker(kind="result", result="flag", files=[WASM, "../escape"]))
    rt.http = Files()
    rt.http.put(SHA(11), WASM, b"wasm v1")
    state = store.State.load(rt.root)
    sync.replay_entry(rt, state, gh.prs[3], "good", entry_yaml("good", REPO))
    assert state.health["good"]["scan_kind"] == "curator-reviewed"
    assert state.approvals["good"]["repo_id"] == repo["id"]
    assert [f["path"] for f in state.approvals["good"]["files"]] == [WASM]


def test_policy_floor_is_validated(root):
    policy = store.load_policy(root)
    assert policy["stage2"]["approved_files_min_confidence"] == 50
