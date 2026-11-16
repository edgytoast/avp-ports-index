# Perfect Dark

**Perfect Dark** · originally on Nintendo 64 (2000)
Port by [@rebelancap](https://github.com/rebelancap)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/perfect-dark-ios && cd perfect-dark-ios && git checkout 906f3f676d8e3a21d3e226d719137c32ffc02674 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/perfect-dark-ios/blob/906f3f676d8e3a21d3e226d719137c32ffc02674/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working |
| Plays as | 2D, 3D immersive |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/perfect-dark-ios at 906f3f676d8e](https://github.com/edgytoast/perfect-dark-ios/tree/906f3f676d8e3a21d3e226d719137c32ffc02674) |
| Install guide | [AVP-INSTALL.md at 906f3f676d8e](https://github.com/edgytoast/perfect-dark-ios/blob/906f3f676d8e3a21d3e226d719137c32ffc02674/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [edgytoast/perfect-dark-ios](https://github.com/edgytoast/perfect-dark-ios) |
| License | Custom license |
| Last commit | 2026-11-13 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | fps, first-person, n64, decompilation, stereo-3d, dabs-mod, xbla |

Perfect Dark on Apple Vision Pro: the decompilation through the PC port and Dab's Mod, on Metal. A 2D window or a stereoscopic 3D screen in your room, with optional Xbox 360 \(XBLA\) art and GoldenEye 007 \(GE Plus\) from your own copies. Bring your own ROM. Listed from a copy with an install guide.

## Screenshots

From the port's README at 906f3f676d8e.

<img src="https://raw.githubusercontent.com/edgytoast/perfect-dark-ios/906f3f676d8e3a21d3e226d719137c32ffc02674/docs/screenshots/vision-pro-airbase-xbla.jpg" alt="Perfect Dark on Apple Vision Pro — Air Base, XBLA art" width="400">

## Credits

- [rebelancap](https://github.com/rebelancap/perfect-dark-ios): The iOS and visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [DabDavis](https://github.com/DabDavis/perfect-dark-dabs-mod): Dab's Mod, the fork this port is built on
- [Perfect Dark PC port](https://github.com/perfect-dark-pc-port/perfect_dark): Platform layer, Fast3D renderer and CLI
- [n64decomp](https://github.com/n64decomp/perfect_dark): Perfect Dark decompilation
- [ANGLE](https://chromium.googlesource.com/angle/angle): OpenGL ES on Metal
- [SDL2](https://libsdl.org): Windowing, input and audio
- Rare / Microsoft: Original game

## Upstream projects

- <https://github.com/rebelancap/perfect-dark-ios>
- <https://github.com/DabDavis/perfect-dark-dabs-mod>
- <https://github.com/perfect-dark-pc-port/perfect_dark>
- <https://github.com/n64decomp/perfect_dark>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
