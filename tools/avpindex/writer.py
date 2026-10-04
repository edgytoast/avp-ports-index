"""The only path by which workflows write to main (spec §8.0 rule 7).

Each job applies its state change to a fresh copy of origin/main, regenerates every surface,
and makes one App commit ending in [skip ci] through the Git Data API, only if there is a
diff. If main moved meanwhile, the fast-forward is rejected: fetch, reset, re-apply,
regenerate and try again. After three failures, an owner issue is opened.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable

GENERATED_DIRS = ("ports", "feed", "skills/avp-index-submit/references", "skills/avp-index-submit/scripts")
# Workflows commit only these paths; anything else in the checkout (downloaded artifacts,
# scratch files) is never published.
COMMITTABLE = ("state/", "blocklist/", "entries/", "ports/", "feed/", "skills/avp-index-submit/references/",
               "skills/avp-index-submit/scripts/", "README.md", "llms.txt")
ATTEMPTS = 3


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=check, capture_output=True, text=True)
    return result.stdout


def git_bytes(root: Path, *args: str) -> bytes | None:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True)
    return result.stdout if result.returncode == 0 else None


def fetch_and_reset(root: Path) -> str:
    """Make the working tree exactly origin/main. The index repos are public, so the fetch
    needs no credentials (checkout runs with persist-credentials: false)."""
    git(root, "fetch", "--quiet", "origin", "main")
    git(root, "reset", "--quiet", "--hard", "origin/main")
    git(root, "clean", "-fdq", "--", *GENERATED_DIRS)
    return git(root, "rev-parse", "HEAD").strip()


def changed_files(root: Path) -> dict[str, tuple[bytes, str] | None]:
    """Changed committable paths -> (content, git file mode), or None for a deletion."""
    out = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    changes: dict[str, tuple[bytes, str] | None] = {}
    for record in [r for r in out.split("\0") if r]:
        path = record[3:]
        if not path.startswith(COMMITTABLE):
            continue
        file = root / path
        if file.is_file():
            changes[path] = (file.read_bytes(), "100755" if os.access(file, os.X_OK) else "100644")
        else:
            changes[path] = None
    return changes


def commit_main(rt, mutate: Callable[[], None], message: str) -> str | None:
    from .generate import generate

    if not message.endswith("[skip ci]"):
        message = f"{message} [skip ci]"
    for _attempt in range(ATTEMPTS):
        parent = fetch_and_reset(rt.root)
        rt.memo.pop("policy", None)
        mutate()
        generate(rt.root, rt.repo)
        changes = changed_files(rt.root)
        if not changes:
            rt.summary("No changes to commit.")
            return None
        if rt.dry_run:
            rt.summary("Dry run; would commit: " + ", ".join(sorted(changes)))
            git(rt.root, "reset", "--quiet", "--hard", "HEAD")
            return None
        sha = rt.gh.create_commit(parent, changes, message)
        if sha and rt.gh.fast_forward("main", sha):
            fetch_and_reset(rt.root)
            rt.summary(f"Committed {sha[:12]}: {message}")
            return sha
    rt.owner_issue("Writing to main failed",
                   f"A workflow couldn't push its change to main after {ATTEMPTS} attempts.\n\n"
                   f"Commit message: `{message}`\n\nRe-run the workflow once main is quiet.")
    raise RuntimeError("push to main failed after retries")
