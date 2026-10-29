# 117

**Halo: Combat Evolved**
Port by Zach Schwendiman ([@zschwendi](https://github.com/zschwendi))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/zschwendi/117-vision && cd 117-vision && git checkout b25332ef95bb2df1735e3d8640167a1e62b8252a && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/zschwendi/117-vision/blob/b25332ef95bb2df1735e3d8640167a1e62b8252a/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Partially working |
| Status | Partially working: Windowed play is stable per the developer. Immersive mode has remaining bugs; tracked input targets on-foot campaign play. Vehicles and turrets use conventional controls. |
| Plays as | 2D, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-10-29 · 0 commits since |
| Source (scanned) | [zschwendi/117-vision at b25332ef95bb](https://github.com/zschwendi/117-vision/tree/b25332ef95bb2df1735e3d8640167a1e62b8252a) |
| Install guide | [AVP-INSTALL.md at b25332ef95bb](https://github.com/zschwendi/117-vision/blob/b25332ef95bb2df1735e3d8640167a1e62b8252a/AVP-INSTALL.md) |
| Repo | [zschwendi/117-vision](https://github.com/zschwendi/117-vision) |
| License | MIT |
| Last commit | 2026-10-29 |
| visionOS | 26.0 or later |
| Input | game controller |

Native Halo: Combat Evolved port based on Master Chef, with windowed and immersive Vision Pro play, PSVR2 Sense tracked aiming and optional iCloud save sync.

## Screenshots

From the port's README at b25332ef95bb.

<img src="https://raw.githubusercontent.com/zschwendi/117-vision/b25332ef95bb2df1735e3d8640167a1e62b8252a/docs/assets/117-sense-rifle-combat.png" alt="Halo gameplay on Vision Pro with a visible hand and PSVR2 Sense controller aiming the assault rifle" width="400">
<img src="https://raw.githubusercontent.com/zschwendi/117-vision/b25332ef95bb2df1735e3d8640167a1e62b8252a/docs/assets/117-sense-sniper-scope.png" alt="A visible PSVR2 Sense controller beneath the sniper scope during gameplay" width="400">
<img src="https://raw.githubusercontent.com/zschwendi/117-vision/b25332ef95bb2df1735e3d8640167a1e62b8252a/docs/assets/117-sense-grenade-throw.png" alt="A visible hand and PSVR2 Sense controller during a grenade throwing gesture" width="400">

## Credits

- [Master Chef](https://github.com/mitchaiet/master-chef): Executable translation, native runtime, Metal renderer and visionOS port

## Upstream projects

- <https://github.com/mitchaiet/master-chef>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
