"""media.py: README screenshots and the app icon, as links pinned to the scanned commit."""

import base64
import hashlib
import json

import jsonschema

from avpindex import generate, media, store

SHA = "a" * 40
RAW = f"https://raw.githubusercontent.com/o/r/{SHA}"


def png(w: int, h: int, tag: bytes = b"") -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + w.to_bytes(4, "big") + h.to_bytes(4, "big") + b"\x08\x06\x00\x00\x00" + tag


def jpeg(w: int, h: int) -> bytes:
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = b"\xff\xc0\x00\x11\x08" + h.to_bytes(2, "big") + w.to_bytes(2, "big") + b"\x03" + b"\x00" * 9
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"


def test_image_headers():
    assert media.image_info(png(1600, 900)) == ("png", 1600, 900)
    assert media.image_info(jpeg(1920, 1080)) == ("jpeg", 1920, 1080)
    assert media.image_info(b"GIF89a" + (640).to_bytes(2, "little") + (360).to_bytes(2, "little") + b"\x00" * 8) == ("gif", 640, 360)
    vp8x = b"RIFF\x00\x00\x00\x00WEBPVP8X" + b"\x00" * 8 + (1279).to_bytes(3, "little") + (719).to_bytes(3, "little")
    assert media.image_info(vp8x) == ("webp", 1280, 720)
    assert media.image_info(b"<svg xmlns='http://www.w3.org/2000/svg'/>") is None  # SVG never counts
    assert media.image_info(png(0, 10)) is None and media.image_info(png(9000, 10)) is None
    assert media.image_info(b"\xff\xd8\xff") is None  # truncated


def test_readme_images_in_reading_order_without_comments():
    text = ('![Shot one](docs/a.png)\n<!-- ![hidden](docs/b.png) -->\n'
            '<p><img alt="Shot two" src="docs/c.jpg" width="300"></p>\n![badge](https://img.shields.io/x.svg)\n'
            '![Shot one again](docs/a.png)')
    assert media.readme_images(text) == [("docs/a.png", "Shot one"), ("docs/c.jpg", "Shot two"),
                                         ("https://img.shields.io/x.svg", "badge")]


def test_pin_keeps_only_this_repo_and_github_attachments():
    pin = lambda src, d="": media.pin("O", "R", SHA, d, src)
    assert pin("docs/a.png") == f"{RAW.replace('/o/r/', '/O/R/')}/docs/a.png"
    assert pin("../img/a.png", "docs") == f"https://raw.githubusercontent.com/O/R/{SHA}/img/a.png"
    assert pin("../../a.png", "docs") is None  # out of the repo
    assert pin("https://github.com/o/r/blob/main/docs/a.png") == f"https://raw.githubusercontent.com/O/R/{SHA}/docs/a.png"
    assert pin("https://raw.githubusercontent.com/o/r/main/docs/a.png") == f"https://raw.githubusercontent.com/O/R/{SHA}/docs/a.png"
    assert pin("https://github.com/user-attachments/assets/1234-abcd") == "https://github.com/user-attachments/assets/1234-abcd"
    assert pin("https://github.com/someone/else/blob/main/a.png") is None  # another repo
    assert pin("https://img.shields.io/badge/x.svg") is None and pin("https://example.com/track.gif") is None
    assert pin("http://github.com/o/r/blob/main/a.png") is None  # not https


def test_icon_layers_back_to_front_and_flat_fallback():
    stack = "App/Assets.xcassets/AppIcon.solidimagestack"
    paths = [f"{stack}/Front.solidimagestacklayer/Content.imageset/f.png",
             f"{stack}/Back.solidimagestacklayer/Content.imageset/b.png",
             f"{stack}/Contents.json", "Other/AppIcon.appiconset/i.png"]
    kind, layers = media.icon_candidates(paths)
    assert kind == "layered" and [name for name, _ in layers] == ["back", "front"]
    assert media.icon_candidates(["X/AppIcon.appiconset/a.png"]) == ("flat", [("icon", ["X/AppIcon.appiconset/a.png"])])
    assert media.icon_candidates(paths, "Other/AppIcon.appiconset/i.png") == ("flat", [("icon", ["Other/AppIcon.appiconset/i.png"])])
    assert media.icon_candidates(paths, "missing.png") is None


class Files:
    """A GitHub stand-in: a tree, a README, and raw files by URL."""

    def __init__(self, files: dict[str, bytes], readme: str | None):
        self.files, self.readme, self.gets = files, readme, []

    def tree(self, owner, name, sha):
        return {"tree": [{"path": p, "type": "blob"} for p in self.files]}

    def get(self, path, params=None):
        if path.endswith("/readme") and self.readme is not None:
            return {"encoding": "base64", "content": base64.b64encode(self.readme.encode()).decode(), "path": "README.md"}
        return None


class Http:
    def __init__(self, files: dict[str, bytes], redirects: dict[str, str] | None = None):
        self.files, self.redirects, self.urls = files, redirects or {}, []

    def get(self, url, **_kw):
        self.urls.append(url)
        return Resp(self.redirects.get(url), self.files.get(url.split(f"/{SHA}/", 1)[-1]))


class Resp:
    def __init__(self, location, data):
        self.location, self.data = location, data
        self.is_redirect = location is not None
        self.status_code = 302 if location else (200 if data is not None else 404)
        self.headers = {"Location": location} if location else {"Content-Length": str(len(data or b""))}

    def iter_content(self, _n):
        yield self.data

    def close(self):
        pass


