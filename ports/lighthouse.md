# Lighthouse

**Banjo-Kazooie** · originally on Nintendo 64 (1998)
Port by [@rebelancap](https://github.com/rebelancap)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/Lighthouse-ios && cd Lighthouse-ios && git checkout b2b6b2b8817b7229f63beaad30237f2af2d35e81 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/Lighthouse-ios/blob/b2b6b2b8817b7229f63beaad30237f2af2d35e81/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working |
| Plays as | 2D, 3D immersive |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/Lighthouse-ios at b2b6b2b8817b](https://github.com/edgytoast/Lighthouse-ios/tree/b2b6b2b8817b7229f63beaad30237f2af2d35e81) |
| Install guide | [AVP-INSTALL.md at b2b6b2b8817b](https://github.com/edgytoast/Lighthouse-ios/blob/b2b6b2b8817b7229f63beaad30237f2af2d35e81/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [edgytoast/Lighthouse-ios](https://github.com/edgytoast/Lighthouse-ios) |
| License | MIT |
| Last commit | 2026-11-13 |
| visionOS | 2.0 or later |
| Input | game controller |
| Tags | banjo-kazooie, platformer, n64, source-port, harbour-masters, stereo-3d, randomizer |

Banjo-Kazooie on Apple Vision Pro through Harbour Masters' Lighthouse, rendering natively on Metal: a resizable 2D window, or a stereoscopic 3D screen in your room. Enhancements, randomizer, co-op, ROM hacks and in-app ROM extraction. Bring your own ROM. Listed from a copy with an install guide.

## Screenshots

From the port's README at b2b6b2b8817b.

<img src="https://raw.githubusercontent.com/edgytoast/Lighthouse-ios/b2b6b2b8817b7229f63beaad30237f2af2d35e81/docs/screenshots/visionos-window.jpg" alt="Banjo-Kazooie on Apple Vision Pro" width="400">

## Credits

- [rebelancap](https://github.com/rebelancap/Lighthouse-ios): The iOS and visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [Harbour Masters](https://github.com/HarbourMasters/Lighthouse): Lighthouse, the port this is built on
- [Harbour Masters](https://github.com/HarbourMasters/libultraship): libultraship, the platform layer
- Nintendo and Rare: Original game

## Upstream projects

- <https://github.com/rebelancap/Lighthouse-ios>
- <https://github.com/HarbourMasters/Lighthouse>
- <https://github.com/HarbourMasters/libultraship>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
