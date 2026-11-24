"""What's new (WHATS-NEW.md): the build logs what changed for players and renders it newest first."""
from __future__ import annotations

import json

from avpindex import changelog, generate, store
from conftest import list_entry
from test_delist import event, ks  # noqa: F401  (fixture)


def log(rt) -> dict:
    return store.read_yaml(rt.root / changelog.PATH, {})


def test_listing_logs_an_added_event_once_and_links_the_port(rt, gh, monkeypatch):
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    out = generate.generate(rt.root, rt.repo)
    (added,) = log(rt)["events"]
    assert added["event"] == "added" and added["id"] == "good"
    assert added["at"] == store.State.load(rt.root).lifecycle["good"]["listed_at"]
    assert "](ports/good.md)" in out["WHATS-NEW.md"] and "joined the index" in out["WHATS-NEW.md"]
    assert "](WHATS-NEW.md)" in out["README.md"]
    monkeypatch.setenv("AVP_NOW", "2026-12-01T00:00:00Z")
    generate.generate(rt.root, rt.repo)
    assert len(log(rt)["events"]) == 1  # nothing changed, nothing logged


def test_player_facing_changes_are_logged_and_internal_ones_are_not(rt, gh, monkeypatch):
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    generate.generate(rt.root, rt.repo)
    state = store.State.load(rt.root)
    state.health["good"]["commits_since_scan"] = 40  # internal: not news
    state.health["good"]["testflight"] = {"url": "https://testflight.apple.com/join/abcd1234", "status": "open"}
    state.save()
    monkeypatch.setenv("AVP_NOW", "2026-12-01T00:00:00Z")
    out = generate.generate(rt.root, rt.repo)
    _added, updated = log(rt)["events"]
    assert updated["event"] == "updated" and updated["at"] == "2026-12-01T00:00:00Z"
    assert updated["changes"] == [{"field": "testflight", "from": False, "to": True}]
    assert "has a public TestFlight beta" in out["WHATS-NEW.md"].split("## December 2026", 1)[1]


def test_delist_is_logged_without_a_link_and_relisting_reads_as_back(rt, gh, event):  # noqa: F811
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    generate.generate(rt.root, rt.repo)
    ks(rt, event, "good", "delist", "legal-451")
    out = generate.generate(rt.root, rt.repo)
    gone = log(rt)["events"][-1]
    assert gone["event"] == "unavailable" and gone["reason"] == "legal-451"
    page = out["WHATS-NEW.md"]
    assert "is no longer available: repo blocked for legal reasons" in page and "](ports/good.md)" not in page


def test_a_port_hidden_for_a_while_is_not_news():
    seen = {"listed": {"a": {"name": "A", "kind": "port"}}, "unavailable": {}, "removed": []}
    hidden = {"listed": {}, "unavailable": {}, "removed": []}
    first = changelog.update({"seen": seen, "events": []}, hidden, "2026-12-01T00:00:00Z", {})
    assert first["events"] == [] and "a" in first["seen"]["listed"]
    back = changelog.update(first, seen, "2026-12-02T00:00:00Z", {})
    assert back["events"] == []


def test_notes_render_and_months_run_newest_first():
    events = [{"at": "2026-10-04T00:00:00Z", "event": "note", "text": "The index opened."},
              {"at": "2026-11-02T00:00:00Z", "event": "removed", "id": "x", "name": "X", "game": "Game X"}]
    labels = {"md": generate.md, "status": generate.STATUS_LABEL, "reasons": {}, "curator": "trevorbilt"}
    months = changelog.render_items({"events": events}, set(), labels)
    assert [m["month"] for m in months] == ["November 2026", "October 2026"]
    assert months[1]["items"] == [{"day": "Oct 4", "text": "The index opened."}]
    assert json.dumps(months).count("came off the index") == 1
