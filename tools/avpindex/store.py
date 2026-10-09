"""The index's own files: policy, brand, entries, state/, blocklist/ and verification/.

These are trusted files on main (written by the App or the owner), except entries/,
which contributors control and which is always parsed with the untrusted loader.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import validate

ROOT = Path(os.environ.get("AVP_ROOT") or Path(__file__).resolve().parents[2])

HEALTH = "state/health.yaml"
LIFECYCLE = "state/lifecycle.yaml"
SYNC = "state/sync.yaml"
FLAGS = "state/flags.yaml"
MEDIA = "state/media.yaml"
APPROVALS = "state/approvals.yaml"
BLOCKLIST = "blocklist/blocklist.yaml"
VERIFIED = "verification/owner-verified.yaml"
POLICY = "config/policy.yaml"
BRAND = "brand/brand.yaml"


# --- time ---------------------------------------------------------------------------

def utcnow() -> dt.datetime:
    """Now, in UTC. AVP_NOW (ISO 8601) overrides it in tests."""
    forced = os.environ.get("AVP_NOW")
    if forced:
        return parse_iso(forced)
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(when: dt.datetime) -> str:
    return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def today(now: dt.datetime | None = None) -> str:
    return (now or utcnow()).date().isoformat()


# --- YAML ---------------------------------------------------------------------------

class _Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):  # never emit anchors or aliases
        return True


def dump_yaml(data: object) -> str:
    return yaml.dump(data, Dumper=_Dumper, sort_keys=True, default_flow_style=False,
                     allow_unicode=True, width=1000)


def read_yaml(path: Path, default: object) -> object:
    if not path.exists():
        return copy.deepcopy(default)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return validate.normalize(data if data is not None else copy.deepcopy(default))


def write_text_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def load_json(rel: str, root: Path | None = None) -> dict:
    return json.loads(((root or ROOT) / rel).read_text(encoding="utf-8"))


# --- config -------------------------------------------------------------------------

def load_policy(root: Path | None = None) -> dict:
    policy = read_yaml((root or ROOT) / POLICY, {})
    timeout = policy["stage2"]["jules_timeout_minutes"]
    if not isinstance(timeout, int) or not 1 <= timeout <= 180:
        raise ValueError("stage2.jules_timeout_minutes must be between 1 and 180")
    floor = policy["stage2"]["approved_files_min_confidence"]
    if not isinstance(floor, int) or not 0 <= floor <= 100:
        raise ValueError("stage2.approved_files_min_confidence must be between 0 and 100")
    return policy


def load_brand(root: Path | None = None) -> dict:
    return read_yaml((root or ROOT) / BRAND, {})


def site_urls(policy: dict, repo_full_name: str) -> tuple[str, str]:
    base = policy.get("site", {}).get("base_url", "auto")
    raw = policy.get("site", {}).get("raw_base_url", "auto")
    if base == "auto":
        base = f"https://github.com/{repo_full_name}/blob/main"
    if raw == "auto":
        raw = f"https://raw.githubusercontent.com/{repo_full_name}/main"
    return base.rstrip("/"), raw.rstrip("/")


# --- entries ------------------------------------------------------------------------

def entry_path(entry_id: str, root: Path | None = None) -> Path:
    return (root or ROOT) / "entries" / f"{validate.entry_id(entry_id)}.yaml"


def load_entries(root: Path | None = None) -> tuple[dict[str, dict], dict[str, str]]:
    """Parse every entries/*.yaml on disk. Returns (entries by id, errors by file stem)."""
    entries: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for path in sorted(((root or ROOT) / "entries").glob("*.yaml")):
        stem = path.stem
        try:
            data = validate.load_untrusted_yaml(path.read_bytes())
        except validate.YamlError as exc:
            errors[stem] = str(exc)
            continue
        if not isinstance(data, dict):
            errors[stem] = "not a mapping"
            continue
        entries[stem] = data
    return entries, errors


# --- state --------------------------------------------------------------------------

EMPTY_LIST_FILE = {"schema_version": 1, "entries": []}


@dataclass
class State:
    """All bot-written state plus the owner's verification records."""

    root: Path
    health: dict = field(default_factory=dict)
    lifecycle: dict = field(default_factory=dict)
    sync: dict = field(default_factory=lambda: {"last_synced_sha": None})
    flags: dict = field(default_factory=lambda: copy.deepcopy(EMPTY_LIST_FILE))
    blocklist: dict = field(default_factory=lambda: copy.deepcopy(EMPTY_LIST_FILE))
    verified: dict = field(default_factory=lambda: {"schema_version": 1, "records": {}})
    media: dict = field(default_factory=dict)
    approvals: dict = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path | None = None) -> "State":
        root = root or ROOT
        return cls(
            root=root,
            health=read_yaml(root / HEALTH, {}),
            lifecycle=read_yaml(root / LIFECYCLE, {}),
            sync=read_yaml(root / SYNC, {"last_synced_sha": None}),
            flags=read_yaml(root / FLAGS, EMPTY_LIST_FILE),
            blocklist=read_yaml(root / BLOCKLIST, EMPTY_LIST_FILE),
            verified=read_yaml(root / VERIFIED, {"schema_version": 1, "records": {}}),
            media=read_yaml(root / MEDIA, {}),
            approvals=read_yaml(root / APPROVALS, {}),
        )

    def save(self) -> None:
        """Write the bot-owned files. verification/ is owner-only and never written."""
        write_text_if_changed(self.root / HEALTH, dump_yaml(self.health) if self.health else "{}\n")
        write_text_if_changed(self.root / LIFECYCLE, dump_yaml(self.lifecycle) if self.lifecycle else "{}\n")
        write_text_if_changed(self.root / SYNC, dump_yaml(self.sync))
        write_text_if_changed(self.root / FLAGS, dump_yaml(self.flags))
        write_text_if_changed(self.root / BLOCKLIST, dump_yaml(self.blocklist))
        write_text_if_changed(self.root / MEDIA, dump_yaml(self.media) if self.media else "{}\n")
        write_text_if_changed(self.root / APPROVALS, dump_yaml(self.approvals) if self.approvals else "{}\n")

    def health_record(self, entry_id: str) -> dict:
        return self.health.setdefault(entry_id, default_health())

    def status(self, entry_id: str) -> str | None:
        record = self.lifecycle.get(entry_id)
        return record.get("status") if record else None


def default_health() -> dict:
    return {
        "last_commit_date": None,
        "last_checked": None,
        "health": "ok",
        "failing_since": None,
        "consecutive_failures": 0,
        "failures": [],
        "routes": [],
        "outreach_issue_url": None,
        "outreach_opened_at": None,
        "archived": False,
        "github_verified": False,
        "curator_own": False,
        "license": {"spdx": None, "kind": "none"},
        "scanned_commit": None,
        "scanned_at": None,
        "scan_kind": None,
        "scan_confidence": None,
        "commits_since_scan": None,
        "scan_state": "unknown",
        "flagged_commit": None,
        "flagged_files": [],
        "rescan_hold": False,
        "rescan_after": None,
        "decay_reset_at": None,
        "warnings": [],
    }
