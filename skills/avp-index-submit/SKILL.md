---
name: avp-index-submit
description: Prepares a visionOS (Apple Vision Pro) game-port repository for listing in the AVP Ports Index curated by trevorbilt, and opens the submission pull request. Use when the user wants their Vision Pro port listed, asks to submit to the AVP ports index, or needs an AVP-INSTALL.md.
license: MIT
---

# Submit a port to the AVP Ports Index

You are preparing the user's port repo so it passes the index's automated checks on the first try. `scripts/preflight.py` runs the index's Stage 1 checks, except those that need the index's own data (S1-04, S1-05, S1-15, S1-16, S1-17, S1-18) (needs Python 3.11+, `pip install pyyaml jsonschema requests`; set GITHUB_TOKEN to avoid rate limits).

## Steps
1. Confirm the port repo is on GitHub and public, and that the user can push to it. Never add game data, disc images, archives or prebuilt binaries.
2. If `AVP-INSTALL.md` is missing at the repo root, create it from `assets/AVP-INSTALL.template.md` (suggested sections: Requirements, Game Files, Build, Install on Apple Vision Pro). Write Build so it starts from an existing checkout, since players clone the scanned commit from the port's index page. Fill it from the repo's README and build files; ask the user for anything unknown.
3. Leave licensing alone. A missing or custom license is accepted and shown as-is; never add or change a license on the user's behalf.
4. With the user's approval, commit and push those changes to the branch the port lives on.
5. Build `entries/<id>.yaml` from `assets/entry.template.yaml` using `references/entry-fields.md`. Fill the six required fields, and the optional ones the user can answer quickly. `developer.github` is whoever built the port, usually the user. Ask the user for their honest `status`, explaining the four values. Credit upstream decompilation and VR-port projects in `credits`. If the port lives on a branch other than the repo's default branch, set `source_ref` to that branch.
6. Run `python scripts/preflight.py entries/<id>.yaml` and fix everything it reports.
7. Fork edgytoast/avp-ports-index (or push a branch, if the user has write access to it), add only that one file, and open a PR to `main` using the template checklist. Open it from the account that owns the port repo (or a public member of its org), or it will wait for the curator.
8. Tell the user: clean PRs merge on their own after a queued security review that can take hours; labels show progress; the curator's verification is separate and can't be requested in the PR. Once the port is listed, they can add the README badge from CONTRIBUTING.md.

## Never
- Edit any file outside `entries/` in the index.
- Add verification, health, scan or date fields.
- Link to downloads of game files.
