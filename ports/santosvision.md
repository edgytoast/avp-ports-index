# V

**Grand Theft Auto V**
Port by Zach Schwendiman ([@zschwendi](https://github.com/zschwendi))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/zschwendi/SantosVision && cd SantosVision && git checkout 71b376cfb8f066d1d6df9f4a53495974ecdab2dd && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/zschwendi/SantosVision/blob/71b376cfb8f066d1d6df9f4a53495974ecdab2dd/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Partially working |
| Status | Partially working: Windowed play is stable per the developer. Experimental third-person immersion has remaining image-quality, depth-edge, flicker and performance bugs. |
| Plays as | 2D, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-10-30 · 0 commits since |
| Source (scanned) | [zschwendi/SantosVision at 71b376cfb8f0](https://github.com/zschwendi/SantosVision/tree/71b376cfb8f066d1d6df9f4a53495974ecdab2dd) |
| Install guide | [AVP-INSTALL.md at 71b376cfb8f0](https://github.com/zschwendi/SantosVision/blob/71b376cfb8f066d1d6df9f4a53495974ecdab2dd/AVP-INSTALL.md) |
| Repo | [zschwendi/SantosVision](https://github.com/zschwendi/SantosVision) |
| License | GPL-3.0 |
| Last commit | 2026-10-30 |
| visionOS | 26.0 or later |
| Input | game controller |

Native Apple-platform GTA V port built on Muguet, with local ahead-of-time compiled game code, a game window and experimental head-tracked third-person immersion.

## Screenshots

From the port's README at 2a09ecb2b643.

<img src="https://raw.githubusercontent.com/zschwendi/SantosVision/2a09ecb2b643299297e269ed8cf997eaca449062/assets/branding/spatial-v-front-glass-master-v28.png" alt="V — green Vision Pro front glass reflecting a Los Santos sunset" width="400">

## Credits

- [Muguet](https://github.com/c22dev/muguet): Native WASM runtime foundation

## Upstream projects

- <https://github.com/c22dev/muguet>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
