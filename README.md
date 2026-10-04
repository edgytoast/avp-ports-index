<!-- trevorbilt:brand:start -->
<img src="https://trevorbilt.com/assets/logo-BdrEikAq.png" alt="Trevorbilt" width="200">

# AVP Ports Index, curated by trevorbilt

Curated by Trevor "Toast" ([@edgytoast](https://github.com/edgytoast)) · [trevorbilt.com](https://trevorbilt.com)
<!-- trevorbilt:brand:end -->

A list of games people have lovingly coaxed onto Apple Vision Pro. Every port here was built by someone in the community, standing on years of reverse-engineering and porting work by other someones, and this index exists so that work doesn't quietly disappear into an old Discord channel. It hosts nothing but links, credits and install guides, so you'll bring your own copy of the game (and a little patience with Xcode).

> **Read before installing.** Most entries here are *not* human-reviewed. Each listing either passed automated checks or was reviewed by the curator, and is labeled accordingly. The automated checks confirm that the linked source repo exists and is public, has an install guide (`AVP-INSTALL.md`), its links resolve, and no disc images or other known game-data file types were found; anything that looked like archives or prebuilt downloads went to the curator. Each entry shows its license as stated; some ports have a custom license or none. An AI agent (Google's Jules) reviewed the specific commit linked as **Source (scanned)** for signs of malicious code, paying closest attention to its build scripts; build that commit to get what was reviewed, and check the "commits since scan" count. Building a port runs its build scripts on your Mac with your permissions. Automation **cannot** confirm a port runs on Apple Vision Pro, does not vet third-party code downloaded during the build, may not read every file, and can miss malicious code. Sideloading is at your own discretion. Some developers also publish prebuilt apps; the security review covers the source code, never the apps. This index hosts no games, ports, emulators or binaries. You must own the game and supply your own legally obtained game files, then build from the linked repo.

## How to install a port

1. Own the original game and prepare your own files as the port describes.
2. Have a Mac with the Xcode version the port lists.
3. Get the exact code that was scanned with the clone command on the port's page (it checks out the scanned commit, with submodules). Then follow the port's install guide (pinned link) from its build steps onward. Skip only the guide's step that clones or downloads this port's own repo, since that would fetch the latest code, which may not have been scanned. Keep every other step, including ones that download dependencies.
4. Build to your Vision Pro with your Apple ID. With a free developer account, sideloaded apps need re-signing periodically.
5. For extra caution, build from a separate macOS user account, since build scripts run with your permissions.

## What the labels mean

**Trust**, from highest to lowest:

- **✔ Verified by trevorbilt:** the curator ran the port on Apple Vision Pro. "Repo updated since" means the port has newer scanned code than the commit the curator tested.
- **Developer-verified:** the port's developer ran the current build on Apple Vision Pro, end to end.
- **Working:** the contributor reports it runs and is playable.
- **Partially working:** playable with notable bugs or missing features.
- **Not working:** does not currently run; listed for preservation.

Everything below "Verified by trevorbilt" is self-reported by whoever submitted the port.

**Plays as:** how the port plays on Vision Pro. A port can have several:

- **2D:** a flat picture in a window beside your other apps.
- **3D immersive:** a stereo 3D screen in front of you, with your other apps put away, seen from the game's camera.
- **3D shared space:** the game's 3D world with real depth, in a window beside your other apps. Lean and you see around things.
- **6DoF immersive:** inside the game at life scale, with your head as the camera.
- **6DoF progressive:** the same, through a portal the Digital Crown widens and narrows.

**Curator's own port:** built by the curator, so you know who made it.

**Health:** "OK", or "⚠ May have issues" when the daily check found a problem. The port stays listed while its developer has time to fix it.

**Scan:** "Scanned <date> · N commits since" means the automated security review covered the commit the links point to, and the repo has N newer commits that haven't been reviewed. "Reviewed by the curator" means the curator looked at that commit instead.

## Ports

| Game | Port | Developer | Plays as | Trust | Health | License | Last commit | Scan | Install guide |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Simpsons: Hit &amp; Run | [SHAR VR](ports/shar-visionos.md) | Trevorbilt ([@edgytoast](https://github.com/edgytoast)) |  | Working · Curator's own port | OK | MIT | 2026-10-04 | Scanned 2026-10-04 · 0 commits since | [AVP-INSTALL.md](https://github.com/edgytoast/shar-visionos/blob/f982d0a8f3d0a35550846b9a552dcdd2bca40e98/AVP-INSTALL.md) |
| The Legend of Zelda: Twilight Princess | [Twilight Princess VR](ports/twilight-princess-vr.md) | trevorbilt ([@edgytoast](https://github.com/edgytoast)) |  | Working · Curator's own port | OK | CC0-1.0 | 2026-10-04 | Scanned 2026-10-04 · 0 commits since | [AVP-INSTALL.md](https://github.com/edgytoast/tpvr-visionos/blob/69873b7cecd5bb99ae05d64f7592fb9ac1937b80/AVP-INSTALL.md) |

## Developers: get your port listed

Read [CONTRIBUTING.md](CONTRIBUTING.md), or give your coding agent the [avp-index-submit skill](skills/avp-index-submit/SKILL.md). Clean submissions merge on their own after a queued security review.

## Data

- [JSON feed](feed/v1/index.json) ([schema](schema/feed-v1.schema.json), [versioning policy](docs/feed.md))
- [llms.txt](https://raw.githubusercontent.com/edgytoast/avp-ports-index/main/llms.txt)

Entries and feed data are [CC0-1.0](LICENSE-DATA); the tooling is [MIT](LICENSE).

## Reports and takedowns

Found something broken or malicious? [Open a report issue](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Rights holders: see [SECURITY.md](SECURITY.md#takedown) or email admin@trevorbilt.com.

## More from Trevorbilt

Apps for Apple Vision Pro from the curator of this index.

| | |
| --- | --- |
| <a href="https://trevorbilt.com/loose-papers"><img src="https://trevorbilt.com/assets/loose-papers-icon-DJ006cPT.png" alt="Loose Papers icon" width="64"></a> | **[Loose Papers](https://trevorbilt.com/loose-papers)**<br>A reader for your own books and comics \(PDF, EPUB, CBR and CBZ\), with page turns that follow your hand. |
| <a href="https://trevorbilt.com/papas-ball-and-tee"><img src="https://trevorbilt.com/assets/papas-icon-DUIo8ARw.png" alt="Papa's Ball &amp; Tee icon" width="64"></a> | **[Papa's Ball &amp; Tee](https://trevorbilt.com/papas-ball-and-tee)**<br>A small balancing game that rests in your space, for a quick challenge you never quite master. |

---

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
