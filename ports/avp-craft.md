# AVPcraft

**Minecraft: Java Edition**
Port by Zach Schwendiman ([@zschwendi](https://github.com/zschwendi))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/zschwendi/avp-craft && cd avp-craft && git checkout 81a863314917f99662735c48a4f03b65788de9b3 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/zschwendi/avp-craft/blob/81a863314917f99662735c48a4f03b65788de9b3/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Partially working |
| Status | Partially working: Windowed play needs further testing; immersive mode has remaining bugs. The complete build has not yet been repeated from a clean public checkout. See the install guide for known limits. |
| Plays as | 2D, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-10-29 · 0 commits since |
| Source (scanned) | [zschwendi/avp-craft at 81a863314917](https://github.com/zschwendi/avp-craft/tree/81a863314917f99662735c48a4f03b65788de9b3) |
| Install guide | [AVP-INSTALL.md at 81a863314917](https://github.com/zschwendi/avp-craft/blob/81a863314917f99662735c48a4f03b65788de9b3/AVP-INSTALL.md) |
| Repo | [zschwendi/avp-craft](https://github.com/zschwendi/avp-craft) |
| License | MIT |
| Last commit | 2026-10-29 |
| visionOS | 26.0 or later |
| Input | game controller |

Minecraft: Java Edition 26.2 compiled ahead of time for Vision Pro, with an AVPcraft launcher, windowed play, Vivecraft immersion and PSVR2 Sense input.

## Credits

- [vivecraft-visionos](https://github.com/rebelancap/vivecraft-visionos): Vision Pro port foundation
- [Vivecraft](https://github.com/Vivecraft/VivecraftMod): Minecraft VR integration
- [Klepton](https://github.com/shinyquagsire23/Klepton): Ahead-of-time Java runtime

## Upstream projects

- <https://github.com/rebelancap/vivecraft-visionos>
- <https://github.com/Vivecraft/VivecraftMod>
- <https://github.com/shinyquagsire23/Klepton>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
