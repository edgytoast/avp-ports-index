# Luigi's Mansion VR

**Luigi's Mansion** · originally on GameCube (2001)
Port by Trevorbilt ([@edgytoast](https://github.com/edgytoast))

Start with this command, which gets exactly the code that was scanned:

```
git clone https://github.com/edgytoast/luigismansion-visionos && cd luigismansion-visionos && git checkout f61bb7bb9f6f5b1fd5a6198b5c1486c045e5afde && git submodule update --init --recursive
```

Then follow the [install guide](https://github.com/edgytoast/luigismansion-visionos/blob/f61bb7bb9f6f5b1fd5a6198b5c1486c045e5afde/AVP-INSTALL.md) from its build steps. Skip only its step that clones or downloads this repo, which would fetch newer code that may not have been scanned; keep every other step, including dependency downloads.

| | |
| --- | --- |
| Trust | Working · Curator's own port |
| Status | Working: Plays with a gamepad \(the only input supported\) as a world-locked diorama in your room \(Full\) and as a model on your table beside other apps, both played on Apple Vision Pro. USA disc \(GLME01\) only. |
| Plays as | 3D shared space, 3D tabletop |
| Health | OK |
| Scan | Scanned 2026-10-31 · 0 commits since |
| Source (scanned) | [edgytoast/luigismansion-visionos at f61bb7bb9f6f](https://github.com/edgytoast/luigismansion-visionos/tree/f61bb7bb9f6f5b1fd5a6198b5c1486c045e5afde) |
| Install guide | [AVP-INSTALL.md at f61bb7bb9f6f](https://github.com/edgytoast/luigismansion-visionos/blob/f61bb7bb9f6f5b1fd5a6198b5c1486c045e5afde/AVP-INSTALL.md) |
| Repo | [edgytoast/luigismansion-visionos](https://github.com/edgytoast/luigismansion-visionos) |
| Developer site | <https://trevorbilt.com> |
| License | No license stated |
| Last commit | 2026-10-31 |
| visionOS | 26.0 or later |
| Input | game controller |
| Tags | luigis-mansion, vr, diorama, tabletop, gamecube, recompilation |

Luigi's Mansion as a haunted diorama on Apple Vision Pro: the mansion stands in your room as a miniature you can walk around, or sits on your table beside your other apps. A native visionOS port of u/sonarix's Luigi's Mansion VR mod and rob646464's recompilation. Bring your own disc.

## Credits

- [Trevorbilt](https://trevorbilt.com): visionOS port
- [u/sonarix](https://www.reddit.com/user/sonarix): Luigi's Mansion VR, the VR mod this port is built on
- [u/sonarix](https://www.reddit.com/r/virtualreality/comments/1xg3kvj/): Luigi's Mansion VR build 150's source, released and handed on
- [rob646464](https://github.com/rob646464/luigis-mansion-recompiled): Luigi's Mansion Recompiled, the native recompilation
- [SomeJakeGuy](https://github.com/SomeJakeGuy/lm-decomp): lm-decomp, the decompilation that drives the recompiler
- [encounter](https://github.com/encounter/aurora): Aurora, the GameCube graphics and system layer
- [Twilit Realm](https://github.com/TwilitRealm/dusklight): Dusklight, source of the JSystem code
- [iChris4](https://github.com/iChris4/Wiicompiled_VR): WiiCompiled Vision, source of the visionOS OpenXR provider

## Upstream projects

- <https://github.com/rob646464/luigis-mansion-recompiled>
- <https://www.reddit.com/r/virtualreality/comments/1xg3kvj/>
- <https://github.com/SomeJakeGuy/lm-decomp>
- <https://github.com/encounter/aurora>

---

This index only links to the developer's own repository. Automated checks and an AI safety check can miss things, and they can't confirm the port runs on Apple Vision Pro. Building runs the port's build scripts on your Mac with your permissions. You must own the game and supply your own legally obtained game files. [Report a problem](https://github.com/edgytoast/avp-ports-index/issues/new?template=report-entry.yml).

Curated by trevorbilt · [trevorbilt.com](https://trevorbilt.com)
