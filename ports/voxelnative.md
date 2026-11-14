# VoxelNative

**Luanti** · originally on PC (2010)
Port by [@bettse](https://github.com/bettse)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/voxelnative && cd voxelnative && git checkout f8aca2d1efe4f8ab20dcb13ea786e755dc90bf17 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/voxelnative/blob/f8aca2d1efe4f8ab20dcb13ea786e755dc90bf17/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: Joining a server and playing works in the headset, with VoxeLibre as the daily driver. The README calls it a work in progress, rough in places. |
| Plays as | 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/voxelnative at f8aca2d1efe4](https://github.com/edgytoast/voxelnative/tree/f8aca2d1efe4f8ab20dcb13ea786e755dc90bf17) |
| Install guide | [AVP-INSTALL.md at f8aca2d1efe4](https://github.com/edgytoast/voxelnative/blob/f8aca2d1efe4f8ab20dcb13ea786e755dc90bf17/AVP-INSTALL.md) |
| Repo | [edgytoast/voxelnative](https://github.com/edgytoast/voxelnative) |
| License | Custom license |
| Last commit | 2026-11-13 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | luanti, minetest, voxelibre, voxel, sandbox, vr, 6dof |

A native Swift and Metal Luanti \(Minetest\) client for Apple Vision Pro. It speaks the Luanti protocol to any server and renders the world per eye in full immersion; walk, dig, place and craft with PS VR2 Sense controllers or a Bluetooth keyboard. Listed from a copy with an install guide.

## Credits

- [bettse](https://github.com/bettse/voxelnative): VoxelNative, the Apple Vision Pro client
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [Luanti](https://github.com/luanti-org/luanti): The engine whose network protocol this client reimplements
- [VoxeLibre](https://github.com/VoxeLibre/VoxeLibre): The game it's built and tested against
- [BigInt](https://github.com/attaswift/BigInt): Third-party code \(MIT\)
- Luanti contributors: Original game

## Upstream projects

- <https://github.com/bettse/voxelnative>
- <https://github.com/luanti-org/luanti>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
