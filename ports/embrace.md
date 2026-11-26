# Embrace

**Vampire: The Masquerade, Bloodlines** · originally on PC (2004)
Port by A. Cervantez ([@Ywach404](https://github.com/Ywach404))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/Ywach404/embrace && cd embrace && git checkout cc28207f2122ccc0547b171b2b5c87d84b141f1d && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/Ywach404/embrace/blob/cc28207f2122ccc0547b171b2b5c87d84b141f1d/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Developer-verified |
| Status | Developer-verified: Plays in full-view 6DoF stereo with a Metal renderer, head look, hand-aimed weapons and tracked PS VR2 Sense controllers. |
| Plays as | 2D, 3D immersive, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-11-26 · 0 commits since |
| Source (scanned) | [Ywach404/embrace at cc28207f2122](https://github.com/Ywach404/embrace/tree/cc28207f2122ccc0547b171b2b5c87d84b141f1d) |
| Install guide | [AVP-INSTALL.md at cc28207f2122](https://github.com/Ywach404/embrace/blob/cc28207f2122ccc0547b171b2b5c87d84b141f1d/AVP-INSTALL.md) |
| Repo | [Ywach404/embrace](https://github.com/Ywach404/embrace) |
| License | MIT |
| Last commit | 2026-11-25 |
| visionOS | 27.0 or later |
| Input | game controller |
| Tags | rpg, first-person, metal |

A native visionOS port of Vampire: The Masquerade, Bloodlines by A. Cervantez, in full-view stereo with your head as the camera and weapons aimed by hand.

## Screenshots

From the port's repo at ac513afb89c4.

<img src="https://raw.githubusercontent.com/Ywach404/embrace/ac513afb89c4e922ef2ab08de55e20397c22ba4b/docs/media/embrace-downtown.gif" alt="Screenshot of Embrace" width="400">
<img src="https://raw.githubusercontent.com/Ywach404/embrace/ac513afb89c4e922ef2ab08de55e20397c22ba4b/docs/media/hand-aimed-rifle.jpg" alt="Screenshot of Embrace" width="400">
<img src="https://raw.githubusercontent.com/Ywach404/embrace/ac513afb89c4e922ef2ab08de55e20397c22ba4b/docs/media/third-person-street.jpg" alt="Screenshot of Embrace" width="400">

## Credits

- [Bloodlines Porter](https://github.com/OlehPetrykUA/bloodlines-porter): Native runtime and recompiler toolchain \(MIT\)
- [DXVK \(jm2 fork\)](https://github.com/jm2/dxvk): D3D9 shader front end \(Zlib\)
- [dxbc-spirv](https://github.com/doitsujin/dxbc-spirv): Shader bytecode to SPIR-V \(MIT\)
- [SPIRV-Cross](https://github.com/KhronosGroup/SPIRV-Cross): SPIR-V to Metal Shading Language \(Apache-2.0\)
- [SDL](https://github.com/libsdl-org/SDL): Platform layer \(Zlib\)
- [FFmpeg](https://github.com/FFmpeg/FFmpeg): Bink movie playback \(LGPL-2.1-or-later\)

## Upstream projects

- <https://github.com/OlehPetrykUA/bloodlines-porter>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
