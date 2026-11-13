# Wind Waker VR

**The Legend of Zelda: The Wind Waker** · originally on GameCube (2002)
Port by Trevorbilt ([@edgytoast](https://github.com/edgytoast))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/windwaker-visionos && cd windwaker-visionos && git checkout a1fcc30a3b8ee86eeff204b58a642b77d4aaa25c && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/windwaker-visionos/blob/a1fcc30a3b8ee86eeff204b58a642b77d4aaa25c/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working · Curator's own port |
| Status | Working: Plays in a window beside your apps, in 3D or in 2D like the original, with a gamepad; played on Apple Vision Pro. Full and Progressive VR are in the app behind an experimental switch, untested on a headset. |
| Plays as | 2D, 3D shared space |
| Health | OK |
| Scan | Scanned 2026-10-29 · 0 commits since |
| Source (scanned) | [edgytoast/windwaker-visionos at a1fcc30a3b8e](https://github.com/edgytoast/windwaker-visionos/tree/a1fcc30a3b8ee86eeff204b58a642b77d4aaa25c) |
| Install guide | [AVP-INSTALL.md at a1fcc30a3b8e](https://github.com/edgytoast/windwaker-visionos/blob/a1fcc30a3b8ee86eeff204b58a642b77d4aaa25c/AVP-INSTALL.md) |
| Repo | [edgytoast/windwaker-visionos](https://github.com/edgytoast/windwaker-visionos) |
| Developer site | <https://trevorbilt.com> |
| License | MIT |
| Last commit | 2026-10-29 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | zelda, wind-waker, gamecube, decompilation, shared-space, window, aurora |

The Wind Waker in a window beside your apps on Apple Vision Pro, with the Great Sea rebuilt in real 3D behind the glass every frame, so you can lean in and look around Outset. Or switch it to 2D, like the GameCube. A native visionOS port of SwitchWaker. Bring your own disc.

## Screenshots

From the port's README at a1fcc30a3b8e.

<img src="https://raw.githubusercontent.com/edgytoast/windwaker-visionos/a1fcc30a3b8ee86eeff204b58a642b77d4aaa25c/visionos/docs/images/window-3d.jpg" alt="Link on Outset Island&#x27;s pier, in a window floating in a living room" width="400">
<img src="https://raw.githubusercontent.com/edgytoast/windwaker-visionos/a1fcc30a3b8ee86eeff204b58a642b77d4aaa25c/visionos/docs/images/window-angle.jpg" alt="Link on Windfall Island&#x27;s dock, in a window seen from off to one side: he and the cliffs stand out of the sea behind the glass" width="400">

## Credits

- [Trevorbilt](https://trevorbilt.com): visionOS port
- [centollOS](https://github.com/centollOS/SwitchWaker): SwitchWaker, the native port this builds on \(Pulpparty, depende3000\)
- [zeldaret](https://github.com/zeldaret/tww): The Wind Waker decompilation
- [snrubrm](https://github.com/snrubrm/tww): Completed the decompilation's missing functions
- [encounter](https://github.com/encounter/aurora): Aurora, the GameCube graphics, input and disc layer
- [JoeyAW](https://github.com/JoeyAW/TPVR): TPVR, whose stereo view and VR hooks this port follows
- [Twilit Realm](https://twilitrealm.dev/): Dusklight, the model for SwitchWaker's SDK layer
- [iChris4](https://github.com/iChris4/Wiicompiled_VR): WiiCompiled Vision, source of the visionOS OpenXR provider

## Upstream projects

- <https://github.com/centollOS/SwitchWaker>
- <https://github.com/zeldaret/tww>
- <https://github.com/encounter/aurora>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
