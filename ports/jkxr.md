# JKXR for Apple Vision Pro

**Jedi Outcast and Jedi Academy** · originally on PC (2002)
Port by [@myMartek](https://github.com/myMartek)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/myMartek/JKXR && cd JKXR && git checkout a94c94603d06295956d3b5c100e4d8a836a5b0c8 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/myMartek/JKXR/blob/a94c94603d06295956d3b5c100e4d8a836a5b0c8/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: Both games play fully immersive with PS VR2 Sense controllers or a gamepad. Loading a level shows a black view for a while. |
| Plays as | 6DoF immersive |
| Health | OK |
| Scan | Reviewed by the curator 2026-11-16 · 0 commits since |
| Source (scanned) | [myMartek/JKXR at a94c94603d06](https://github.com/myMartek/JKXR/tree/a94c94603d06295956d3b5c100e4d8a836a5b0c8) |
| Install guide | [AVP-INSTALL.md at a94c94603d06](https://github.com/myMartek/JKXR/blob/a94c94603d06295956d3b5c100e4d8a836a5b0c8/AVP-INSTALL.md) |
| Repo | [myMartek/JKXR](https://github.com/myMartek/JKXR) |
| License | GPL-2.0 |
| Last commit | 2026-11-16 |
| visionOS | 26.4 or later |
| Input | game controller |

Team Beef's open-source VR engine for two first-person action classics of the early 2000s, native on visionOS: fully immersive, foveated, with tracked Sense controllers and room-scale play. Bring your own game files; AVP Play can fetch them from Steam.

## Credits

- [JKXR by Team Beef](https://github.com/Team-Beef-Studios/JKXR): VR port the visionOS version is based on
- [OpenJK](https://github.com/JACoders/OpenJK): Open-source engine
- [gl4es](https://github.com/ptitSeb/gl4es): OpenGL translation layer
- [ANGLE](https://chromium.googlesource.com/angle/angle): OpenGL ES on Metal

## Upstream projects

- <https://github.com/Team-Beef-Studios/JKXR>
- <https://github.com/JACoders/OpenJK>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
