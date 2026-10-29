# V

**Grand Theft Auto V**
Port by Zach Schwendiman ([@zschwendi](https://github.com/zschwendi))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/zschwendi/SantosVision && cd SantosVision && git checkout 20fb8e39e18788a71469a2a63c2889ae12f3a0d8 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/zschwendi/SantosVision/blob/20fb8e39e18788a71469a2a63c2889ae12f3a0d8/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Partially working |
| Status | Partially working: Windowed play is stable per the developer. Experimental third-person immersion has remaining image-quality, depth-edge, flicker and performance bugs. |
| Plays as | 2D, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-10-29 · 0 commits since |
| Source (scanned) | [zschwendi/SantosVision at 20fb8e39e187](https://github.com/zschwendi/SantosVision/tree/20fb8e39e18788a71469a2a63c2889ae12f3a0d8) |
| Install guide | [AVP-INSTALL.md at 20fb8e39e187](https://github.com/zschwendi/SantosVision/blob/20fb8e39e18788a71469a2a63c2889ae12f3a0d8/AVP-INSTALL.md) |
| Repo | [zschwendi/SantosVision](https://github.com/zschwendi/SantosVision) |
| License | GPL-3.0 |
| Last commit | 2026-10-29 |
| visionOS | 26.0 or later |
| Input | game controller |

Native Apple-platform GTA V port built on Muguet, with local ahead-of-time compiled game code, a game window and experimental head-tracked third-person immersion.

## Screenshots

From the port's README at 20fb8e39e187.

<img src="https://raw.githubusercontent.com/zschwendi/SantosVision/20fb8e39e18788a71469a2a63c2889ae12f3a0d8/assets/branding/spatial-v-front-glass-master-v28.png" alt="V — green Vision Pro front glass reflecting a Los Santos sunset" width="400">

## Credits

- [Muguet](https://github.com/c22dev/muguet): Native WASM runtime foundation

## Upstream projects

- <https://github.com/c22dev/muguet>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
