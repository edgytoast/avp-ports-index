# MacNativeGames

**The Legend of Zelda: Tears of the Kingdom** · originally on Other (2023)
Port by [@ly05010419](https://github.com/ly05010419)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/ly05010419/MacNativeGames && cd MacNativeGames && git checkout 31aa41b4101a413f69113985120ba095e1c9586f && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/ly05010419/MacNativeGames/blob/31aa41b4101a413f69113985120ba095e1c9586f/docs/install.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Partially working |
| Status | Partially working: Early Vision Pro support: Tears of the Kingdom in a 16:9 window with a controller, not VR. In the guide, read What you need and Build the app first; Xcode, Apple ID and 7-day signing are under iPhone and iPad. Not tested by the curator. |
| Plays as | 2D |
| Health | OK |
| Scan | Reviewed by the curator 2026-11-16 · 314 commits since |
| Source (scanned) | [ly05010419/MacNativeGames at 31aa41b4101a](https://github.com/ly05010419/MacNativeGames/tree/31aa41b4101a413f69113985120ba095e1c9586f) |
| Install guide | [docs/install.md at 31aa41b4101a](https://github.com/ly05010419/MacNativeGames/blob/31aa41b4101a413f69113985120ba095e1c9586f/docs/install.md) |
| Repo | [ly05010419/MacNativeGames](https://github.com/ly05010419/MacNativeGames) |
| License | MIT |
| Last commit | 2026-11-24 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | zelda, tears-of-the-kingdom, switch, window, metal, native-port |

Tears of the Kingdom in a window on Apple Vision Pro, with the game's own ARM64 code running directly on Apple silicon and its graphics rebuilt on Metal. Not an emulator. Needs your own game files and keys.

## Credits

- [ly05010419](https://github.com/ly05010419/MacNativeGames): MacNativeGames, including the visionOS build
- Ryujinx: The shader translator and a reference for system services
- Nintendo: Original game

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
