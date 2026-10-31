# Dark Eco

**Jak and Daxter**
Port by Zach Schwendiman ([@zschwendi](https://github.com/zschwendi))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/zschwendi/dark-eco && cd dark-eco && git checkout c89b91c8c9fe1b95dc4e35e5a3ec4acb965dcf08 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/zschwendi/dark-eco/blob/c89b91c8c9fe1b95dc4e35e5a3ec4acb965dcf08/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Partially working |
| Status | Partially working: Windowed Jak and Daxter is stable per the developer. This public v2.0 source exposes 2D Comfort mode. The separate experimental immersive build has remaining bugs and is not included in this entry. |
| Plays as | 2D |
| Health | OK |
| Scan | Scanned 2026-10-30 · 4 commits since |
| Source (scanned) | [zschwendi/dark-eco at c89b91c8c9fe](https://github.com/zschwendi/dark-eco/tree/c89b91c8c9fe1b95dc4e35e5a3ec4acb965dcf08) |
| Install guide | [AVP-INSTALL.md at c89b91c8c9fe](https://github.com/zschwendi/dark-eco/blob/c89b91c8c9fe1b95dc4e35e5a3ec4acb965dcf08/AVP-INSTALL.md) |
| Repo | [zschwendi/dark-eco](https://github.com/zschwendi/dark-eco) |
| Branch | `v2.0` |
| License | No license stated |
| Last commit | 2026-10-30 |
| visionOS | 26.5 or later |
| Input | game controller |

Native Apple OpenGOAL port with a Dark Eco launcher, on-device import of user-supplied Jak and Daxter data, Metal graphics and controller support. This entry covers the public windowed Vision Pro build.

## Screenshots

From the port's README at c89b91c8c9fe.

<img src="https://raw.githubusercontent.com/zschwendi/dark-eco/c89b91c8c9fe1b95dc4e35e5a3ec4acb965dcf08/docs/media/dark-eco-vision-pro.gif" alt="Jak 1 immersive gameplay recorded by Zach on Apple Vision Pro" width="400">

## Credits

- [OpenGOAL](https://github.com/open-goal/jak-project): GOAL language tools, reconstructed game code and runtime
- [jak-pad](https://github.com/zschwendi/jak-pad): Pinned Apple-platform OpenGOAL engine fork

## Upstream projects

- <https://github.com/open-goal/jak-project>
- <https://github.com/zschwendi/jak-pad>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
