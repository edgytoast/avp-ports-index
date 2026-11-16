# WiiCompiled Vision

**Mario Kart Wii** · originally on Wii (2008)
Port by [@iChris4](https://github.com/iChris4)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/wiicompiled_vr-avp-index && cd wiicompiled_vr-avp-index && git checkout 87c18efa00ceca1706321a1b0d87254a92afbdc7 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/wiicompiled_vr-avp-index/blob/87c18efa00ceca1706321a1b0d87254a92afbdc7/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: Runs on Apple Vision Pro \(tested on visionOS 26.6.1\): menus on a virtual screen, races in stereo. The docs call the port experimental; comfort, frame timing and bare-hand driving are still being tuned. |
| Plays as | 2D, 3D immersive, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/wiicompiled_vr-avp-index at 87c18efa00ce](https://github.com/edgytoast/wiicompiled_vr-avp-index/tree/87c18efa00ceca1706321a1b0d87254a92afbdc7) |
| Install guide | [AVP-INSTALL.md at 87c18efa00ce](https://github.com/edgytoast/wiicompiled_vr-avp-index/blob/87c18efa00ceca1706321a1b0d87254a92afbdc7/AVP-INSTALL.md) |
| Repo | [edgytoast/wiicompiled_vr-avp-index](https://github.com/edgytoast/wiicompiled_vr-avp-index) |
| Branch | `vision-pro` |
| License | GPL-3.0 |
| Last commit | 2026-11-13 |
| visionOS | 2.0 or later |
| Input | game controller, hand tracking |
| Tags | racing, kart, mario-kart, wii, recompilation, vr, first-person, hand-tracking |

Mario Kart Wii on Apple Vision Pro through WiiCompiled, a static recompilation with no emulator: 6DoF stereo races, from the chase camera or a life-size cockpit, with menus on a virtual screen, or a window. Bring your own PAL disc image. Listed from a copy with an install guide.

## Screenshots

From the port's README at 87c18efa00ce.

<img src="https://raw.githubusercontent.com/edgytoast/wiicompiled_vr-avp-index/87c18efa00ceca1706321a1b0d87254a92afbdc7/docs/images/wiicompiled-vr-logo.png" alt="Mario Kart WiiCompiled VR logo (logo by Inkwreck)" width="400">

## Credits

- [iChris4](https://github.com/iChris4/Wiicompiled_VR): WiiCompiled Vision, the Apple Vision Pro port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [WiiCompiled](https://github.com/patchzyy/Wiicompiled): The Mario Kart Wii static recompilation this fork builds on
- [Aurora](https://github.com/encounter/aurora): GameCube and Wii graphics layer
- [Dawn](https://dawn.googlesource.com/dawn): WebGPU implementation under Aurora
- [heurazy](https://github.com/heurazy/mario-kart-wii-VR-port): mario-kart-wii-VR-port, source of the cockpit wheel and hand steering
- [Dolphin Emulator](https://github.com/dolphin-emu/dolphin): Hardware reference, DSP coefficient ROM and WiiConnect24 bootstrap files
- [Retro Rewind \(ZPL\)](https://wiki.tockdom.com/wiki/Retro_Rewind): The supported mod distribution
- Nintendo: Original game

## Upstream projects

- <https://github.com/iChris4/Wiicompiled_VR>
- <https://github.com/patchzyy/Wiicompiled>
- <https://github.com/encounter/aurora>
- <https://github.com/heurazy/mario-kart-wii-VR-port>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
