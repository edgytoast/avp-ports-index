# GoldenEye 007

**GoldenEye 007** · originally on Other
Port by [@rebelancap](https://github.com/rebelancap)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/GoldenEye-Recomp-ios && cd GoldenEye-Recomp-ios && git checkout c9de4192319ea5569817c2c29c507d8c02d626dc && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/GoldenEye-Recomp-ios/blob/c9de4192319ea5569817c2c29c507d8c02d626dc/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working |
| Plays as | 2D |
| Health | OK |
| Scan | Scanned 2026-11-25 · 0 commits since |
| Source (scanned) | [edgytoast/GoldenEye-Recomp-ios at c9de4192319e](https://github.com/edgytoast/GoldenEye-Recomp-ios/tree/c9de4192319ea5569817c2c29c507d8c02d626dc) |
| Install guide | [AVP-INSTALL.md at c9de4192319e](https://github.com/edgytoast/GoldenEye-Recomp-ios/blob/c9de4192319ea5569817c2c29c507d8c02d626dc/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [edgytoast/GoldenEye-Recomp-ios](https://github.com/edgytoast/GoldenEye-Recomp-ios) |
| License | Unlicense |
| Last commit | 2026-11-24 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | goldeneye, fps, first-person, xbox-360, xbla, static-recompilation, rexglue, remaster |

GoldenEye 007 on Apple Vision Pro: Rare's unreleased 2007 Xbox 360 remaster, statically recompiled through GoldenEye-Recomp and the ReXGlue SDK. A 2D window, with a flip between remastered and original N64 graphics. Bring your own copy of the game files. Listed from a copy with an install guide.

## Screenshots

From the port's README at c9de4192319e.

<img src="https://raw.githubusercontent.com/edgytoast/GoldenEye-Recomp-ios/c9de4192319ea5569817c2c29c507d8c02d626dc/docs/screenshots/vision-pro-dam-remaster.jpg" alt="GoldenEye on Apple Vision Pro" width="400">

## Credits

- [rebelancap](https://github.com/rebelancap/GoldenEye-Recomp-ios): The iOS and visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [SunJaycy](https://github.com/SunJaycy/GoldenEye-Recomp): GoldenEye-Recomp, the PC recompilation this port is built on
- [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk): PowerPC to C\+\+ recompiler and Xbox 360 runtime
- [Xenia](https://xenia.jp): GPU, kernel/XAM and XMA audio work that ReXGlue's runtime derives from
- BeanTools Community Edition: Door, portal, near-clip and audio fixes, and 3D-positioned sound
- [MoltenVK](https://github.com/KhronosGroup/MoltenVK): Vulkan on Metal
- Rare / Nintendo / MGM / Danjaq: Original game

## Upstream projects

- <https://github.com/rebelancap/GoldenEye-Recomp-ios>
- <https://github.com/SunJaycy/GoldenEye-Recomp>
- <https://github.com/rexglue/rexglue-sdk>
- <https://github.com/SunJaycy/GoldenEye-Recomp-rexglue>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
