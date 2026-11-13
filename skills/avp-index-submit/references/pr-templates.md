# PR templates for submitters

Use these when opening the PRs in step 7, or the install-guide PR for someone else's repo. Write every PR in the user's own voice and sign it with the user's own name. The user is either the port's **owner** (they own the repo or are a public member of its org) or a **contributor** (anyone else). Neither is the index's curator, so never say or imply the user runs the index, never sign as the curator, and never claim an action only the curator can take: applying `owner:scan` or any routing label, approving a prebuilt app, or waiving a check.

Wording: always "safety check", never "security review".

## Which PRs to open

- **Owner:** commit `AVP-INSTALL.md` to the port's branch yourself (step 4), then open the index PR. There is no install-guide PR.
- **Contributor:** you can't push to the port's repo, so open the index PR first (the install-guide PR links to it), then the install-guide PR in the owner's repo, then edit the index PR body to add its link. The index PR waits for the curator, because only the repo's owner (or a public member of its org) passes the authority check on their own.
- If one owner has several ports to list, open one install-guide PR per repo plus one comment mentioning the owner that lists them.

## Install-guide PR (contributors only)

The PR opened in the port's own repo to add `AVP-INSTALL.md`.

- Branch `avp-ports-index` from your fork, targeting the branch the entry's `source_ref` points to (the repo's default branch if it has none). Commit: `Add AVP-INSTALL.md for the AVP Ports Index`
- Files: only `AVP-INSTALL.md` at the root (from `assets/AVP-INSTALL.template.md`). No game data, binaries or license changes.
- Title: `Add AVP-INSTALL.md (AVP Ports Index)`
- Body:

```
Hi! I'd like to get your port listed in the [AVP Ports Index](https://github.com/edgytoast/avp-ports-index), a curated, link-only index of game ports running natively on the Apple Vision Pro. I'm not the index's curator, just ${who_i_am}.

This adds `AVP-INSTALL.md`, a short Vision Pro install guide that ${guide_source}. It's the only file the index needs from your repo, and it gives players a smooth, consistent onboarding experience across indexed games.

* Draft listing: ${index_pr_link}. Since I'm not the repo's owner, the index's curator reviews it, and it can go live after this merges.${prebuilt_note}
* The index hosts nothing and you stay in control. If a listed repo later fails a basic check (the install guide disappearing, say), a bot opens an issue here.
* Please edit anything that's off, or close this if you'd rather not be listed. You can also take over the listing by opening your own PR to the index.

${notes}

${context}

Thanks for building this!

${your_name}
```

- who_i_am: one true phrase about the user, e.g. "a player who got it running on my Vision Pro" or "a contributor to this port". Ask the user if unsure.
- guide_source: either "points to ${file_name}, given that existing guide has the necessary rigor." or "is drafted with AI, from your README and build scripts, to walk users through the installation process."
- prebuilt_note (only if the repo's releases include a Vision Pro app): " The curator looks at the prebuilt app before it's listed." Never say it's been approved or cleared.
- notes (omit if empty): "Notes from writing it:" bullets. Rule: each bullet names something the guide does that the README doesn't, and the file it came from. Grounding example (from a merged install-guide PR for a Half-Life port):
  * `scripts/push-assets.sh` reads `DEVICE_NAME` and `BUILD_BUNDLE_ID` from `scripts/build-signing.conf`, which the README doesn't mention; the guide adds copying it from `build-signing.conf.example` first.
  * On a fresh checkout, `build_xash_libxash.sh` needs `VisionPort/setup.sh` to have fetched xash3d-fwgs first, and it uses `llvm-objcopy` (`brew install llvm`); the guide runs `setup.sh` first and lists LLVM.
- context (omit if empty): where the port came up, e.g. "Context: [the r/VisionPro post](link)."
- your_name: the user's own name or handle.

## Index PR

The entry PR into edgytoast/avp-ports-index.

- Branch `entry/<id>` on your fork. Files: only `entries/<id>.yaml`. Title: `Add {Port name} ({Game title})`. Don't add labels; the bot and the curator manage them.
- Start the body with the repo's PR template checklist (`.github/PULL_REQUEST_TEMPLATE.md`) and tick only the boxes that are true. A contributor leaves "I own it" unticked.
- Then add, for an **owner**:

```
Lists **{Port name}** ({repo_url}), my port.${prebuilt_note}
```

- Or, for a **contributor**:

```
Lists **{Port name}** by {owner_login} ({repo_url}). I'm not the repo's owner, so this waits for the curator.

Waiting for {install_guide_pr_url} to add `AVP-INSTALL.md`. The index re-checks this PR on its own once that lands.${prebuilt_note}

${context}
```

- prebuilt_note (only if the release includes a Vision Pro app and the entry sets `install: [build, sideload]`): " The repo's releases include a prebuilt Vision Pro app, which the curator looks at first."
- If the owner adds `AVP-INSTALL.md` themselves, write "Waiting for the `AVP-INSTALL.md` in {repo_url}" instead.
- context (optional): same link as the install-guide PR.
