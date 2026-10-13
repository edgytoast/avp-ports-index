# Glovebox

**Half-Life: Alyx** · originally on PC (2020)
Port by [@glovebox-vr](https://github.com/glovebox-vr)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/glovebox && cd glovebox && git checkout 77766c24038ba874f67af23239fc0693bdcd7f83 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/glovebox/blob/77766c24038ba874f67af23239fc0693bdcd7f83/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working |
| Status | Working: Runs on the headset itself; the curator installed it from scratch with this copy's guide \(Steam save, controllers, frame rate fine\). Known issues: close objects can look doubled as you move \(45 fps shown twice\), busy scenes can slow down, no left-handed or one-controller play. |
| Plays as | 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-10-12 · commits since unknown |
| Source (scanned) | [edgytoast/glovebox at 77766c24038b](https://github.com/edgytoast/glovebox/tree/77766c24038ba874f67af23239fc0693bdcd7f83) |
| Install guide | [AVP-INSTALL.md at 77766c24038b](https://github.com/edgytoast/glovebox/blob/77766c24038ba874f67af23239fc0693bdcd7f83/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [edgytoast/glovebox](https://github.com/edgytoast/glovebox) |
| License | Custom license |
| Last commit | 2026-10-12 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | half-life, half-life-alyx, vr, 6dof, first-person, source-2, klepton, steam |

Half-Life: Alyx on Apple Vision Pro itself, with no PC or streaming: Klepton converts the game's ARM64 Linux build into signed visionOS code on your Mac. Install it with the Glovebox Mac app or build it from source, with your own Steam copy. Listed from a copy that adds only the install guide.

## Screenshots

From the port's README at 77766c24038b.

<img src="https://raw.githubusercontent.com/edgytoast/glovebox/77766c24038ba874f67af23239fc0693bdcd7f83/installer/App/Glovebox/Assets.xcassets/AppIcon.appiconset/icon_512x512.png" alt="Glovebox" width="400">

## Credits

- [Glovebox contributors](https://github.com/glovebox-vr/glovebox): Glovebox, the visionOS port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [shinyquagsire23](https://github.com/shinyquagsire23/Klepton): Klepton, the runtime Glovebox builds on
- [Khronos Group](https://github.com/KhronosGroup/MoltenVK): MoltenVK, Vulkan on Metal
- [Valve](https://github.com/ValveSoftware/Fossilize): Fossilize, ahead-of-time pipeline building
- [SDL](https://github.com/libsdl-org/SDL): SDL 3 and sdl2-compat
- [LuaJIT](https://github.com/LuaJIT/LuaJIT): The game's Lua scripting, with the JIT off
- [Debian](https://www.debian.org): arm64 runtime libraries, downloaded at install time
- Valve: Original game

## Upstream projects

- <https://github.com/glovebox-vr/glovebox>
- <https://github.com/shinyquagsire23/Klepton>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
