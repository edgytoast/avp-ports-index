# Holofold

**Nintendo 3DS games** · originally on Other (2011)
Emulator by [@zlinoliver](https://github.com/zlinoliver)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/zlinoliver/Holofold && cd Holofold && git checkout c646470c3eeb06365846edb94b7a4fdb7870da2c && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/zlinoliver/Holofold/blob/c646470c3eeb06365846edb94b7a4fdb7870da2c/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Partially working |
| Status | Partially working: Early and experimental, per the developer. On an M5 headset Super Mario 3D Land plays at about 60 fps without JIT and Ocarina of Time 3D boots. A game can freeze after several minutes of play. Not tested by the curator. |
| Plays as | 3D shared space (stereo) |
| Health | OK |
| Scan | Scanned 2026-11-25 · 0 commits since |
| Source (scanned) | [zlinoliver/Holofold at c646470c3eeb](https://github.com/zlinoliver/Holofold/tree/c646470c3eeb06365846edb94b7a4fdb7870da2c) |
| Install guide | [AVP-INSTALL.md at c646470c3eeb](https://github.com/zlinoliver/Holofold/blob/c646470c3eeb06365846edb94b7a4fdb7870da2c/AVP-INSTALL.md) |
| Repo | [zlinoliver/Holofold](https://github.com/zlinoliver/Holofold) |
| License | GPL-2.0 |
| Last commit | 2026-11-25 |
| visionOS | 26.0 or later |
| Input | game controller, hand tracking |
| Tags | emulator, 3ds, stereo-3d |

3DS emulation on Apple Vision Pro with the top screen in real stereoscopic 3D, optionally curved, and the bottom screen in its own window you tap by looking and pinching. A fork of Bifold on the Azahar core, from the developer of SheikahVision. Bring your own games.

## Screenshots

From the port's repo at c646470c3eeb.

<img src="https://raw.githubusercontent.com/zlinoliver/Holofold/c646470c3eeb06365846edb94b7a4fdb7870da2c/docs/images/holofold-vision-pro.jpg" alt="Screenshot of Holofold" width="400">

## Credits

- [zlinoliver](https://github.com/zlinoliver/Holofold): Holofold, the visionOS fork
- [Bifold](https://github.com/Bifold-Emu/Bifold): The iOS front end Holofold forks
- [Azahar](https://github.com/azahar-emu/azahar): Emulator core

## Upstream projects

- <https://github.com/Bifold-Emu/Bifold>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
