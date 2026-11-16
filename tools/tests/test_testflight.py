"""testflight.py: public TestFlight betas found in a port's own repo, confirmed on Apple's site."""

import base64

from avpindex import testflight

OPEN = "<html><head><title>Join the Mountain 64 beta - TestFlight - Apple</title></head><body>Step 2 View Mountain 64 Beta</body></html>"
FULL = "<html><head><title>Join the X beta - TestFlight - Apple</title></head><body><p>This beta is full.</p></body></html>"
CLOSED = "<title>Join the X beta - TestFlight - Apple</title><p>This beta isn&#8217;t accepting any new testers right now.</p>"
GONE = "<html><head><title>Not Found</title></head><body>Not Found</body></html>"


class Resp:
    def __init__(self, status_code, text):
        self.status_code, self.text = status_code, text


class Http:
    def __init__(self, pages):
        self.pages, self.seen = pages, []

    def get(self, url, **kwargs):
        self.seen.append((url, kwargs.get("headers") or {}))
        return Resp(*self.pages.get(url, (404, GONE)))


class Reader:
    def __init__(self, readmes=None, releases=None):
        self.readmes, self.rels, self.calls = readmes or {}, releases or {}, []

    def get(self, path, params=None, **kwargs):
        self.calls.append((path, params))
        full = path.split("/repos/")[1].rsplit("/readme", 1)[0]
        text = self.readmes.get(full)
        if text is None:
            return None
        return {"path": "README.md", "encoding": "base64", "content": base64.b64encode(text.encode()).decode()}

    def releases(self, owner, name, count=30):
        return self.rels.get(f"{owner}/{name}", [])

    def branch_head(self, owner, name, ref):
        return "b" * 40


def repo(full, **extra):
    owner, name = full.split("/")
    return {"owner": {"login": owner}, "name": name, "default_branch": "main", "description": "", "homepage": None, **extra}


def test_codes_in_reading_order_once():
    text = ("[![TestFlight](badge.svg)](https://testflight.apple.com/join/bGjuRjfg) and again "
            "https://testflight.apple.com/join/bGjuRjfg, then http://testflight.apple.com/join/n6sD7wYX "
            "but not https://testflight.apple.com/join/ab or https://example.com/join/zzzzzzzz")
    assert testflight.codes(text) == ["bGjuRjfg", "n6sD7wYX"]


def test_classify_apple_pages():
    assert testflight.classify(200, OPEN) == ("open", "Mountain 64")
    assert testflight.classify(200, FULL) == ("full", "X")
    assert testflight.classify(200, CLOSED) == ("closed", "X")
    assert testflight.classify(200, GONE) == ("gone", None)
    assert testflight.classify(404, "") == ("gone", None)


def test_open_beta_in_readme_is_recorded_and_probed_without_token():
    reader = Reader({"o/r": "Try it: https://testflight.apple.com/join/bGjuRjfg"})
    http = Http({testflight.url("bGjuRjfg"): (200, OPEN)})
    record, line = testflight.check(reader, http, repo("o/r"), {})
    assert record == {"url": "https://testflight.apple.com/join/bGjuRjfg", "status": "open",
                      "app": "Mountain 64", "source": "o/r README.md"}
    assert reader.calls[0] == ("/repos/o/r/readme", {"ref": "b" * 40})  # the linked branch
    assert all("Authorization" not in h for _, h in http.seen)


def test_fork_reads_parent_only_when_the_copy_has_none():
    parent = repo("dev/port")
    copy = repo("curator/port", fork=True, parent=parent)
    http = Http({testflight.url("n6sD7wYX"): (200, OPEN), testflight.url("AAAAAAAA"): (200, OPEN)})
    reader = Reader(releases={"dev/port": [{"tag_name": "v1", "body": "Beta: https://testflight.apple.com/join/n6sD7wYX"}]})
    record, _ = testflight.check(reader, http, copy, {})
    assert record["url"].endswith("n6sD7wYX") and record["source"] == "dev/port release v1"
    reader = Reader({"curator/port": "https://testflight.apple.com/join/AAAAAAAA"},
                    {"dev/port": [{"body": "https://testflight.apple.com/join/n6sD7wYX"}]})
    record, _ = testflight.check(reader, http, copy, {})
    assert record["url"].endswith("AAAAAAAA")


