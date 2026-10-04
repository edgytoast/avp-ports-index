"""Validators for untrusted input (spec §8.0 rule 3) and escaping for untrusted text (rule 4).

Every value that comes from an event payload, a workflow input, an issue form or a
contributor's file passes through here before it is used.
"""

from __future__ import annotations

import datetime as _dt
import html
import re

import yaml

ENTRY_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_NAME_RE = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
REPO_URL_RE = re.compile(r"^https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9._-]+)$")
LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?(\[bot\])?$")

MAX_ENTRY_BYTES = 16 * 1024


class InvalidInput(ValueError):
    """An untrusted value failed validation. Jobs fail on this."""


class YamlError(ValueError):
    """A contributor's YAML file is unsafe or unparsable (check S1-02)."""


def entry_id(value: object) -> str:
    """An entry id: ^[a-z0-9]+(-[a-z0-9]+)*$, at most 64 characters."""
    if not isinstance(value, str) or len(value) > 64 or not ENTRY_ID_RE.match(value):
        raise InvalidInput("invalid entry id")
    return value


def positive_int(value: object, what: str = "number") -> int:
    """A PR or issue number: a positive integer (accepts its decimal string form)."""
    if isinstance(value, bool):
        raise InvalidInput(f"invalid {what}")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,9}", value):
        number = int(value)
    else:
        raise InvalidInput(f"invalid {what}")
    if number <= 0:
        raise InvalidInput(f"invalid {what}")
    return number


def pr_number(value: object) -> int:
    return positive_int(value, "PR number")


def issue_number(value: object) -> int:
    return positive_int(value, "issue number")


def sha(value: object) -> str:
    """A full 40-character lowercase commit SHA."""
    if not isinstance(value, str) or not SHA_RE.match(value):
        raise InvalidInput("invalid commit SHA")
    return value


def repo_name(value: object) -> str:
    """An owner/name pair."""
    if not isinstance(value, str) or not REPO_NAME_RE.match(value) or value.endswith(".git"):
        raise InvalidInput("invalid repository name")
    return value


def login(value: object) -> str:
    if not isinstance(value, str) or not LOGIN_RE.match(value):
        raise InvalidInput("invalid GitHub login")
    return value


def boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value in ("true", "True", "1"):
        return True
    if value in ("false", "False", "0", "", None):
        return False
    raise InvalidInput("invalid boolean")


def choice(value: object, allowed: tuple[str, ...], what: str) -> str:
    if value not in allowed:
        raise InvalidInput(f"invalid {what}")
    return value  # type: ignore[return-value]


def parse_repo_url(url: str) -> tuple[str, str]:
    """Split a validated https://github.com/<owner>/<name> URL."""
    match = REPO_URL_RE.match(url or "")
    if not match or url.endswith(".git"):
        raise InvalidInput("invalid repository URL")
    return match.group(1), match.group(2)


def normalize(obj: object) -> object:
    """Turn YAML dates and datetimes into ISO strings, recursively."""
    if isinstance(obj, dict):
        return {str(k): normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize(v) for v in obj]
    if isinstance(obj, _dt.datetime):
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=_dt.timezone.utc)
        return obj.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(obj, _dt.date):
        return obj.isoformat()
    return obj


def load_untrusted_yaml(data: bytes | str, max_bytes: int = MAX_ENTRY_BYTES) -> object:
    """Parse contributor YAML: size cap, no anchors or aliases, yaml.safe_load only."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    if len(raw) > max_bytes:
        raise YamlError(f"file is {len(raw)} bytes; the limit is {max_bytes}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise YamlError("file is not valid UTF-8") from exc
    try:
        for event in yaml.parse(text, Loader=yaml.SafeLoader):
            if isinstance(event, yaml.AliasEvent):
                raise YamlError("YAML aliases are not allowed")
            if getattr(event, "anchor", None):
                raise YamlError("YAML anchors are not allowed")
        return normalize(yaml.safe_load(text))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" (line {mark.line + 1})" if mark is not None else ""
        raise YamlError(f"YAML could not be parsed{where}") from exc


# --- escaping for untrusted text in comments and check summaries -------------------

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+!|~>])")


def neutralize_mentions(text: str) -> str:
    """Stop @mentions and team mentions from notifying anyone."""
    return text.replace("@", "@⁠")


def md_inline(value: object, limit: int = 300) -> str:
    """Escape untrusted text for inline Markdown (table cells, sentences)."""
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    text = html.escape(text, quote=False)
    text = _MD_SPECIAL.sub(r"\\\1", text)
    return neutralize_mentions(text)


def fence(value: object, lang: str = "text", limit: int = 20000) -> str:
    """Wrap untrusted multi-line text in a code fence it can't break out of."""
    text = "" if value is None else str(value)
    if len(text) > limit:
        text = text[:limit] + "\n[truncated]"
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{lang}\n{text}\n{ticks}"
