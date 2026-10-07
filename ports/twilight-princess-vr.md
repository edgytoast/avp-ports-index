# Twilight Princess VR

**The Legend of Zelda: Twilight Princess** · originally on GameCube (2006)
Port by Trevorbilt ([@edgytoast](https://github.com/edgytoast))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/tpvr-visionos && cd tpvr-visionos && git checkout a4fbe68d0a8446e6678bb328e273cb1e3d6b72e9 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/tpvr-visionos/blob/a4fbe68d0a8446e6678bb328e273cb1e3d6b72e9/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working · Curator's own port |
| Status | Working: Plays on Apple Vision Pro \(visionOS 27\) in full and progressive immersion, with PS VR2 Sense controllers or bare hands. Window mode \(third person, gamepad\) is newer: characters look a little flatter than in the game. |
| Plays as | 3D shared space, 6DoF immersive, 6DoF progressive |
| Health | OK |
| Scan | Scanned 2026-10-07 · 0 commits since |
| Source (scanned) | [edgytoast/tpvr-visionos at a4fbe68d0a84](https://github.com/edgytoast/tpvr-visionos/tree/a4fbe68d0a8446e6678bb328e273cb1e3d6b72e9) |
| Install guide | [AVP-INSTALL.md at a4fbe68d0a84](https://github.com/edgytoast/tpvr-visionos/blob/a4fbe68d0a8446e6678bb328e273cb1e3d6b72e9/AVP-INSTALL.md) |
| Repo | [edgytoast/tpvr-visionos](https://github.com/edgytoast/tpvr-visionos) |
| Developer site | <https://trevorbilt.com> |
| License | CC0-1.0 |
| Last commit | 2026-10-07 |
| visionOS | 26.0 or later |
| Input | game controller, hand tracking |
| Tags | zelda, twilight-princess, vr, first-person, gamecube, wii, decompilation, hand-tracking |

Twilight Princess in first person on Apple Vision Pro: JoeyAW's TPVR mod on Dusklight, built natively for visionOS. Full or progressive immersion with PS VR2 Sense controllers or bare hands, or the GameCube game in a window beside your apps, with real depth. Bring your own disc.

## Credits

- [JoeyAW](https://github.com/JoeyAW/TPVR): TPVR, the VR mod this port is built on
- [Twilit Realm](https://twilitrealm.dev/): Dusklight, the Twilight Princess PC port
- [zeldaret](https://github.com/zeldaret/tp): Twilight Princess decompilation
- [encounter](https://github.com/encounter/aurora): Aurora, the GameCube and Wii graphics layer
- [iChris4](https://github.com/iChris4/Wiicompiled_VR): WiiCompiled Vision, source of the visionOS OpenXR provider

## Upstream projects

- <https://github.com/JoeyAW/TPVR>
- <https://github.com/TwilitRealm/dusklight>
- <https://github.com/zeldaret/tp>

---

This index only links to the developer's own repository. Automated checks and an AI security review can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
