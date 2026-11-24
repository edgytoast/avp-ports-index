# Xbawks

**Original Xbox games** · originally on Xbox (2001)
Emulator by A.Cervantez ([@Ywach404](https://github.com/Ywach404))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/Ywach404/xbawks-avp && cd xbawks-avp && git checkout dc753349d88b19cf91707b2d34179277ca1c24a8 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/Ywach404/xbawks-avp/blob/dc753349d88b19cf91707b2d34179277ca1c24a8/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: Original Xbox emulator \(xemu port\) running on the headset. Needs Apparition on a Mac at every launch for JIT. Many titles play; see the compatibility table. |
| Plays as | 2D |
| Health | OK |
| Scan | Scanned 2026-11-24 · 0 commits since |
| Source (scanned) | [Ywach404/xbawks-avp at dc753349d88b](https://github.com/Ywach404/xbawks-avp/tree/dc753349d88b19cf91707b2d34179277ca1c24a8) |
| Install guide | [AVP-INSTALL.md at dc753349d88b](https://github.com/Ywach404/xbawks-avp/blob/dc753349d88b19cf91707b2d34179277ca1c24a8/AVP-INSTALL.md) |
| Repo | [Ywach404/xbawks-avp](https://github.com/Ywach404/xbawks-avp) |
| License | GPL-2.0 |
| Last commit | 2026-11-24 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | emulator |

Original Xbox emulator for Apple Vision Pro, running on the headset. A port of xemu with a visionOS shell, JIT through Apparition, and PSVR2 Sense and Bluetooth controller input. Watch it run: https://youtu.be/AnmeuEjDdMU Sibling project 720, for the Xbox 360: https://github.com/Ywach404/720-avp

## Screenshots

From the port's repo at dc753349d88b.

<img src="https://raw.githubusercontent.com/Ywach404/xbawks-avp/dc753349d88b19cf91707b2d34179277ca1c24a8/docs/media/promo.gif" alt="Screenshot of Xbawks" width="400">
<img src="https://raw.githubusercontent.com/Ywach404/xbawks-avp/dc753349d88b19cf91707b2d34179277ca1c24a8/docs/media/colorways.gif" alt="Screenshot of Xbawks" width="400">
<img src="https://raw.githubusercontent.com/Ywach404/xbawks-avp/dc753349d88b19cf91707b2d34179277ca1c24a8/docs/media/dpad.gif" alt="Screenshot of Xbawks" width="400">

## Credits

- [xemu](https://github.com/xemu-project/xemu): Emulator core
- [zlixas/xemu \(Apple Silicon fork\)](https://github.com/zlixas/xemu): Metal-compatible Vulkan path, IOSurface display

## Upstream projects

- <https://github.com/xemu-project/xemu>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
