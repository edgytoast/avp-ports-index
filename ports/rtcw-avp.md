# RTCW for Apple Vision Pro

**Return to Castle Wolfenstein** · originally on PC (2001)
Port by [@florind-ens](https://github.com/florind-ens)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/RTCW-AVP && cd RTCW-AVP && git checkout 9982831d996d9f6058b75684c2dae3be2204b5a6 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/RTCW-AVP/blob/9982831d996d9f6058b75684c2dae3be2204b5a6/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: Single player, in VR or in a flat window. |
| Plays as | 2D, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/RTCW-AVP at 9982831d996d](https://github.com/edgytoast/RTCW-AVP/tree/9982831d996d9f6058b75684c2dae3be2204b5a6) |
| Install guide | [AVP-INSTALL.md at 9982831d996d](https://github.com/edgytoast/RTCW-AVP/blob/9982831d996d9f6058b75684c2dae3be2204b5a6/AVP-INSTALL.md) |
| Repo | [edgytoast/RTCW-AVP](https://github.com/edgytoast/RTCW-AVP) |
| License | GPL-3.0 |
| Last commit | 2026-11-13 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | fps, shooter, first-person, vr, 6dof, iortcw, id-tech-3, source-port |

Return to Castle Wolfenstein's single player on Apple Vision Pro, on the iortcw engine: VR in a fully immersive space with stereo, head tracking, a virtual menu screen and DualSense controls, or a flat window. Bring your own GOG or Steam pk3 files. Listed from a copy with an install guide.

## Credits

- [florind-ens](https://github.com/florind-ens/RTCW-AVP): The Apple Vision Pro port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [iortcw](https://github.com/iortcw/iortcw): The engine
- [RTCWQuest](https://github.com/DrBeef/RTCWQuest): VR design reference \(head/body split, stereo, world scale\)
- [halflife-visionos](https://github.com/illixion/halflife-visionos): The ANGLE-for-visionOS build approach
- [ANGLE](https://chromium.googlesource.com/angle/angle): OpenGL ES on Metal
- [XcodeGen](https://github.com/yonaskolb/XcodeGen): Xcode project generation
- Gray Matter Interactive / id Software: Original game

## Upstream projects

- <https://github.com/florind-ens/RTCW-AVP>
- <https://github.com/iortcw/iortcw>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
