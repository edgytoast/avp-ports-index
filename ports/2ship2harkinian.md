# 2 Ship 2 Harkinian

**The Legend of Zelda: Majora's Mask** · originally on Nintendo 64 (2000)
Port by [@rebelancap](https://github.com/rebelancap)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/2ship2harkinian-ios && cd 2ship2harkinian-ios && git checkout a2ee3158f5a0edf5c1882db161c9186e81f216b3 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/2ship2harkinian-ios/blob/a2ee3158f5a0edf5c1882db161c9186e81f216b3/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working |
| Plays as | 2D, 3D immersive |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/2ship2harkinian-ios at a2ee3158f5a0](https://github.com/edgytoast/2ship2harkinian-ios/tree/a2ee3158f5a0edf5c1882db161c9186e81f216b3) |
| Install guide | [AVP-INSTALL.md at a2ee3158f5a0](https://github.com/edgytoast/2ship2harkinian-ios/blob/a2ee3158f5a0edf5c1882db161c9186e81f216b3/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [edgytoast/2ship2harkinian-ios](https://github.com/edgytoast/2ship2harkinian-ios) |
| License | MIT |
| Last commit | 2026-11-13 |
| visionOS | 2.0 or later |
| Input | game controller |
| Tags | zelda, majoras-mask, n64, source-port, harbour-masters, stereo-3d |

Majora's Mask on Apple Vision Pro through Harbour Masters' 2 Ship 2 Harkinian, rendering natively on Metal: a resizable 2D window, or a stereoscopic 3D screen in your room. Enhancements menu, texture packs and in-app ROM extraction. Bring your own ROM. Listed from a copy with an install guide.

## Screenshots

From the port's README at a2ee3158f5a0.

<img src="https://raw.githubusercontent.com/edgytoast/2ship2harkinian-ios/a2ee3158f5a0edf5c1882db161c9186e81f216b3/docs/screenshots/visionos-window.jpg" alt="The Legend of Zelda: Majora&#x27;s Mask on Apple Vision Pro" width="400">

## Credits

- [rebelancap](https://github.com/rebelancap/2ship2harkinian-ios): The iOS and visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [Harbour Masters](https://github.com/HarbourMasters/2ship2harkinian): 2 Ship 2 Harkinian, the port this is built on
- [Harbour Masters](https://github.com/HarbourMasters/libultraship): libultraship, the platform layer
- Nintendo: Original game

## Upstream projects

- <https://github.com/rebelancap/2ship2harkinian-ios>
- <https://github.com/HarbourMasters/2ship2harkinian>
- <https://github.com/HarbourMasters/libultraship>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
