# Lambda VisionPro

**Half-Life** · originally on PC (1998)
Port by Ixion ([@illixion](https://github.com/illixion))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/illixion/halflife-visionos && cd halflife-visionos && git checkout b22c5744c706c4bc4a9331706726fe2760063578 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/illixion/halflife-visionos/blob/b22c5744c706c4bc4a9331706726fe2760063578/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: Playable end to end on Apple Vision Pro, per the README. The hand-tracked VR input is described there as proof-of-concept quality: functional, with rough edges. |
| Plays as | 6DoF immersive |
| Health | OK |
| Scan | Reviewed by the curator 2026-10-09 · 1 commit since |
| Source (scanned) | [illixion/halflife-visionos at b22c5744c706](https://github.com/illixion/halflife-visionos/tree/b22c5744c706c4bc4a9331706726fe2760063578) |
| Install guide | [AVP-INSTALL.md at b22c5744c706](https://github.com/illixion/halflife-visionos/blob/b22c5744c706c4bc4a9331706726fe2760063578/AVP-INSTALL.md) |
| Repo | [illixion/halflife-visionos](https://github.com/illixion/halflife-visionos) |
| License | GPL-3.0 |
| Last commit | 2026-10-09 |
| visionOS | 26.4 or later |
| Input | hand tracking, game controller |
| Tags | fps, half-life, vr, 6dof, hand-tracking, xash3d |

Half-Life in full immersion on Apple Vision Pro: the Xash3D-FWGS engine with its ref\_gl renderer on Metal through ANGLE, presented with Compositor Services, with hand-tracked weapons and locomotion. Bring your own Half-Life from Steam \(the pre-25th-anniversary build\).

## Screenshots

From the port's README at b22c5744c706.

<img src="https://raw.githubusercontent.com/illixion/halflife-visionos/b22c5744c706c4bc4a9331706726fe2760063578/images/ingame.jpg" alt="In-game screenshot" width="400">

## Credits

- [FWGS](https://github.com/FWGS/xash3d-fwgs): Xash3D-FWGS, the engine
- [FWGS](https://github.com/FWGS/hlsdk-portable): hlsdk-portable, the Half-Life game code
- [ANGLE](https://github.com/google/angle): OpenGL ES on Metal
- [Lambda1VR \(DrBeef\)](https://github.com/DrBeef/Lambda1VR): Inspiration \(Quest VR port\); no code reused
- Valve: Original game

## Upstream projects

- <https://github.com/FWGS/xash3d-fwgs>
- <https://github.com/FWGS/hlsdk-portable>

---

This index only links to the developer's own repository. Automated checks and an AI security review can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
