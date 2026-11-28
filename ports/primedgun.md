# PrimedGun 2.0

**Metroid Prime** · originally on GameCube (2002)
Port by [@iChris4](https://github.com/iChris4)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/iChris4/MetroidPrimePortVR && cd MetroidPrimePortVR && git checkout d9aa4a0294a0584ce7aa325b6aae4d041da2a0f5 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/iChris4/MetroidPrimePortVR/blob/d9aa4a0294a0584ce7aa325b6aae4d041da2a0f5/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: Played on a headset with PS VR2 Sense controllers \(the Frigate and beyond\) and a DualSense, per the developers. Stereo comfort, frame pacing and Joy-Con hand tracking are not yet checked there. Needs a paid developer account. Not tested by the curator. |
| Plays as | 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-11-28 · 0 commits since |
| Source (scanned) | [iChris4/MetroidPrimePortVR at d9aa4a0294a0](https://github.com/iChris4/MetroidPrimePortVR/tree/d9aa4a0294a0584ce7aa325b6aae4d041da2a0f5) |
| Install guide | [AVP-INSTALL.md at d9aa4a0294a0](https://github.com/iChris4/MetroidPrimePortVR/blob/d9aa4a0294a0584ce7aa325b6aae4d041da2a0f5/AVP-INSTALL.md) |
| Repo | [iChris4/MetroidPrimePortVR](https://github.com/iChris4/MetroidPrimePortVR) |
| License | CC0-1.0 |
| Last commit | 2026-11-28 |
| visionOS | 26.0 or later |
| Input | game controller, hand tracking |
| Tags | metroid, metroid-prime, gamecube, decompilation, vr, first-person, shooter |

Metroid Prime in native VR, built from the PrimeDecomp decompilation with no emulator: a 6DoF arm cannon that follows your Sense controller or Joy-Con, room-scale movement, and randomizer and Archipelago support. By Nobbie and iChris4. Bring your own disc image.

## Credits

- [Nobbie and iChris4](https://github.com/iChris4/MetroidPrimePortVR): PrimedGun 2.0, including the Apple Vision Pro build
- [Nobbie](https://github.com/Nobbie248/PrimedGun): The original PrimedGun
- PrimeDecomp: The Metroid Prime decompilation the game is built from
- Odran's MetroidPrimePort: Native port the engine builds on
- [Aurora](https://github.com/encounter/aurora): GameCube graphics layer
- [Dawn](https://dawn.googlesource.com/dawn): WebGPU implementation under Aurora
- [Wiicompiled VR](https://github.com/iChris4/Wiicompiled_VR): OpenXR and visionOS layer
- Nintendo and Retro Studios: Original game

## Upstream projects

- <https://github.com/Nobbie248/PrimedGun>
- <https://github.com/iChris4/Wiicompiled_VR>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
