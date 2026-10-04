"""PR classification (spec §8.1): by changed paths first, then author."""

from __future__ import annotations

import re
from dataclasses import dataclass

ENTRY_ADD, ENTRY_EDIT, ENTRY_REMOVE = "entry-add", "entry-edit", "entry-remove"
OWNER_VERIFY, OWNER_ADMIN, INVALID, SKIP = "owner-verify", "owner-admin", "invalid", "skip"
ENTRY_CLASSES = (ENTRY_ADD, ENTRY_EDIT, ENTRY_REMOVE)
ENTRY_FILE = re.compile(r"^entries/([^/]+)\.yaml$")
VERIFY_FILE = "verification/owner-verified.yaml"
DEPENDABOT = "dependabot[bot]"


@dataclass(frozen=True)
class Classification:
    kind: str
    path: str | None = None      # the entry file, for entry classes
    stem: str | None = None      # its file-name stem (validated later by S1-03)

    @property
    def change(self) -> str | None:
        return {ENTRY_ADD: "add", ENTRY_EDIT: "edit", ENTRY_REMOVE: "remove"}.get(self.kind)


def classify(files: list[dict], author_id: int | None, author_login: str | None,
             owner_id: int) -> Classification:
    """files are GitHub's PR file records: {filename, status, previous_filename?}."""
    if author_login == DEPENDABOT:
        return Classification(SKIP)
    touches_entries = any(
        f["filename"].startswith("entries/") or str(f.get("previous_filename") or "").startswith("entries/")
        for f in files)
    renames_entry = any(f.get("status") in ("renamed", "copied") and touches for f in files
                        for touches in [f["filename"].startswith("entries/")
                                        or str(f.get("previous_filename") or "").startswith("entries/")])
    if renames_entry:
        return Classification(INVALID)
    if len(files) == 1:
        only = files[0]
        match = ENTRY_FILE.match(only["filename"])
        kinds = {"added": ENTRY_ADD, "modified": ENTRY_EDIT, "removed": ENTRY_REMOVE}
        if match and only.get("status") in kinds:
            return Classification(kinds[only["status"]], only["filename"], match.group(1))
        if only["filename"] == VERIFY_FILE and only.get("status") == "modified" and author_id == owner_id:
            return Classification(OWNER_VERIFY, VERIFY_FILE)
    if author_id == owner_id and not touches_entries:
        return Classification(OWNER_ADMIN)
    return Classification(INVALID)
