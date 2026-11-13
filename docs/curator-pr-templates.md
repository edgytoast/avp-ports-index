# Curator PR templates

**Curator only.** These are the PR templates the index's curator (edgytoast) uses when listing someone else's port. They speak in the curator's voice, sign as the curator and rely on curator-only actions (the `owner:scan` label, clearing a prebuilt app). They live outside `skills/` on purpose, so the community submission skill never ships them. Contributors use `skills/avp-index-submit/references/pr-templates.md` instead.

Approved by the curator on 2026-11-13. Keep the wording as is unless the curator approves a change.

## External PR template

The PR opened in the port's own repo to add `AVP-INSTALL.md`.

- Branch `avp-ports-index` from the fork, targeting the branch the entry's `source_ref` points to. Commit: `Add AVP-INSTALL.md for the AVP Ports Index`
- Files: only `AVP-INSTALL.md` at the root (from `skills/avp-index-submit/assets/AVP-INSTALL.template.md`). No game data, binaries or license changes.
- Title: `Add AVP-INSTALL.md (AVP Ports Index)`
- Batch to one owner: one PR per repo plus one comment mentioning the owner that lists them.
- Body:

```
Hi! I run the [AVP Ports Index](https://github.com/edgytoast/avp-ports-index), a curated, link-only index of game ports running natively on the Apple Vision Pro.

This adds `AVP-INSTALL.md`, a short Vision Pro install guide that ${placeholder_one}. It's the only file the index needs from your repo, and it gives players a smooth, consistent onboarding experience across indexed games.

* Your draft listing: ${index_pr_link}. It goes live after this merges${placeholder_two}.
* The index hosts nothing and you stay in control. If a listed repo later fails a basic check (the install guide disappearing, say), a bot opens an issue here.
* Please edit anything that's off, or close this if you'd rather not be listed.

${placeholder_three}

${placeholder_four}

Thanks for building this!

Trevor (Trevorbilt)
```

- placeholder_one: either "points to ${file_name}, given that existing guide has the necessary rigor." or "is drafted with AI, from your README and build scripts, to walk users through the installation process."
- placeholder_two (optional): extra steps taken or pending, e.g. " because I've already approved the prebuilt app after confirming it has no game code." or " and I've had a chance to check the prebuilt app." Generally avoid blocking steps. Claude may decide on Toast's behalf whether a blocking item like a prebuilt app can be cleared.
- placeholder_three (omit if empty): "Notes from writing it:" bullets. Rule: each bullet names something the guide does that the README doesn't, and the file it came from. Grounding example (Half-Life, the merged PR):
  * `scripts/push-assets.sh` reads `DEVICE_NAME` and `BUILD_BUNDLE_ID` from `scripts/build-signing.conf`, which the README doesn't mention; the guide adds copying it from `build-signing.conf.example` first.
  * On a fresh checkout, `build_xash_libxash.sh` needs `VisionPort/setup.sh` to have fetched xash3d-fwgs first, and it uses `llvm-objcopy` (`brew install llvm`); the guide runs `setup.sh` first and lists LLVM.
- placeholder_four (omit if empty): external context, e.g. "Context: [my reply on your r/VisionPro post](link)."

## Index-side PR template

The entry PR into edgytoast/avp-ports-index.

- Order: open the index PR first (the external PR links to it), then the external PR, then edit the index PR body to add its link.
- Branch `entry/<id>`. Files: only `entries/<id>.yaml`. Title: `Add {Port name} ({Game title})`. Label: `owner:scan`.
- Skip the repo's PR checklist on curator PRs (its boxes are written for owners).
- Body:

```
Lists **{Port name}** by {owner_login} ({repo_url}).

Waiting for {external_pr_url} to add `AVP-INSTALL.md`. The index re-checks this PR on its own once that lands, and it merges after the safety check.${prebuilt_note}

Opened with `owner:scan` by the curator.

${context}
```

- prebuilt_note (matches placeholder_two in the external PR): cleared = " The curator pre-reviewed the repo's prebuilt files and archives."; still blocking = " The curator checks the prebuilt app before the safety check runs."; no prebuilt app = omit.
- context (optional): same Reddit link as the external PR.
- If the owner opens the external PR themselves: "Waiting for the `AVP-INSTALL.md` in {repo_url}", rest unchanged.
- Wording: always "safety check", never "security review".
