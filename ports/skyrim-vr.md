# Skyrim VR on Apple Vision Pro

**The Elder Scrolls V: Skyrim VR** · originally on PC (2017)
Port by [@gseddon](https://github.com/gseddon)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/gseddon/Skyrim-VR-Vision-Pro && cd Skyrim-VR-Vision-Pro && git checkout c036b4e4b3580c5ee5442540f0d14b912153c584 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/gseddon/Skyrim-VR-Vision-Pro/blob/c036b4e4b3580c5ee5442540f0d14b912153c584/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: The developer reports it plays well on the headset: about 35 fps redrawn at 100 Hz, Sense controllers, sound, menus, saves and SKSE mods. Connect both controllers before pressing Start. Needs a paid Apple Developer account. Not tested by the curator. |
| Plays as | 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-11-15 · 41 commits since |
| Source (scanned) | [gseddon/Skyrim-VR-Vision-Pro at c036b4e4b358](https://github.com/gseddon/Skyrim-VR-Vision-Pro/tree/c036b4e4b3580c5ee5442540f0d14b912153c584) |
| Install guide | [AVP-INSTALL.md at c036b4e4b358](https://github.com/gseddon/Skyrim-VR-Vision-Pro/blob/c036b4e4b3580c5ee5442540f0d14b912153c584/AVP-INSTALL.md) |
| Repo | [gseddon/Skyrim-VR-Vision-Pro](https://github.com/gseddon/Skyrim-VR-Vision-Pro) |
| License | MIT |
| Last commit | 2026-11-15 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | skyrim, skyrim-vr, vr, 6dof, rpg, open-world, steam, aot-recompilation |

The Windows PC version of Skyrim VR on Apple Vision Pro itself, with no PC or streaming: your Mac recompiles your own Steam copy for Apple silicon once, and the headset plays it in full VR with PS VR2 Sense controllers and physics mods.

## Credits

- [gseddon](https://github.com/gseddon/Skyrim-VR-Vision-Pro): The visionOS port
- [Ag3497120](https://github.com/Ag3497120/VeRantyx): VeRantyx, the x86-64 to ARM64 recompiler and Windows layer it builds on
- [Supreeeme](https://github.com/Supreeeme/xrizer): xrizer, OpenVR on OpenXR
- [shinyquagsire23](https://github.com/shinyquagsire23/Klepton): Klepton, the source of its visionOS OpenXR provider
- Bethesda Softworks: Original game

## Upstream projects

- <https://github.com/Ag3497120/VeRantyx>
- <https://github.com/Supreeeme/xrizer>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
