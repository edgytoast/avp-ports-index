"""What's new (WHATS-NEW.md): what changed on the index for players, newest first.

state/changelog.yaml holds a small snapshot of what the README showed last time (each listed
entry's player-facing fields, and the Unavailable ports) plus the event log. Every time
generate() runs, it compares the snapshot with what the README shows now, appends one event per
change, and stores the new snapshot. Running it again without other changes adds nothing, so the
page stays the same for the same files.

Events: added, back (relisted), unavailable (moved to Unavailable ports), removed, updated (with
the fields that changed) and note (hand-written, for index features players will notice; add one
to the log by hand with an `at` date and a `text`). Internal changes (scans, CI, health plumbing)
never reach the log because the snapshot doesn't hold them.
"""

from __future__ import annotations

import datetime as dt

from . import store

PATH = "state/changelog.yaml"
EMPTY = {"schema_version": 1, "seen": None, "events": []}
HEADER = ("# What's new log, rendered to WHATS-NEW.md. The build appends events and keeps `seen` "
          "current;\n# add a `note` event by hand ({at, event: note, text}) for an index change "
          "players will notice.\n")


def _developer(dev: dict | None) -> str | None:
    dev = dev or {}
    return dev.get("name") or (f"@{dev['github']}" if dev.get("github") else None)


def snapshot(feed_data: dict, testflight: dict[str, bool]) -> dict:
    """The player-facing part of a feed (any feed version) plus which ports have a TestFlight beta."""
    listed = {}
    for e in feed_data.get("entries") or []:
        listed[e["id"]] = {
            "name": e.get("name"),
            "game": (e.get("game") or {}).get("title"),
            "kind": e.get("kind") or "port",
            "developer": _developer(e.get("developer")),
            "status": e.get("self_reported_status"),
            "verified": bool((e.get("owner_verified") or {}).get("verified")),
            "repo": e.get("repo_url"),
            "prebuilt": "sideload" in (e.get("install") or []),
            "testflight": bool(testflight.get(e["id"])),
        }
    unavailable = {}
    for u in feed_data.get("unavailable") or []:
        unavailable[u["id"]] = {"name": u.get("name"), "game": (u.get("game") or {}).get("title"),
                                "reason": u.get("reason") or "health", "since": u.get("unavailable_since")}
    removed = sorted(t["id"] for t in feed_data.get("tombstones") or [])
    return {"listed": listed, "unavailable": unavailable, "removed": removed}


UPDATE_FIELDS = ("name", "kind", "status", "verified", "repo", "prebuilt", "testflight")


def diff(old: dict | None, new: dict, when: str, listed_at: dict[str, str | None]) -> list[dict]:
    """Events between two snapshots. With no old snapshot, every listed entry counts as added."""
    old = old or {"listed": {}, "unavailable": {}}
    events: list[dict] = []

    def event(what: str, entry_id: str, rec: dict, at: str | None, **extra) -> None:
        events.append({"at": at or when, "event": what, "id": entry_id, "name": rec.get("name"),
                       "game": rec.get("game"), **extra})

    for entry_id, rec in new["listed"].items():
        before = old["listed"].get(entry_id)
        if before is None:
            if entry_id in old["unavailable"] or entry_id in old.get("removed", []):
                event("back", entry_id, rec, when, kind=rec["kind"])
            else:
                event("added", entry_id, rec, listed_at.get(entry_id), kind=rec["kind"],
                      developer=rec.get("developer"))
            continue
        changes = [{"field": f, "from": before.get(f), "to": rec.get(f)}
                   for f in UPDATE_FIELDS if f in before and before.get(f) != rec.get(f)]
        if changes:
            event("updated", entry_id, rec, when, kind=rec["kind"], changes=changes)
    for entry_id, rec in old["listed"].items():
        if entry_id in new["listed"]:
            continue
        gone = new["unavailable"].get(entry_id)
        if gone:
            event("unavailable", entry_id, rec, gone.get("since"), kind=rec["kind"], reason=gone["reason"])
        elif entry_id in new.get("removed", []):
            event("removed", entry_id, rec, when, kind=rec["kind"])
    return events


def carry_hidden(old: dict | None, new: dict) -> dict:
    """A port that drops off the README for a while (waiting on a rescan, say) without being
    delisted or removed isn't news: keep its old record, so its return isn't news either."""
    if not old:
        return new
    listed = dict(new["listed"])
    for entry_id, rec in old["listed"].items():
        if entry_id not in listed and entry_id not in new["unavailable"] and entry_id not in new.get("removed", []):
            listed[entry_id] = rec
    return {**new, "listed": dict(sorted(listed.items()))}


