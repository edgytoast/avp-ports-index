# GalaxyVision

**Super Mario Galaxy**
Port by [@palex0481](https://github.com/palex0481)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/palex0481/GalaxyVision-AVP && cd GalaxyVision-AVP && git checkout 7ade570d09f703603de170a33fce1ab16b81cab9 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/palex0481/GalaxyVision-AVP/blob/7ade570d09f703603de170a33fce1ab16b81cab9/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: Plays in a flat window, or a stereoscopic 3D window \(beta\) drawn once per eye, per the developer. USA disc \(RMGE01 rev 0\) only. A hobby project that isn't in active development. |
| Plays as | 2D, 3D shared space (stereo) |
| Health | OK |
| Scan | Scanned 2026-10-30 · 0 commits since |
| Source (scanned) | [palex0481/GalaxyVision-AVP at 7ade570d09f7](https://github.com/palex0481/GalaxyVision-AVP/tree/7ade570d09f703603de170a33fce1ab16b81cab9) |
| Install guide | [AVP-INSTALL.md at 7ade570d09f7](https://github.com/palex0481/GalaxyVision-AVP/blob/7ade570d09f703603de170a33fce1ab16b81cab9/AVP-INSTALL.md) |
| Repo | [palex0481/GalaxyVision-AVP](https://github.com/palex0481/GalaxyVision-AVP) |
| License | GPL-3.0 |
| Last commit | 2026-10-26 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | mario, platformer, wii, decompilation, recompilation, stereoscopic |

Super Mario Galaxy running natively on Apple Vision Pro: a visionOS app for GalaxyPad, with a flat window or a beta stereoscopic 3D window, a launcher, antialiasing and a side-by-side 3D video recorder. Bring your own disc.

## Credits

- [GalaxyPad](https://github.com/chrissotraidis/galaxypad): Native Super Mario Galaxy for Apple devices, the base of this port
- [MacioGalaxy](https://github.com/classicrob/MacioGalaxy): Native port of the Petari decompilation behind the engine
- [Petari](https://github.com/SMGCommunity/Petari): Super Mario Galaxy decompilation
- [ModernGekko](https://github.com/ExpansionPak/ModernGekko): Runtime integration and game-port tooling

## Upstream projects

- <https://github.com/chrissotraidis/galaxypad>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
