# Omarchy Edition — v0.1.0

Package Conflict now has three fixed players: green Omarchy, pink **Reboot Required**, and purple **The Walled Orchard**. The two AI opponents share the original custom closed-platform army, but have distinct names, colours and original faction flags. The unused combined Walled Garden flag remains available for generic or random faction UI. Vendor-specific names in the army roster have been replaced with original jokes.

The map adds a third start and two ore mines, keeping the resource field rotationally symmetric. The lobby shows all three factions and allows the third slot to be filled with an AI. Omarchy's radar, HUD, command bar, menu, loading screen and installer artwork use the themed assets. The bundled engine and .NET runtime remain pinned to OpenRA `release-20250330`.

## Install

Download `install-omarchy-edition.sh` and its `.sha256` sidecar together, then run:

```bash
sha256sum --check install-omarchy-edition.sh.sha256
bash install-omarchy-edition.sh
```

Run as your normal user, without sudo. The app launcher is **Command & Conquer: Omarchy Edition**. The window title says **v0.1.0 (bundled)**. First launch may download Red Alert terrain and sounds; the bundle does not contain that content. Existing downloads can be reused.

In the Package Conflict lobby, take the green Omarchy slot and assign an AI to both the pink and purple slots. To check the installed bundle or launch it again:

```bash
bash "${XDG_DATA_HOME:-$HOME/.local/share}/command-and-conquer-omarchy/launch.sh" --verify
bash "${XDG_DATA_HOME:-$HOME/.local/share}/command-and-conquer-omarchy/launch.sh"
```

The installer checks the payload digest and all 136 faction image resolutions before activating the new build. An existing bundled installation is retained if verification fails. `bash install-omarchy-edition.sh --uninstall` removes the bundle and launcher but preserves content, settings and saves. It leaves any system OpenRA installation untouched.

## Verification scope

The skirmish tests cover economy, routes, map packaging and assets. The CI workflow builds the pinned OpenRA engine and Omarchy mod, checks whole-mod YAML and roster images, runs the bundled client under virtual X11, installs the generated artifact in a clean home and verifies its digest. A live local lobby was exercised with both AI slots filled and a three-player match started. Tom also played Preview 8 on his Omarchy machine and reports that it plays well; a complete match and wider hardware coverage are not documented.

Release assets and checksum must come from the successful CI run for the v0.1.0 source commit.
