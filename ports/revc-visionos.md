# reVC for visionOS

**Grand Theft Auto: Vice City** · originally on PlayStation 2 (2002)
Port by [@LowRiderXR](https://github.com/LowRiderXR)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/LowRiderXR/revc-visionos-app && cd revc-visionos-app && git checkout c0ddb43a395beb14ffd195cfe9f98bb8aa5c874c && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/LowRiderXR/revc-visionos-app/blob/c0ddb43a395beb14ffd195cfe9f98bb8aa5c874c/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Developer-verified |
| Status | Developer-verified: Own code \(launcher, renderer\) is MIT; the reVC engine itself has no license and is published as-is. Requires the player's own classic PC copy of Vice City \(not the Definitive Edition\). Tested on Apple Vision Pro M2 and M5. |
| Plays as | 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-11-02 · 0 commits since |
| Source (scanned) | [LowRiderXR/revc-visionos-app at c0ddb43a395b](https://github.com/LowRiderXR/revc-visionos-app/tree/c0ddb43a395beb14ffd195cfe9f98bb8aa5c874c) |
| Install guide | [AVP-INSTALL.md at c0ddb43a395b](https://github.com/LowRiderXR/revc-visionos-app/blob/c0ddb43a395beb14ffd195cfe9f98bb8aa5c874c/AVP-INSTALL.md) |
| Repo | [LowRiderXR/revc-visionos-app](https://github.com/LowRiderXR/revc-visionos-app) |
| License | Custom license |
| Last commit | 2026-10-31 |
| visionOS | 27.0 or later |
| Input | game controller |
| Tags | gta, vice-city, vr, decompilation |

Native Vision Pro port of reVC, the reverse-engineered GTA Vice City engine: stereo rendering in a full immersive space, head tracking, foveated rendering, game-controller input, and a launcher for settings, save games and the game data. Bring your own classic PC copy.

## Credits

- re3 project: reVC, the reverse-engineered engine
- [librw](https://github.com/aap/librw): RenderWare reimplementation
- [ANGLE](https://chromium.googlesource.com/angle/angle): OpenGL ES to Metal
- [Klepton](https://github.com/shinyquagsire23/Klepton): Reference for Compositor Services and ANGLE
- [OpenAL Soft](https://github.com/kcat/openal-soft): Audio

## Upstream projects

- <https://github.com/LowRiderXR/revc-visionos>
- <https://github.com/LowRiderXR/librw-visionos>
- <https://github.com/LowRiderXR/visionos-angle-kit>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
