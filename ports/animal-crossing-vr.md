# Animal Crossing VR

**Animal Crossing** · originally on GameCube (2002)
Port by Trevorbilt ([@edgytoast](https://github.com/edgytoast))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/animalcrossing-visionos && cd animalcrossing-visionos && git checkout b5b463f8e29a51a5718db30ecb5d38ee175f0a40 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/animalcrossing-visionos/blob/b5b463f8e29a51a5718db30ecb5d38ee175f0a40/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working · Curator's own port |
| Status | Working: Plays in Full and Progressive immersion with PS VR2 Sense controllers, bare hands or a gamepad, and in a 3D window with a gamepad. Played on Apple Vision Pro in the Window view; Full and Progressive tested in the visionOS Simulator. |
| Plays as | 3D shared space, 6DoF immersive, 6DoF progressive |
| Health | OK |
| Scan | Scanned 2026-10-10 · 0 commits since |
| Source (scanned) | [edgytoast/animalcrossing-visionos at b5b463f8e29a](https://github.com/edgytoast/animalcrossing-visionos/tree/b5b463f8e29a51a5718db30ecb5d38ee175f0a40) |
| Install guide | [AVP-INSTALL.md at b5b463f8e29a](https://github.com/edgytoast/animalcrossing-visionos/blob/b5b463f8e29a51a5718db30ecb5d38ee175f0a40/AVP-INSTALL.md) |
| Repo | [edgytoast/animalcrossing-visionos](https://github.com/edgytoast/animalcrossing-visionos) |
| Developer site | <https://trevorbilt.com> |
| License | Custom license |
| Last commit | 2026-10-10 |
| visionOS | 26.0 or later |
| Input | game controller, hand tracking |
| Tags | animal-crossing, vr, first-person, life-sim, gamecube, decompilation, hand-tracking |

Animal Crossing in six degrees of freedom on Apple Vision Pro: walk your town at life size and swing the net with your own arm, or keep it in a 3D window beside your apps. A native visionOS port of LiquidAzir's VR mod. Bring your own disc.

## Screenshots

From the port's README at b5b463f8e29a.

<img src="https://raw.githubusercontent.com/edgytoast/animalcrossing-visionos/b5b463f8e29a51a5718db30ecb5d38ee175f0a40/docs/images/window-view.jpg" alt="The player outside their house, beside the town&#x27;s notice board and mailbox, in a window floating in a living room" width="400">
<img src="https://raw.githubusercontent.com/edgytoast/animalcrossing-visionos/b5b463f8e29a51a5718db30ecb5d38ee175f0a40/docs/images/full-immersion.jpg" alt="First person in town: a house with a green roof behind a white fence, fruit trees, a paved path and a notice board, under a blue sky" width="400">
<img src="https://raw.githubusercontent.com/edgytoast/animalcrossing-visionos/b5b463f8e29a51a5718db30ecb5d38ee175f0a40/docs/images/window-angle.jpg" alt="The same window seen from the side: the notice board and the house stand out of the town behind the glass" width="400">

## Credits

- [Trevorbilt](https://trevorbilt.com): visionOS port
- [LiquidAzir](https://github.com/LiquidAzir/animal-crossing-vr): animal-crossing-vr, the VR mod this port is built on
- [ACreTeam](https://github.com/ACreTeam/ac-decomp): Animal Crossing decompilation
- [flyngmt](https://github.com/flyngmt/ACGC-PC-Port): ACGC-PC-Port, the native PC port
- [zwaetschge](https://github.com/zwaetschge/ACGC-Android-Port): ACGC-Android-Port, the 64-bit base
- [iChris4](https://github.com/iChris4/Wiicompiled_VR): WiiCompiled Vision, source of the visionOS OpenXR provider

## Upstream projects

- <https://github.com/LiquidAzir/animal-crossing-vr>
- <https://github.com/zwaetschge/ACGC-Android-Port>
- <https://github.com/flyngmt/ACGC-PC-Port>
- <https://github.com/ACreTeam/ac-decomp>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
