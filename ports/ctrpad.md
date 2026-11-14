# CTRPad for Vision Pro

**Crash Team Racing** · originally on PlayStation (1999)
Port by [@eurobob](https://github.com/eurobob)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/ctrpad && cd ctrpad && git checkout df1d0671ed8d540b695113f1cc28e9fb26e570e9 && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/ctrpad/blob/df1d0671ed8d540b695113f1cc28e9fb26e570e9/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Partially working |
| Status | Partially working: The README calls the Apple Vision Pro target a development preview: portal and cockpit stereo are implemented, and physical-headset acceptance is still required. |
| Plays as | 2D, 3D immersive, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-11-14 · 0 commits since |
| Source (scanned) | [edgytoast/ctrpad at df1d0671ed8d](https://github.com/edgytoast/ctrpad/tree/df1d0671ed8d540b695113f1cc28e9fb26e570e9) |
| Install guide | [AVP-INSTALL.md at df1d0671ed8d](https://github.com/edgytoast/ctrpad/blob/df1d0671ed8d540b695113f1cc28e9fb26e570e9/AVP-INSTALL.md) |
| Repo | [edgytoast/ctrpad](https://github.com/edgytoast/ctrpad) |
| License | Custom license |
| Last commit | 2026-11-13 |
| Input | game controller |
| Tags | racing, kart, ps1, crash, decompilation, stereo-3d, vr |

Crash Team Racing built from the CTR-ModSDK decompilation, through CTR Native and CTRPad, with a visionOS preview: a 4:3 window, a stereo Portal into the game in your room, or Cockpit VR from the driver's seat. Bring your own NTSC-U disc image. Listed from a copy with an install guide.

## Screenshots

From the port's README at df1d0671ed8d.

<img src="https://raw.githubusercontent.com/edgytoast/ctrpad/df1d0671ed8d540b695113f1cc28e9fb26e570e9/docs/design/ctrpad-app-icon-master.png" alt="CTRPad app icon" width="400">
<img src="https://raw.githubusercontent.com/edgytoast/ctrpad/df1d0671ed8d540b695113f1cc28e9fb26e570e9/docs/readme/ctrpad-crash-cove-gameplay.png" alt="CTRPad running Crash Cove on iPad with the touch controller" width="400">
<img src="https://raw.githubusercontent.com/edgytoast/ctrpad/df1d0671ed8d540b695113f1cc28e9fb26e570e9/docs/readme/ctrpad-title-screen.png" alt="CTRPad title screen on iPad" width="400">

## Credits

- [eurobob](https://github.com/eurobob/ctrpad): The Apple Vision Pro port
- [Trevorbilt](https://trevorbilt.com): Install guide and AVP Ports Index listing
- [chrissotraidis](https://github.com/chrissotraidis/ctrpad): CTRPad, the Apple-platform port this visionOS work is built on
- [CTR Native](https://github.com/CTR-tools/ctr-native): Native PC port and platform architecture
- [CTR-ModSDK](https://github.com/CTR-tools/CTR-ModSDK): Crash Team Racing decompilation
- [PsyCross](https://github.com/OpenDriver2/PsyCross): Portions of the native platform layer and PsyQ facade
- [SDL3](https://github.com/libsdl-org/SDL): Multimedia and controller layer
- Naughty Dog / Sony Computer Entertainment: Original game

## Upstream projects

- <https://github.com/eurobob/ctrpad>
- <https://github.com/chrissotraidis/ctrpad>
- <https://github.com/CTR-tools/ctr-native>
- <https://github.com/CTR-tools/CTR-ModSDK>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
