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
    assert "is no longer available: the repo was taken down." in page and "](ports/good.md)" not in page


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
    labels = generate.changelog_labels()
    months = changelog.render_items({"events": events}, set(), labels)
    assert [m["month"] for m in months] == ["November 2026", "October 2026"]
    assert months[1]["items"] == [{"day": "Oct 4", "text": "The index opened."}]
    assert json.dumps(months).count("came off the index") == 1


def _labels():
    return generate.changelog_labels("https://github.com/o/r/blob/main/")


class FakeGH:
    def __init__(self, existing=()):
        self.existing, self.made = set(existing), []

    def release_by_tag(self, tag):
        return {"tag_name": tag} if tag in self.existing else None

    def create_release(self, tag, target, name, body):
        self.made.append((tag, name, body))
        self.existing.add(tag)


WEEK_LOG = {"events": [
    {"at": "2026-11-22T06:55:54Z", "event": "added", "kind": "port", "id": "old", "name": "Old", "game": "Old Game"},
    # listed on a Sunday, first shown on Tuesday: it belongs to the week it was logged
    {"at": "2026-11-29T23:00:00Z", "logged": "2026-12-01T10:00:00Z", "event": "added", "kind": "port",
     "id": "a", "name": "A", "game": "Game A", "developer": "@dev"},
    {"at": "2026-12-03T10:00:00Z", "logged": "2026-12-03T10:00:00Z", "event": "added", "kind": "emulator",
     "id": "e", "name": "E", "game": "Console games"},
    {"at": "2026-12-04T10:00:00Z", "logged": "2026-12-04T10:00:00Z", "event": "unavailable", "kind": "port",
     "id": "g", "name": "G", "game": "Game G", "reason": "legal-451"},
    {"at": "2026-12-09T10:00:00Z", "logged": "2026-12-09T10:00:00Z", "event": "added", "kind": "port",
     "id": "b", "name": "B", "game": "Game B"},
]}


def test_one_release_per_finished_week_with_news_and_none_twice():
    gh = FakeGH()
    made = changelog.publish_releases(gh, WEEK_LOG, {"a", "e"}, _labels(), store.parse_iso("2026-12-10T00:00:00Z").date(), "sha")
    # the week before RELEASES_FROM stays page-only; the week of Nov 23 has no news; Dec 7 isn't over
    assert made == ["whats-new-2026-11-30"]
    (_tag, name, body), = gh.made
    assert name == "Week of Nov 30: 1 new port, 1 new emulator, 1 port gone"
    assert "[A](https://github.com/o/r/blob/main/ports/a.md) by @dev" in body
    assert "G (*Game G*) is no longer available: the repo was taken down." in body
    assert "HTTP 451" not in body and "Game B" not in body
    again = changelog.publish_releases(gh, WEEK_LOG, {"a", "e"}, _labels(), store.parse_iso("2026-12-10T00:00:00Z").date(), "sha")
    assert again == [] and len(gh.made) == 1


def test_a_missed_monday_catches_up_in_order():
    gh = FakeGH()
    made = changelog.publish_releases(gh, WEEK_LOG, set(), _labels(), store.parse_iso("2026-12-16T00:00:00Z").date(), "sha")
    assert made == ["whats-new-2026-11-30", "whats-new-2026-12-07"]
    assert gh.made[1][1] == "Week of Dec 7: 1 new port"


def test_events_carry_when_they_were_logged(rt, gh, monkeypatch):
    monkeypatch.setenv("AVP_NOW", "2026-12-02T10:00:00Z")
    repo = gh.add_repo("trevorbilt-bot/good", 11)
    list_entry(rt, "good", repo)
    generate.generate(rt.root, rt.repo)
    (added,) = log(rt)["events"]
    assert added["logged"] == "2026-12-02T10:00:00Z"
