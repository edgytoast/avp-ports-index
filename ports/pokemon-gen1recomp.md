# Gen1 Vision

**Pokémon Red, Blue and Yellow** · originally on Other (1996)
Port by [@myMartek](https://github.com/myMartek)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/gen1recomp && cd gen1recomp && git checkout bbe5f881c7b070233f724ba6927b82666e54568c && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/gen1recomp/blob/bbe5f881c7b070233f724ba6927b82666e54568c/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Partially working |
| Status | Partially working: The game shows on a world-locked panel in an immersive space and is played with a game controller. The visionOS README records Simulator verification. |
| Plays as | 2D |
| Health | OK |
| Scan | Scanned 2026-11-13 · 0 commits since |
| Source (scanned) | [edgytoast/gen1recomp at bbe5f881c7b0](https://github.com/edgytoast/gen1recomp/tree/bbe5f881c7b070233f724ba6927b82666e54568c) |
| Install guide | [AVP-INSTALL.md at bbe5f881c7b0](https://github.com/edgytoast/gen1recomp/blob/bbe5f881c7b070233f724ba6927b82666e54568c/AVP-INSTALL.md) |
| Repo | [edgytoast/gen1recomp](https://github.com/edgytoast/gen1recomp) |
| Branch | `visionos-foveation` |
| License | MIT |
| Last commit | 2026-11-13 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | rpg, pokemon, game-boy, love2d, lua, recreation |

Gen 1 Pokémon on Apple Vision Pro: a visionOS build of Gen1Recomp, the hand-written Lua and LÖVE recreation that decodes its data from your cartridge, on a panel in an immersive space. Bring your own US Red, Blue or Yellow ROM. Listed from a copy with an install guide.

## Screenshots

From the port's README at bbe5f881c7b0.

<img src="https://raw.githubusercontent.com/edgytoast/gen1recomp/bbe5f881c7b070233f724ba6927b82666e54568c/.github/resources/sidestore-badge.png" alt="Add to SideStore" width="400">
<img src="https://raw.githubusercontent.com/edgytoast/gen1recomp/bbe5f881c7b070233f724ba6927b82666e54568c/.github/resources/feather-badge.png" alt="Add to Feather" width="400">
<img src="https://raw.githubusercontent.com/edgytoast/gen1recomp/bbe5f881c7b070233f724ba6927b82666e54568c/.github/resources/altstore-badge.png" alt="Add to AltStore" width="400">

## Credits

- [myMartek](https://github.com/myMartek/gen1recomp): Gen1 Vision, the visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [bryanthaboi](https://github.com/bryanthaboi/gen1recomp): Gen1Recomp, the LÖVE recreation this visionOS build is a fork of
- [pret](https://github.com/pret/pokered): pokered disassembly, credited in the README
- [LÖVE](https://github.com/love2d/love): Game framework
- Game Freak / Nintendo: Original game

## Upstream projects

- <https://github.com/myMartek/gen1recomp>
- <https://github.com/bryanthaboi/gen1recomp>
- <https://github.com/pret/pokered>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
