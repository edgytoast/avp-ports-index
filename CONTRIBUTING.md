# Getting your port listed

Thanks for thinking of listing your port here. This index is for people who have brought a classic game to Apple Vision Pro as a native visionOS app, usually on top of a decompilation or source-port project. The index only links to your repository. It never hosts your code, your builds or anyone's game files, and players always bring their own copy of the game.

## The checklist

These mirror the automated checks (the [full list of checks](skills/avp-index-submit/references/checks.md) explains each one).

- **One PR, one file.** Your PR adds or changes exactly one file, `entries/<id>.yaml`, and nothing else.
- **An install guide in your repo.** Put `AVP-INSTALL.md` at the root of your repo (exact name, not empty, under 256 KB). Tell players how to supply their own game files, how to build, and how to install on Apple Vision Pro. There's no required format; the [skill's template](skills/avp-index-submit/assets/AVP-INSTALL.template.md) is a starting point. Players start from a checkout of the exact commit that was scanned, so keep your build steps usable from an existing checkout.
- **Your own public repo.** The repo is public and you own it, or it belongs to an org you're a public member of. Anyone else's submission goes to the curator first, which is fine, just slower.
- **A license, if you have one.** No license, or a custom one, is fine. It's shown as stated. If a custom license seems to forbid personal use, the curator takes a look first.
- **No game data.** No disc images, game data, archives or Git LFS files in the repo or its releases.
- **Prebuilt apps are fine as long as players still supply their own game files.** If your releases include a Vision Pro app (an `.ipa`, say), set `install: [build, sideload]` so your port page says so; the curator looks at the app first and approves it only then. The security review covers your source code, not the app. An app that lets people play without supplying their own game files can't be listed.
- **These rules cover what's on GitHub: your repo and its releases.** The index doesn't vet anything hosted elsewhere, such as files your app downloads from your own server.
- **Agent files are welcome.** `CLAUDE.md`, `AGENTS.md`, skills and similar files are fine. They're reviewed like any other code.

## The fields

[entry-fields.md](skills/avp-index-submit/references/entry-fields.md) lists every allowed field. It's generated from the schema, so it's always current. Seven fields are required: `id`, `name`, `game.title`, `repo`, `developer.github`, `status` and `experiences`. Please credit the upstream decompilation and VR-port projects you built on in `credits`. If your port lives on a branch other than your repo's default branch, set the optional `source_ref` to that branch, and the index scans and follows it instead.

`experiences` lists every way your port plays:

- **2D:** a flat picture in a window beside your other apps.
- **3D immersive:** a stereo 3D screen in front of you, with your other apps put away, seen from the game's camera.
- **3D shared space:** the game's 3D world with real depth, in a window beside your other apps. Lean and you see around things.
- **6DoF immersive:** inside the game at life scale, with your head as the camera.
- **6DoF progressive:** the same, through a portal the Digital Crown widens and narrows.

If you also publish a prebuilt app, add `install: [build, sideload]`, or `install: [sideload]` if the app is the only way to install it. Every listed port must still build from source, contain a sideload-able asset, or otherwise enable players to actually play the game in line with this repo's bring-your-own-game policy.

## What happens after you open the PR

1. The Stage 1 checks run right away. They're free and take a minute or two.
2. If everything passes, your PR joins the queue for the automated security review, first come, first served. Expect minutes to hours.
3. Clean PRs merge on their own, and your port appears in the README, on its own page, in the JSON feed and in `llms.txt`.

The checks rerun whenever you push to the PR branch. If you fix something in your port's repo instead (adding `AVP-INSTALL.md`, say), the index re-checks within a few hours of a new commit there, and at least daily otherwise; close and reopen the PR to rerun them right away.

## A badge for your README

Once your port is listed, you're welcome to add this badge to your README. It links to your port's page; replace `<id>` with your entry's id.

```markdown
[![Listed in the AVP Ports Index](https://img.shields.io/badge/AVP_Ports_Index-listed-0A84FF)](https://github.com/edgytoast/avp-ports-index/blob/main/ports/<id>.md)
```

## "fail" or "route"

- A **fail** means something needs fixing. The bot's comment says what and how.
- A **route** means a person needs to look, for example because the PR doesn't come from the repo's owner, or the repo has archives in it. There's nothing for you to do; the curator will take a look.

Only the curator applies `owner:scan`, which sends a routed PR on to the security review.

## Labels

| Label | Meaning |
| --- | --- |
| `stage1:pass`, `stage1:fail`, `stage1:route` | How the Stage 1 checks came out |
| `stage2:queued` | Waiting for the automated security review |
| `stage2:scanning` | The review is running |
| `stage2:pass` | The review passed |
| `stage2:flagged` | The review asked for a person to take a closer look; nothing has been decided |
| `needs-author` | Something for you to fix |
| `needs-owner` | Waiting for the curator |
| `owner:scan`, `blocklist` | Applied by the curator only |

## Updating your entry

Edit your file in a new PR. The index tracks only the current state; your own git history holds the versions. Edits are scanned again only when your repo has changed since the last scan.

## Pinned links

Players are pointed at your last scanned commit: the install guide link, the source link and the clone command all use it. The pin moves forward automatically when newer commits on your default branch (or your `source_ref` branch) pass the security review, so you don't need to do anything when you push.

## Health checks

A daily check reruns the basic checks on every listed port.

1. If something breaks, your port gets a "⚠ May have issues" badge and stays listed.
2. If it's still broken the next day, a friendly issue opens on your repo saying what to fix and by when (30 days out).
3. If it's still broken after that, the listing comes off the index. Its name, credits and dates stay on the "Unavailable ports" record.
4. Fix things and open a PR updating your entry (any small change, such as `status_notes`, is enough), and it comes back.

Being listed means your repo may receive these maintenance issues from `trevorbilt-bot`.

## Removing your entry

Delete your file in a PR. The repo's owner, or whoever first submitted the entry, can do this, and it merges on its own.

## Curator's own ports

Ports built by the curator are tagged "Curator's own port", so readers always know who made them.

## Appeals

If you think a decision on your PR was wrong, [open an appeal](../../issues/new?template=appeal.yml) and the curator will take another look.

## The agent skill

[skills/avp-index-submit](skills/avp-index-submit/SKILL.md) is a skill for coding agents. Give it to your agent and it will add `AVP-INSTALL.md` to your repo if it's missing, write your entry file, run the same checks locally with `scripts/preflight.py`, and open the PR.
