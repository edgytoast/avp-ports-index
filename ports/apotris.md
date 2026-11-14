# Apotris

**Apotris** · originally on Other
Port by [@rebelancap](https://github.com/rebelancap)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/apotris-ios && cd apotris-ios && git checkout 865f50b5223ffc91eb0f864bf3a06043006b4f36 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/apotris-ios/blob/865f50b5223ffc91eb0f864bf3a06043006b4f36/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working |
| Plays as | 2D |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/apotris-ios at 865f50b5223f](https://github.com/edgytoast/apotris-ios/tree/865f50b5223ffc91eb0f864bf3a06043006b4f36) |
| Install guide | [AVP-INSTALL.md at 865f50b5223f](https://github.com/edgytoast/apotris-ios/blob/865f50b5223ffc91eb0f864bf3a06043006b4f36/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [edgytoast/apotris-ios](https://github.com/edgytoast/apotris-ios) |
| License | AGPL-3.0 |
| Last commit | 2026-11-13 |
| visionOS | 2.0 or later |
| Input | game controller, keyboard and mouse |
| Tags | puzzle, block-stacking, free-game, multiplayer, open-source |

Apotris, akouzoukos' free and open block-stacking game, built natively for Apple Vision Pro: a resizable window with left- and right-hand pinch controls, a control ornament, controller and keyboard support, and online Multi Battle. Nothing to supply. Listed from a copy with an install guide.

## Screenshots

From the port's README at 865f50b5223f.

<img src="https://raw.githubusercontent.com/edgytoast/apotris-ios/865f50b5223ffc91eb0f864bf3a06043006b4f36/screenshots/hero.png" alt="Apotris running natively on iPhone — a Marathon game with the score bar on top and a large playfield" width="400">

## Credits

- [rebelancap](https://github.com/rebelancap/apotris-ios): The iOS and visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [akouzoukos](https://apotris.com): Apotris, the game and its engine

## Upstream projects

- <https://github.com/rebelancap/apotris-ios>
- <https://apotris.com>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
