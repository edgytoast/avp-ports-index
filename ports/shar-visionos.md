# SHAR VR

**The Simpsons: Hit &amp; Run** · originally on PC (2003)
Port by Trevorbilt ([@edgytoast](https://github.com/edgytoast))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/shar-visionos && cd shar-visionos && git checkout 218b0cd2baa279d32fb6418ef19fb52c466e71e7 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/shar-visionos/blob/218b0cd2baa279d32fb6418ef19fb52c466e71e7/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working · Curator's own port |
| Status | Working: Plays in the Full, Progressive and Window views, with PS VR2 Sense controllers, a gamepad or bare hands. Built and played on Apple Vision Pro. |
| Plays as | 3D shared space, 6DoF immersive, 6DoF progressive |
| Health | OK |
| Scan | Scanned 2026-10-05 · 0 commits since |
| Source (scanned) | [edgytoast/shar-visionos at 218b0cd2baa2](https://github.com/edgytoast/shar-visionos/tree/218b0cd2baa279d32fb6418ef19fb52c466e71e7) |
| Install guide | [AVP-INSTALL.md at 218b0cd2baa2](https://github.com/edgytoast/shar-visionos/blob/218b0cd2baa279d32fb6418ef19fb52c466e71e7/AVP-INSTALL.md) |
| Repo | [edgytoast/shar-visionos](https://github.com/edgytoast/shar-visionos) |
| Developer site | <https://trevorbilt.com> |
| License | MIT |
| Last commit | 2026-10-04 |
| visionOS | 26.0 or later |
| Input | game controller, hand tracking |
| Tags | vr, 6dof, driving, open-world, source-port |

The Simpsons: Hit &amp; Run in six degrees of freedom on Apple Vision Pro. Walk Springfield with a Sense controller in each hand, drive from the driver's seat, or play it as a 3D window beside your other apps. A native visionOS port of kote2345's Hit &amp; Run VR mod.

## Credits

- [Trevorbilt](https://trevorbilt.com): visionOS port
- [Radical Entertainment](https://en.wikipedia.org/wiki/Radical_Entertainment): Original game \(2003\)
- [Svxy](https://github.com/Svxy/The-Simpsons-Hit-and-Run): The original source code, on GitHub
- [ZenoArrows](https://github.com/ZenoArrows/The-Simpsons-Hit-and-Run): Source port \(Nintendo Switch, PS Vita\)
- [Carlox33](https://github.com/Carlox33/The-Simpsons-Hit-and-Run-Android): Android port
- [kote2345](https://github.com/kote2345/The-Simpsons-Hit-and-Run-VR): VR mod \(Meta Quest 3, PC VR\)

## Upstream projects

- <https://github.com/kote2345/The-Simpsons-Hit-and-Run-VR>
- <https://github.com/Carlox33/The-Simpsons-Hit-and-Run-Android>
- <https://github.com/ZenoArrows/The-Simpsons-Hit-and-Run>

---

This index only links to the developer's own repository. Automated checks and an AI security review can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
