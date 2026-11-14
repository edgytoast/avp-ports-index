# SpaghettiKart

**Mario Kart 64** · originally on Nintendo 64 (1996)
Port by [@rebelancap](https://github.com/rebelancap)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/SpaghettiKart-ios && cd SpaghettiKart-ios && git checkout 1eabc254e86b3a420d761dc8a8efe04c37fb1b06 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/SpaghettiKart-ios/blob/1eabc254e86b3a420d761dc8a8efe04c37fb1b06/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working |
| Plays as | 2D, 3D immersive |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/SpaghettiKart-ios at 1eabc254e86b](https://github.com/edgytoast/SpaghettiKart-ios/tree/1eabc254e86b3a420d761dc8a8efe04c37fb1b06) |
| Install guide | [AVP-INSTALL.md at 1eabc254e86b](https://github.com/edgytoast/SpaghettiKart-ios/blob/1eabc254e86b3a420d761dc8a8efe04c37fb1b06/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [edgytoast/SpaghettiKart-ios](https://github.com/edgytoast/SpaghettiKart-ios) |
| License | MIT |
| Last commit | 2026-11-13 |
| visionOS | 2.0 or later |
| Input | game controller |
| Tags | racing, mario-kart, n64, source-port, harbour-masters, stereo-3d, texture-packs |

Mario Kart 64 on Apple Vision Pro through Harbour Masters' SpaghettiKart, rendering natively on Metal: a resizable 2D window, or a stereoscopic 3D screen in your room. Enhancements, controllers, 4K texture packs, in-app ROM extraction. Bring your own ROM. Listed from a copy with an install guide.

## Screenshots

From the port's README at 1eabc254e86b.

<img src="https://raw.githubusercontent.com/edgytoast/SpaghettiKart-ios/1eabc254e86b3a420d761dc8a8efe04c37fb1b06/docs/screenshots/visionos-window.jpg" alt="Mario Kart 64 on Apple Vision Pro" width="400">

## Credits

- [rebelancap](https://github.com/rebelancap/SpaghettiKart-ios): The iOS and visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [Harbour Masters](https://github.com/HarbourMasters/SpaghettiKart): SpaghettiKart, the port this is built on
- [Harbour Masters](https://github.com/HarbourMasters/libultraship): libultraship, the platform layer
- Nintendo: Original game

## Upstream projects

- <https://github.com/rebelancap/SpaghettiKart-ios>
- <https://github.com/HarbourMasters/SpaghettiKart>
- <https://github.com/HarbourMasters/libultraship>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
