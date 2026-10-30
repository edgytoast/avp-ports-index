# VISR

**Halo: Combat Evolved** · originally on Xbox (2001)
Port by [@steverice](https://github.com/steverice)

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/steverice/visr && cd visr && git checkout 154e4f87d458c40a0305fcf0daa987d73b9ffe3d && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/steverice/visr/blob/154e4f87d458c40a0305fcf0daa987d73b9ffe3d/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Developer-verified |
| Status | Developer-verified |
| Plays as | 2D, 3D immersive, 6DoF immersive |
| Health | OK |
| Scan | Scanned 2026-10-29 · 55 commits since |
| Source (scanned) | [steverice/visr at 154e4f87d458](https://github.com/steverice/visr/tree/154e4f87d458c40a0305fcf0daa987d73b9ffe3d) |
| Install guide | [AVP-INSTALL.md at 154e4f87d458](https://github.com/steverice/visr/blob/154e4f87d458c40a0305fcf0daa987d73b9ffe3d/AVP-INSTALL.md) |
| Prebuilt app | The developer publishes an app you can sideload; see their repo. The index's safety check covers the source code, not the app. |
| Repo | [steverice/visr](https://github.com/steverice/visr) |
| License | Apache-2.0 |
| Last commit | 2026-10-30 |
| visionOS | 2.0 or later |
| Input | game controller |
| Tags | fps, sci-fi, metal, vr, multiplayer |

Native Metal port of Halo: Combat Evolved for Apple Vision Pro and other Apple devices. Head-tracked stereo, foveated rendering, a 3D theater screen and PlayStation VR2 Sense controller aiming. Bring your own disc image of the original Xbox release.

## Screenshots

From the port's README at 154e4f87d458.

<img src="https://raw.githubusercontent.com/steverice/visr/154e4f87d458c40a0305fcf0daa987d73b9ffe3d/docs/images/readme-banner.png" alt="VISR: the app icon, a helmet with a gold visor, beside the VISR wordmark on a dark teal grid" width="400">

## Credits

- [punpckhdq](https://github.com/punpckhdq/halo): Decompilation
- [bnunu](https://github.com/bnunu/halo-1): Decompilation fork
- [OpenCE](https://github.com/OpenCommunityEdition/OpenCE): Native desktop ports
- [NicholasDominici](https://github.com/NicholasDominici/halo-ce-ios): Original iOS port

## Upstream projects

- <https://github.com/punpckhdq/halo>
- <https://github.com/bnunu/halo-1>
- <https://github.com/OpenCommunityEdition/OpenCE>
- <https://github.com/NicholasDominici/halo-ce-ios>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
