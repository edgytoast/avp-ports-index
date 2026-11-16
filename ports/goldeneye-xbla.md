# GoldenEye 007

**GoldenEye 007** · originally on Other
Port by [@rebelancap](https://github.com/rebelancap)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/GoldenEye-Recomp-ios && cd GoldenEye-Recomp-ios && git checkout 95bcd76b08da5111d6e6f420e19d44e1237fe119 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/GoldenEye-Recomp-ios/blob/95bcd76b08da5111d6e6f420e19d44e1237fe119/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working |
| Plays as | 2D |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/GoldenEye-Recomp-ios at 95bcd76b08da](https://github.com/edgytoast/GoldenEye-Recomp-ios/tree/95bcd76b08da5111d6e6f420e19d44e1237fe119) |
| Install guide | [AVP-INSTALL.md at 95bcd76b08da](https://github.com/edgytoast/GoldenEye-Recomp-ios/blob/95bcd76b08da5111d6e6f420e19d44e1237fe119/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [edgytoast/GoldenEye-Recomp-ios](https://github.com/edgytoast/GoldenEye-Recomp-ios) |
| License | Unlicense |
| Last commit | 2026-11-13 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | goldeneye, fps, first-person, xbox-360, xbla, static-recompilation, rexglue, remaster |

GoldenEye 007 on Apple Vision Pro: Rare's unreleased 2007 Xbox 360 remaster, statically recompiled through GoldenEye-Recomp and the ReXGlue SDK. A 2D window, with a flip between remastered and original N64 graphics. Bring your own copy of the game files. Listed from a copy with an install guide.

## Screenshots

From the port's README at 95bcd76b08da.

<img src="https://raw.githubusercontent.com/edgytoast/GoldenEye-Recomp-ios/95bcd76b08da5111d6e6f420e19d44e1237fe119/docs/screenshots/vision-pro-dam-remaster.jpg" alt="GoldenEye on Apple Vision Pro" width="400">

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