def test_not_a_fork_never_reads_elsewhere():
    reader = Reader()
    record, line = testflight.check(reader, Http({}), repo("o/r", parent=repo("x/y")), {})
    assert record is None and line == "no TestFlight link"
    assert [p for p, _ in reader.calls] == ["/repos/o/r/readme"]


def test_full_is_kept_closed_and_gone_are_left_out():
    reader = Reader({"o/r": "https://testflight.apple.com/join/FULLFULL"})
    record, _ = testflight.check(reader, Http({testflight.url("FULLFULL"): (200, FULL)}), repo("o/r"), {})
    assert record["status"] == "full"
    reader = Reader({"o/r": "https://testflight.apple.com/join/SHUTSHUT https://testflight.apple.com/join/GONEGONE"})
    record, line = testflight.check(reader, Http({testflight.url("SHUTSHUT"): (200, CLOSED)}), repo("o/r"), {})
    assert record is None and "no live beta" in line and "(closed, X)" in line and "(gone)" in line


def test_two_live_betas_are_ambiguous():
    reader = Reader({"o/r": "https://testflight.apple.com/join/AAAAAAAA https://testflight.apple.com/join/BBBBBBBB"})
    http = Http({testflight.url("AAAAAAAA"): (200, OPEN), testflight.url("BBBBBBBB"): (200, OPEN)})
    record, line = testflight.check(reader, http, repo("o/r"), {})
    assert record is None and "more than one live beta" in line


class Rt:
    def __init__(self, gh, http):
        self.gh, self.http, self.lines = gh, http, []

    def summary(self, line):
        self.lines.append(line)


def test_refresh_keeps_the_old_record_on_error_and_reports_only_changes():
    class Broken(Reader):
        def get(self, *a, **k):
            raise RuntimeError("boom")

    old = {"url": "https://testflight.apple.com/join/bGjuRjfg", "status": "open", "app": "M", "source": "o/r README.md"}
    health = {"testflight": dict(old)}
    rt = Rt(Broken(), Http({}))
    testflight.refresh(rt, health, "e", {}, repo("o/r"))
    assert health["testflight"] == old and "kept the previous record" in rt.lines[0]
    rt = Rt(Reader({"o/r": "https://testflight.apple.com/join/bGjuRjfg"}),
            Http({testflight.url("bGjuRjfg"): (200, OPEN.replace("Mountain 64", "M"))}))
    testflight.refresh(rt, health, "e", {}, repo("o/r"))
    assert health["testflight"] == old and rt.lines == []


def test_health_check_records_the_beta_and_the_readme_shows_it(rt, gh, monkeypatch):
    import json

    import requests
    from conftest import SHA, FakeHTTP, git, list_entry

    from avpindex import generate, health, store

    class AppleHTTP(FakeHTTP):
        def get(self, url, **kw):
            if url.startswith("https://testflight.apple.com/join/"):
                resp = requests.Response()
                resp.status_code, resp._content, resp.encoding = 200, OPEN.encode(), "utf-8"
                return resp
            return super().get(url, **kw)

    rt.http = AppleHTTP()
    repo = gh.add_repo("trevorbilt-bot/beta", 31)
    list_entry(rt, "beta", repo)
    gh.files[("trevorbilt-bot/beta", "README.md", SHA(31))] = \
        b"# Beta\n\n[![TestFlight](b.svg)](https://testflight.apple.com/join/bGjuRjfg)\n"
    git(rt.root, "add", "-A")
    git(rt.root, "commit", "-qm", "listed")
    monkeypatch.setenv("AVP_NOW", "2026-10-04T06:17:00Z")
    health.run(rt)
    state = store.State.load(rt.root)
    assert state.health["beta"]["testflight"] == {"url": "https://testflight.apple.com/join/bGjuRjfg", "status": "open",
                                                  "app": "Mountain 64", "source": "trevorbilt-bot/beta README.md"}
    readme = generate.generate(rt.root, rt.repo)["README.md"]
    assert "| Install guide | TestFlight |" in readme
    assert "| [Join the beta](https://testflight.apple.com/join/bGjuRjfg) |" in readme
    import jsonschema
    schema = json.loads((rt.root / "schema" / "state.schema.json").read_text())
    jsonschema.validate(state.health, {**schema, **schema["$defs"]["health"]})
