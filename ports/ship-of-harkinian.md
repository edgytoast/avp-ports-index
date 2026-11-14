# Ship of Harkinian

**The Legend of Zelda: Ocarina of Time** · originally on Nintendo 64 (1998)
Port by [@rebelancap](https://github.com/rebelancap)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/Shipwright-ios && cd Shipwright-ios && git checkout a61edd238439f0fd81ef1e49694731e8cfca334c && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/Shipwright-ios/blob/a61edd238439f0fd81ef1e49694731e8cfca334c/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working |
| Plays as | 2D, 3D immersive, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/Shipwright-ios at a61edd238439](https://github.com/edgytoast/Shipwright-ios/tree/a61edd238439f0fd81ef1e49694731e8cfca334c) |
| Install guide | [AVP-INSTALL.md at a61edd238439](https://github.com/edgytoast/Shipwright-ios/blob/a61edd238439f0fd81ef1e49694731e8cfca334c/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [edgytoast/Shipwright-ios](https://github.com/edgytoast/Shipwright-ios) |
| License | MIT |
| Last commit | 2026-11-13 |
| visionOS | 2.0 or later |
| Input | game controller |
| Tags | zelda, ocarina-of-time, n64, source-port, harbour-masters, vr, first-person, stereo-3d |

Ocarina of Time on Apple Vision Pro through Harbour Masters' Ship of Harkinian, rendering natively on Metal: a resizable 2D window, a stereoscopic 3D screen in your room, or first-person VR with PS VR2 Sense controllers as your hands. Bring your own ROM. Listed from a copy with an install guide.

## Screenshots

From the port's README at a61edd238439.

<img src="https://raw.githubusercontent.com/edgytoast/Shipwright-ios/a61edd238439f0fd81ef1e49694731e8cfca334c/docs/screenshots/visionos-window.jpg" alt="The Legend of Zelda: Ocarina of Time on Apple Vision Pro" width="400">

## Credits

- [rebelancap](https://github.com/rebelancap/Shipwright-ios): The iOS and visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [Harbour Masters](https://github.com/HarbourMasters/Shipwright): Ship of Harkinian \(Shipwright\), the port this is built on
- [Harbour Masters](https://github.com/HarbourMasters/libultraship): libultraship, the platform layer
- [Harbour Masters](https://github.com/HarbourMasters/ZAPDTR): ZAPDTR, the asset pipeline
- Nintendo: Original game

## Upstream projects

- <https://github.com/rebelancap/Shipwright-ios>
- <https://github.com/HarbourMasters/Shipwright>
- <https://github.com/HarbourMasters/libultraship>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
