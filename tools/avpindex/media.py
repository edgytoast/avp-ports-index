"""README screenshots and the app icon of each listed port, for the feed's `media` block (feed 1.4.0).

At the commit the index scanned, take up to three images from the port's README and its app icon,
and record each as a link pinned to that commit with its size and SHA-256. The index links, it
never copies: apps fetch from GitHub and check the hash, so they show exactly what was reviewed and
no other host sees their users.

Only the repo's own files and GitHub's attachments count; other hosts (badges, shields, trackers)
are skipped. Files are read, never run, and never decoded: sizes come from the image header.
An entry can pick its own images, or opt out, with `media` in its entry file.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from urllib.parse import quote, unquote, urljoin, urlparse

import requests

from . import store, validate
from .checks import decode_content
from .lifecycle import LISTED

MAX_BYTES = 8 * 1024 * 1024
MAX_SHOTS = 3
MAX_TRIES = 8  # README images fetched per entry, at most
MAX_LAYERS = 3
MIN_SHOT = (480, 270)
MAX_SIDE = 8192
MAX_HOPS = 5
FORMATS = ("png", "jpeg", "gif", "webp")
LAYER_ORDER = ("back", "middle", "front")
GITHUB_HOSTS = ("github.com", "raw.githubusercontent.com")
GITHUB_SUFFIX = ".githubusercontent.com"
RAW = "https://raw.githubusercontent.com"


# --- images ---------------------------------------------------------------------------------

def image_info(data: bytes) -> tuple[str, int, int] | None:
    """(format, width, height) from an image's header, or None if it isn't a PNG, JPEG, GIF or WebP."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
            size = (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))
            kind = "png"
        elif data[:6] in (b"GIF87a", b"GIF89a"):
            size = (int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little"))
            kind = "gif"
        elif data[:2] == b"\xff\xd8":
            size, kind = _jpeg_size(data), "jpeg"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            size, kind = _webp_size(data), "webp"
        else:
            return None
    except IndexError:
        return None
    if not size or not (0 < size[0] <= MAX_SIDE and 0 < size[1] <= MAX_SIDE):
        return None
    return kind, size[0], size[1]


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if marker in sof:
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        if length < 2:
            return None
        i += 2 + length
    return None


def _webp_size(data: bytes) -> tuple[int, int] | None:
    chunk = data[12:16]
    if chunk == b"VP8 ":
        return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
    if chunk == b"VP8L":
        b = data[21:25]
        return 1 + (((b[1] & 0x3F) << 8) | b[0]), 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
    if chunk == b"VP8X":
        return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
    return None


def is_github(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host in GITHUB_HOSTS or host.endswith(GITHUB_SUFFIX))


def download(http: requests.Session, url: str, limit: int = MAX_BYTES) -> bytes:
    """A file's bytes, following redirects only within GitHub, capped at `limit` (8 MB for pictures)."""
    too_big = f"over {limit // (1024 * 1024)} MB"
    for _hop in range(MAX_HOPS + 1):
        if not is_github(url):
            raise ValueError("not a GitHub URL")
        resp = http.get(url, allow_redirects=False, stream=True, timeout=30)
        try:
            if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                url = urljoin(url, resp.headers.get("Location", ""))
                continue
            if resp.status_code != 200:
                raise ValueError(f"HTTP {resp.status_code}")
            if int(resp.headers.get("Content-Length") or 0) > limit:
                raise ValueError(too_big)
            data = bytearray()
            for chunk in resp.iter_content(65536):
                data += chunk
                if len(data) > limit:
                    raise ValueError(too_big)
            return bytes(data)
        finally:
            resp.close()
    raise ValueError("too many redirects")


def describe(http: requests.Session, url: str, alt: str | None = None) -> dict:
    data = download(http, url)
    info = image_info(data)
    if not info or info[0] not in FORMATS:
        raise ValueError("not a PNG, JPEG, GIF or WebP")
    return {"url": url, "alt": alt, "format": info[0], "width": info[1], "height": info[2],
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


# --- README images ----------------------------------------------------------------------------

_MD_IMAGE = re.compile(r"!\[([^\]\n]{0,300})\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"\n]*\")?\s*\)")
_HTML_IMG = re.compile(r"<img\b[^>]{0,2000}>", re.IGNORECASE)
_ATTR = re.compile(r"""\b(src|alt)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def readme_images(markdown: str) -> list[tuple[str, str]]:
    """Every image a README shows, as (src, alt), in reading order. Commented-out ones don't count."""
    text = _COMMENT.sub(lambda m: " " * len(m.group(0)), markdown)
    found = [(m.start(), m.group(2), m.group(1)) for m in _MD_IMAGE.finditer(text)]
    for m in _HTML_IMG.finditer(text):
        attrs = {a.group(1).lower(): a.group(2) if a.group(2) is not None else a.group(3)
                 for a in _ATTR.finditer(m.group(0))}
        if attrs.get("src"):
            found.append((m.start(), attrs["src"], attrs.get("alt") or ""))
    seen, out = set(), []
    for _pos, src, alt in sorted(found):
        if src not in seen:
            seen.add(src)
            out.append((src, " ".join(alt.split())))
    return out


def safe_path(path: str) -> str | None:
    """A repo path with no way out of the repo, or None."""
    parts = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts) or None


def raw_url(owner: str, name: str, sha: str, path: str) -> str:
    return f"{RAW}/{owner}/{name}/{sha}/{quote(path)}"


def pin(owner: str, name: str, sha: str, readme_dir: str, src: str) -> str | None:
    """A README image as a link pinned to the scanned commit, or None unless it's this repo's own
    file or a GitHub attachment."""
    parsed = urlparse(src.strip())
    host = (parsed.hostname or "").lower()
    segs = [unquote(s) for s in parsed.path.split("/") if s]
    same = lambda o, r: o.lower() == owner.lower() and r.lower() == name.lower()
    if not parsed.scheme and not parsed.netloc:
        path = unquote(parsed.path)
        joined = path.lstrip("/") if path.startswith("/") else posixpath.join(readme_dir, path)
        clean = safe_path(joined)
        return raw_url(owner, name, sha, clean) if clean else None
    if parsed.scheme != "https":
        return None
    if host == "raw.githubusercontent.com" and len(segs) >= 4 and same(segs[0], segs[1]):
        clean = safe_path("/".join(segs[3:]))
        return raw_url(owner, name, sha, clean) if clean else None
    if host == "github.com" and len(segs) >= 5 and same(segs[0], segs[1]) and segs[2] in ("blob", "raw"):
        clean = safe_path("/".join(segs[4:]))
        return raw_url(owner, name, sha, clean) if clean else None
    if host == "github.com" and segs[:2] == ["user-attachments", "assets"] and len(segs) == 3:
        return f"https://github.com/user-attachments/assets/{quote(segs[2])}"
    if host == "user-images.githubusercontent.com":
        return src.strip()
    return None


# --- icons ------------------------------------------------------------------------------------

def _pngs(paths: list[str], prefix: str) -> list[str]:
    return [p for p in paths if p.startswith(prefix) and p.lower().endswith(".png")]


def layer_name(directory: str) -> str:
    return directory.rsplit("/", 1)[-1].split(".")[0].lower()


def icon_candidates(paths: list[str], override: str | None = None) -> tuple[str, list[tuple[str, list[str]]]] | None:
    """The app icon's files: ("layered", [(layer, pngs)...]) for a visionOS image stack, or
    ("flat", [("icon", pngs)]) for an app icon set or a single PNG. Shortest path wins."""
    if override:
        if override.lower().endswith(".png"):
            return ("flat", [("icon", [override])]) if override in paths else None
        stacks = [override.rstrip("/")]
    else:
        stacks = sorted({p.split(".solidimagestack/")[0] + ".solidimagestack" for p in paths
                         if ".solidimagestack/" in p and "AppIcon" in p.split(".solidimagestack/")[0]},
                        key=lambda s: (s.count("/"), s))
    for stack in stacks:
        dirs = sorted({p[: p.index(".solidimagestacklayer") + len(".solidimagestacklayer")]
                       for p in paths if p.startswith(stack + "/") and ".solidimagestacklayer" in p})
        layers = [(layer_name(d), _pngs(paths, d + "/")) for d in dirs]
        layers = [layer for layer in layers if layer[1]]
        if layers:
            rank = {n: i for i, n in enumerate(LAYER_ORDER)}
            layers.sort(key=lambda layer: rank.get(layer[0], len(rank)))
            return "layered", layers[:MAX_LAYERS]
    if override:
        return None
    sets = sorted({p.split(".appiconset/")[0] + ".appiconset" for p in paths
                   if ".appiconset/" in p and "AppIcon" in p}, key=lambda s: (s.count("/"), s))
    for icon_set in sets:
        pngs = _pngs(paths, icon_set + "/")
        if pngs:
            return "flat", [("icon", pngs)]
    return None


def collect_icon(http, owner: str, name: str, sha: str, paths: list[str], override: str | None,
                 skipped: list) -> dict | None:
    found = icon_candidates(paths, override)
    if not found:
        return None
    kind, layers = found
    out = []
    for layer, pngs in layers:
        best = None
        for path in pngs[:8]:
            url = raw_url(owner, name, sha, path)
            try:
                d = describe(http, url)
            except (ValueError, requests.RequestException) as exc:
                skipped.append({"src": path, "reason": str(exc)[:120]})
                continue
            if d["width"] != d["height"]:
                skipped.append({"src": path, "reason": "not square"})
                continue
            if not best or d["width"] > best["width"]:
                best = d
        if best:
            best.pop("alt", None)
            out.append({"layer": layer, **best})
    # A layer identical to the one under it adds nothing (it would only drift on hover).
    out = [d for i, d in enumerate(out) if i == 0 or d["sha256"] != out[i - 1]["sha256"]]
    if not out:
        return None
    if kind == "flat" or len(out) == 1:
        single = dict(out[0])
        single.pop("layer", None)
        return {"kind": "flat", **single}
    return {"kind": "layered", "layers": out}


# --- one entry --------------------------------------------------------------------------------

def collect(reader, http, repo_url: str, sha: str, choice: dict | None) -> dict:
    """The media record for one entry at one commit. `choice` is the entry's `media` (picks), if any."""
    owner, name = validate.parse_repo_url(repo_url)
    skipped: list[dict] = []
    shots: list[dict] = []
    tree = reader.tree(owner, name, sha) or {}
    paths = [t["path"] for t in tree.get("tree") or [] if t.get("type") == "blob"]
    picks = (choice or {}).get("screenshots")
    if picks is not None:
        refs = [(raw_url(owner, name, sha, p), "") for p in picks if safe_path(p) == p and p in paths]
        for p in picks:
            if not (safe_path(p) == p and p in paths):
                skipped.append({"src": p, "reason": "not a file at the scanned commit"})
        source = "entry"
    else:
        source = "readme"
        refs = []
        readme = reader.get(f"/repos/{quote(owner)}/{quote(name)}/readme", {"ref": sha})
        if isinstance(readme, dict):
            text = decode_content(readme).decode("utf-8", "replace")
            readme_dir = posixpath.dirname(readme.get("path") or "")
            for src, alt in readme_images(text):
                url = pin(owner, name, sha, readme_dir, src)
                if url:
                    refs.append((url, alt))
                else:
                    skipped.append({"src": src[:200], "reason": "not this repo's file or a GitHub attachment"})
    for tries, (url, alt) in enumerate(refs):
        if len(shots) == MAX_SHOTS or tries == MAX_TRIES:
            break
        try:
            d = describe(http, url, alt or None)
        except (ValueError, requests.RequestException) as exc:
            skipped.append({"src": url, "reason": str(exc)[:120]})
            continue
        if d["width"] < MIN_SHOT[0] or d["height"] < MIN_SHOT[1]:
            skipped.append({"src": url, "reason": f"smaller than {MIN_SHOT[0]}x{MIN_SHOT[1]}"})
            continue
        shots.append(d)
    icon = collect_icon(http, owner, name, sha, paths, (choice or {}).get("icon"), skipped)
    return {"commit": sha, "source": source, "icon": icon, "screenshots": shots, "skipped": skipped[:20]}


def choice_key(choice: object) -> str | None:
    """A short fingerprint of an entry's `media` picks, so a change to them triggers a refresh."""
    if choice is None:
        return None
    return hashlib.sha256(json.dumps(choice, sort_keys=True).encode()).hexdigest()[:16]


def refresh(rt, state: store.State, entries: dict[str, dict]) -> None:
    """Bring state/media.yaml up to date: collect for every listed entry whose scanned commit or picks
    changed, drop records of entries no longer listed. A failure keeps the old record."""
    # Downloads use a session of their own: no token ever travels with a file request.
    http = rt.http or requests.Session()
    for entry_id in list(state.media):
        if (state.lifecycle.get(entry_id) or {}).get("status") != LISTED:
            del state.media[entry_id]
    for entry_id, record in sorted(state.lifecycle.items()):
        if record.get("status") != LISTED:
            continue
        entry = entries.get(entry_id) or {}
        sha = (state.health.get(entry_id) or {}).get("scanned_commit")
        if not entry or not sha:
            continue
        choice = entry.get("media")
        if choice is False:
            if state.media.pop(entry_id, None) is not None:
                rt.summary(f"{entry_id}: media opted out")
            continue
        key = choice_key(choice)
        old = state.media.get(entry_id) or {}
        if old.get("commit") == sha and old.get("choice") == key:
            continue
        try:
            new = collect(rt.gh, http, entry["repo"], sha, choice)
        except Exception as exc:  # noqa: BLE001 - pictures must never stop the health check or a build
            rt.summary(f"{entry_id}: media not collected ({type(exc).__name__}: {str(exc)[:120]}); "
                       "kept the previous record")
            continue
        new["choice"] = key
        new["collected_at"] = store.iso(store.utcnow())
        state.media[entry_id] = new
        rt.summary(f"{entry_id}: media at {sha[:12]}: {len(new['screenshots'])} screenshot(s), "
                   f"icon {new['icon']['kind'] if new['icon'] else 'none'}, {len(new['skipped'])} skipped")


def feed_block(record: dict | None) -> dict | None:
    """The feed's `media` for an entry: what apps need, without the bookkeeping."""
    if not record or (not record.get("icon") and not record.get("screenshots")):
        return None
    return {"commit": record["commit"], "source": record["source"], "icon": record.get("icon"),
            "screenshots": list(record.get("screenshots") or [])}
