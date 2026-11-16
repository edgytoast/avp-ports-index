# Portal 2 VR

**Portal 2** · originally on PC (2011)
Port by [@portal-in-the-visor](https://github.com/portal-in-the-visor)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/portal2-visionos && cd portal2-visionos && git checkout b5f1fc29b707daacf88a86bb50f228626586e893 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/portal2-visionos/blob/b5f1fc29b707daacf88a86bb50f228626586e893/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: The author played it on one M2 headset and archived it; this copy adds an install guide. Heavier areas can drop below 60 fps, the gun's glow is missing, and menus show on a flat screen. Not tested by the curator. |
| Plays as | 6DoF immersive |
| Health | OK |
| Scan | Reviewed by the curator 2026-11-15 · 0 commits since |
| Source (scanned) | [edgytoast/portal2-visionos at b5f1fc29b707](https://github.com/edgytoast/portal2-visionos/tree/b5f1fc29b707daacf88a86bb50f228626586e893) |
| Install guide | [AVP-INSTALL.md at b5f1fc29b707](https://github.com/edgytoast/portal2-visionos/blob/b5f1fc29b707daacf88a86bb50f228626586e893/AVP-INSTALL.md) |
| Repo | [edgytoast/portal2-visionos](https://github.com/edgytoast/portal2-visionos) |
| Branch | `portal2-visionos` |
| License | MIT |
| Last commit | 2026-11-14 |
| visionOS | 26.0 or later |
| Input | game controller, hand tracking |
| Tags | portal-2, portal, valve, vr, 6dof, first-person, puzzle, nxnative |

Portal 2 in VR on Apple Vision Pro, from the Nintendo Switch version: stereo 3D, head tracking, and your hand aims the portal gun while Joy-Cons walk. Built on nxnative from your own Switch dump. Listed from a copy with an install guide.

## Credits

- [portal-in-the-visor](https://github.com/portal-in-the-visor/portal2-visionos): Portal 2 VR, the visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [seedds](https://github.com/seedds/nxnative): nxnative, the Switch-to-Apple native framework it builds on
- [Gistix](https://github.com/Gistix/portal2vr): portal2vr, whose per-eye rendering approach it follows
- Valve: Original game

## Upstream projects

- <https://github.com/portal-in-the-visor/portal2-visionos>
- <https://github.com/seedds/nxnative>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