def update(log: dict, new: dict, when: str, listed_at: dict[str, str | None]) -> dict:
    """The log with this build's events appended and the snapshot moved forward."""
    log = {**EMPTY, **(log or {})}
    new = carry_hidden(log.get("seen"), new)
    if log.get("seen") == new:
        return log
    events = list(log.get("events") or []) + diff(log.get("seen"), new, when, listed_at)
    return {**log, "seen": new, "events": events}


def load(root) -> dict:
    return store.read_yaml(root / PATH, EMPTY) or dict(EMPTY)


def dump(log: dict) -> str:
    return HEADER + store.dump_yaml(log)


# --- the page ------------------------------------------------------------------------

def _when(at: str) -> dt.date:
    return dt.date.fromisoformat(str(at)[:10])


def _link(entry_id: str, name: str, listed: set[str]) -> str:
    return f"[{name}](ports/{entry_id}.md)" if entry_id in listed else name


def _change(change: dict, labels: dict) -> str | None:
    field, old, new = change["field"], change.get("from"), change.get("to")
    if field == "status":
        return f"now marked {labels['status'].get(new, new)}" if new else None
    if field == "verified":
        return f"verified on Apple Vision Pro by {labels['curator']}" if new else None
    if field == "repo":
        return f"now listed from [{new.removeprefix('https://github.com/')}]({new})" if new else None
    if field == "prebuilt":
        return "now lists the developer's prebuilt app (not safety-checked)" if new else \
            "no longer lists a prebuilt app"
    if field == "testflight":
        return "has a public TestFlight beta" if new else "no longer has a public TestFlight beta"
    if field == "kind":
        return "moved to the Emulators section" if new == "emulator" else "moved to the Ports section"
    if field == "name":
        return f"renamed from {old}" if old else None
    return None


def line(ev: dict, listed: set[str], labels: dict) -> str | None:
    """One event as a sentence in Markdown, or None if there's nothing worth saying."""
    md = labels["md"]
    kind = ev.get("event")
    if kind == "note":
        return md(ev.get("text") or "", 600) or None
    name, game, entry_id = md(ev.get("name") or ev.get("id"), 80), md(ev.get("game") or "", 120), ev.get("id")
    what = "emulator" if ev.get("kind") == "emulator" else "port"
    if kind == "added":
        dev = f" by {md(ev['developer'], 80)}" if ev.get("developer") else ""
        if what == "emulator":
            return f"New emulator: {_link(entry_id, name, listed)}{dev}, for {game}."
        return f"*{game}* joined the index: {_link(entry_id, name, listed)}{dev}."
    if kind == "back":
        return f"{_link(entry_id, name, listed)} (*{game}*) is back on the list."
    if kind == "unavailable":
        reason = labels["reasons"].get(ev.get("reason") or "health", "")
        reason = f": {reason[0].lower()}{reason[1:].rstrip('.')}" if reason else ""
        return (f"{name} (*{game}*) is no longer available{reason}. "
                f"It's kept in the [Unavailable ports](README.md#unavailable-ports) record.")
    if kind == "removed":
        return f"{name} (*{game}*) came off the index."
    if kind == "updated":
        parts = [p for p in (_change(c, labels) for c in ev.get("changes") or []) if p]
        if not parts:
            return None
        return f"{_link(entry_id, name, listed)} (*{game}*): {'; '.join(parts)}."
    return None


def render_items(log: dict, listed: set[str], labels: dict) -> list[dict]:
    """Events newest first, grouped by month: [{month, items: [{day, text}]}]."""
    indexed = [(i, ev) for i, ev in enumerate(log.get("events") or []) if ev.get("at")]
    indexed.sort(key=lambda p: (str(p[1]["at"])[:10], p[0]), reverse=True)
    months: list[dict] = []
    for _i, ev in indexed:
        text = line(ev, listed, labels)
        if not text:
            continue
        day = _when(ev["at"])
        month = day.strftime("%B %Y")
        if not months or months[-1]["month"] != month:
            months.append({"month": month, "items": []})
        months[-1]["items"].append({"day": f"{day.strftime('%b')} {day.day}", "text": text})
    return months
