"""Emulators section (decision 69): `kind: emulator` entries get their own README and llms.txt section,
and the feed carries `kind` for every entry."""
from __future__ import annotations

import json

import jsonschema
from conftest import list_entry, write_entry

from avpindex import generate, store


def test_emulators_get_their_own_section_and_the_feed_says_kind(rt, gh):
    for entry_id, rid, extra in (("plain", 31, {}), ("emu", 32, {"kind": "emulator"})):
        repo = gh.add_repo(f"trevorbilt-bot/{entry_id}", rid)
        list_entry(rt, entry_id, repo)
        write_entry(rt.root, entry_id, f"trevorbilt-bot/{entry_id}", **extra)
    out = generate.generate(rt.root, rt.repo)
    feed = {e["id"]: e for e in json.loads(out["feed/v1/index.json"])["entries"]}
    assert feed["plain"]["kind"] == "port" and feed["emu"]["kind"] == "emulator"
    readme = out["README.md"]
    ports, emulators = readme.split("## Ports", 1)[1].split("## Emulators", 1)
    assert "(ports/plain.md)" in ports and "(ports/emu.md)" not in ports
    assert "(ports/emu.md)" in emulators and "(ports/plain.md)" not in emulators.split("##", 1)[0]
    llms = out["llms.txt"]
    assert "1 port and 1 emulator listed." in llms and "## Emulators" in llms
    assert out["ports/emu.md"].count("Emulator by ") == 1 and "Port by " in out["ports/plain.md"]


def test_no_emulators_means_no_section(rt, gh):
    repo = gh.add_repo("trevorbilt-bot/plain", 33)
    list_entry(rt, "plain", repo)
    out = generate.generate(rt.root, rt.repo)
    assert "## Emulators" not in out["README.md"] and "## Emulators" not in out["llms.txt"]


def test_schema_accepts_kind_and_rejects_others():
    schema = store.load_json("schema/entry.schema.json")
    kind = {"$defs": schema.get("$defs", {}), **schema["properties"]["kind"]}
    jsonschema.validate("emulator", kind)
    jsonschema.validate("port", kind)
    try:
        jsonschema.validate("rom-hack", kind)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("an unknown kind must fail")