def test_collect_from_readme_with_layered_icon():
    stack = "App/Assets.xcassets/AppIcon.solidimagestack"
    files = {"docs/shot.png": png(1600, 900), "docs/logo.png": png(400, 160),
             f"{stack}/Back.solidimagestacklayer/Content.imageset/b.png": png(1024, 1024, b"back"),
             f"{stack}/Middle.solidimagestacklayer/Content.imageset/m.png": png(1024, 1024, b"same"),
             f"{stack}/Front.solidimagestacklayer/Content.imageset/f.png": png(1024, 1024, b"same")}
    readme = "![logo](docs/logo.png)\n![The ranch](docs/shot.png)\n![tracker](https://example.com/t.gif)"
    record = media.collect(Files(files, readme), Http(files), "https://github.com/o/r", SHA, None)
    assert record["source"] == "readme" and [s["url"] for s in record["screenshots"]] == [f"{RAW}/docs/shot.png"]
    shot = record["screenshots"][0]
    assert shot["alt"] == "The ranch" and (shot["width"], shot["height"]) == (1600, 900)
    assert shot["sha256"] == hashlib.sha256(files["docs/shot.png"]).hexdigest()
    reasons = {s["reason"] for s in record["skipped"]}
    assert "smaller than 480x270" in reasons and "not this repo's file or a GitHub attachment" in reasons
    icon = record["icon"]  # the front layer repeats the middle one, so it's dropped
    assert icon["kind"] == "layered" and [layer["layer"] for layer in icon["layers"]] == ["back", "middle"]


def test_collect_with_picks_and_a_redirect_off_github():
    files = {"art/a.png": png(1280, 720)}
    redirects = {f"{RAW}/art/a.png": "https://evil.example/a.png"}
    record = media.collect(Files(files, None), Http(files, redirects), "https://github.com/o/r", SHA,
                           {"screenshots": ["art/a.png", "art/missing.png"]})
    assert record["source"] == "entry" and record["screenshots"] == [] and record["icon"] is None
    assert {s["reason"] for s in record["skipped"]} == {"not a GitHub URL", "not a file at the scanned commit"}


class RT:
    def __init__(self, files, readme):
        self.gh, self.http, self.lines = Files(files, readme), Http(files), []

    def summary(self, line):
        self.lines.append(line)


def test_refresh_follows_the_pin_and_respects_opt_out(tmp_path):
    files = {"docs/shot.png": png(1600, 900)}
    state = store.State(root=tmp_path, lifecycle={"p": {"status": "listed"}, "gone": {"status": "pulled"}},
                        health={"p": {"scanned_commit": SHA}}, media={"gone": {"commit": SHA}})
    entries = {"p": {"repo": "https://github.com/o/r"}}
    rt = RT(files, "![x](docs/shot.png)")
    media.refresh(rt, state, entries)
    assert "gone" not in state.media and len(state.media["p"]["screenshots"]) == 1
    rt.http.urls.clear()
    media.refresh(rt, state, entries)  # same commit, same picks: nothing fetched
    assert rt.http.urls == []
    entries["p"]["media"] = False
    media.refresh(rt, state, entries)
    assert "p" not in state.media


def test_feed_carries_media_and_validates(tmp_path):
    record = {"commit": SHA, "source": "readme", "skipped": [], "choice": None, "collected_at": "2026-10-08T00:00:00Z",
              "screenshots": [{"url": f"{RAW}/docs/shot.png", "alt": None, "format": "png", "width": 1600,
                               "height": 900, "bytes": 10, "sha256": "0" * 64}],
              "icon": {"kind": "flat", "url": f"{RAW}/icon.png", "format": "png", "width": 1024, "height": 1024,
                       "bytes": 10, "sha256": "1" * 64}}
    block = media.feed_block(record)
    assert set(block) == {"commit", "source", "icon", "screenshots"}
    schema = store.load_json("schema/feed-v1.schema.json")
    validator = jsonschema.Draft202012Validator({"$ref": "#/$defs/media", "$defs": schema["$defs"]})
    validator.validate(block)
    state_schema = store.load_json("schema/state.schema.json")
    jsonschema.Draft202012Validator({"$ref": "#/$defs/media", "$defs": state_schema["$defs"]}).validate({"p": record})
    assert media.feed_block({**record, "icon": None, "screenshots": []}) is None
    assert generate.attr('a "quoted" <tag>') == "a &quot;quoted&quot; &lt;tag&gt;"
    assert json.dumps(block)  # plain JSON


def test_refresh_without_a_session_and_survives_any_failure(tmp_path, monkeypatch):
    """Production runtimes carry no http session: refresh makes its own. A failure of any kind keeps the old
    record and never raises, so the health check and build-surfaces can't be stopped by pictures."""
    files = {"docs/shot.png": png(1600, 900)}
    made = []
    monkeypatch.setattr(media.requests, "Session", lambda: made.append(1) or Http(files))
    state = store.State(root=tmp_path, lifecycle={"p": {"status": "listed"}}, health={"p": {"scanned_commit": SHA}})
    rt = RT(files, "![x](docs/shot.png)")
    rt.http = None
    media.refresh(rt, state, {"p": {"repo": "https://github.com/o/r"}})
    assert made and len(state.media["p"]["screenshots"]) == 1
    old = dict(state.media["p"])
    state.health["p"]["scanned_commit"] = "b" * 40

    def boom(*_a, **_k):
        raise RuntimeError("anything at all")
    monkeypatch.setattr(media, "collect", boom)
    media.refresh(rt, state, {"p": {"repo": "https://github.com/o/r"}})
    assert state.media["p"] == old and any("RuntimeError" in line for line in rt.lines)


def test_readme_fetches_are_capped():
    files = {f"docs/{i}.png": png(100, 100) for i in range(20)}  # all too small, so every one is tried
    readme = "\n".join(f"![{i}](docs/{i}.png)" for i in range(20))
    http = Http(files)
    media.collect(Files(files, readme), http, "https://github.com/o/r", SHA, None)
    assert len(http.urls) == media.MAX_TRIES
