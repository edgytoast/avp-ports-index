# Installing CTRPad on Apple Vision Pro

CTRPad is by [@eurobob](https://github.com/eurobob/ctrpad). This repository is a copy of
theirs with this guide added, so it can be listed in the
[AVP Ports Index](https://github.com/edgytoast/avp-ports-index); [Trevorbilt](https://trevorbilt.com) wrote the guide.
Report problems [on their repository](https://github.com/eurobob/ctrpad/issues), not here.

CTRPad is an unofficial native Apple-platform port of Crash Team Racing, built from [CTR Native](https://github.com/CTR-tools/ctr-native) and the [CTR-ModSDK](https://github.com/CTR-tools/CTR-ModSDK) decompilation. It runs the decompiled game code directly: it isn't an emulator and doesn't need a PlayStation BIOS. This repository adds a visionOS target to [CTRPad](https://github.com/chrissotraidis/ctrpad), as a development preview, with three presentations of the same running game:

| Mode | What you see |
|---|---|
| Window | The original 4:3 picture in a window. It is also the launcher. |
| Portal | A fixed 4:3 opening into the CTR world in your room, in mixed immersion. Your head position and eye separation drive two game cameras, so it behaves as a view into the scene. |
| Cockpit VR | CTR's first-person kart camera in a fully immersive space, with your headset's pose applied to both eye cameras. |

## What you need

- An Apple Silicon Mac with current Xcode, the visionOS SDK and Xcode's command-line tools
- CMake 3.28 or newer, and Ninja (`brew install cmake ninja`)
- A development identity and provisioning profile that cover your chosen bundle identifier and your Apple Vision Pro
- A game controller
- Your own Crash Team Racing disc image: the North American NTSC-U release, `SCUS_944.26`, as a single-track raw MODE2/2352 BIN

## Your game files

CTRPad never downloads or bundles game data. It needs a **single-track raw MODE2/2352 BIN whose data track starts at byte zero**. If your dumping tool made a BIN/CUE pair, pick the `.bin`, not the `.cue`. Cooked 2048-byte ISOs, CUE files, CHD or compressed archives, other regions and incomplete images are rejected, because they lack the raw XA audio and STR video sectors the game needs.

1. Launch CTRPad and select **Choose Disc…** in the launcher window.
2. Pick your BIN in the system file importer. CTRPad copies it into its private Application Support container, validates it, and starts the game.
3. Connect a controller and choose **Portal** or **Cockpit VR**.
4. Use **Exit**, or the system's immersive-space control, to return to the window.

The imported image stays with the app. Deleting the app also deletes that copy and your saves.

## Build from source

There's no prebuilt visionOS app; the releases on the upstream repository are for Mac, iPhone and iPad. From a checkout of this repository, build the device preset, choosing a unique bundle identifier if you need one:

```sh
cmake --preset visionos-device-arm64 \
  -DCTR_NATIVE_VISIONOS_BUNDLE_IDENTIFIER=com.example.yourname.ctrpad.vision
cmake --build --preset visionos-device-arm64
```

The result is an unsigned `build-visionos-device-arm64/CTRPad.app`.

## Install on Apple Vision Pro

Sign it with your own development team, in either of these ways:

- **With the root Xcode project.** Open `CTRPad.xcodeproj`, choose your team under **Signing & Capabilities**, and build or run the `CTRPad` scheme on your Apple Vision Pro. It runs the same `visionos-device-arm64` CMake preset, then lets Xcode sign and install the app. The project ships with the bundle identifier `io.github.chrissotraidis.ctrpad.vision`, so use one unique identifier in both places: the project's signing settings and `CTR_NATIVE_VISIONOS_BUNDLE_IDENTIFIER`.
- **With a generated Xcode project.** Configure the target with the Xcode generator, then select the `ctr_native` target's **Signing & Capabilities** settings and run it on your headset:

  ```sh
  cmake -S . -B build-visionos-xcode -G Xcode \
    -DCMAKE_SYSTEM_NAME=visionOS \
    -DCMAKE_OSX_SYSROOT=xros \
    -DCMAKE_OSX_ARCHITECTURES=arm64 \
    -DCMAKE_OSX_DEPLOYMENT_TARGET=2.0 \
    -DCTR_NATIVE_RENDERER_GLES=OFF
  open build-visionos-xcode/CTR-Native.xcodeproj
  ```

## Notes

- The launcher window also has **Internal resolution** and **Stereo depth** controls.
- Development-preview limits: stereo is single-player, and split-screen stays in the normal window. The Metal backend doesn't yet match the OpenGL renderer for every effect, so heat haze, screen copies and video-style effects can look different. The README notes that physical-headset acceptance is still required.
- CTRPad is an unofficial community project, not affiliated with or endorsed by Sony, PlayStation, Naughty Dog, Activision, CTR Native, or the CTR-ModSDK maintainers. Crash Team Racing and related names, characters, imagery and marks belong to their respective owners.
