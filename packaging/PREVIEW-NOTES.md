# Bundled Omarchy Edition — preview 5

The loading screen now shows the approved poster with the subtitle plaque removed, Omarchy lettering and “EDITION” beneath the Command & Conquer title. It is embedded in the bundled installer and keeps its full composition at different screen sizes.

This release includes its own pinned OpenRA engine, .NET runtime, dedicated Omarchy mod and complete 91-entry custom faction roster. It does not install or launch the system OpenRA package. Only Package Conflict is playable.

The custom rules, sprites and names are now mod defaults. Both the build and installer load the actual game rules and check every faction-specific image, palette and sprite asset. A failed check stops installation before switching the active build.

## Install

Download `install-omarchy-edition.sh` and its `.sha256` sidecar, then run in their directory:

```bash
sha256sum --check install-omarchy-edition.sh.sha256
bash install-omarchy-edition.sh
```

Run without sudo. The app launcher is **Command & Conquer: Omarchy Edition**. The window title says **preview 5 (bundled)**. First launch may download the Red Alert terrain and sounds via the content installer; these are not embedded in the bundle. Existing content is reused where available.

To verify or launch the precise installed bundle:

```bash
bash "${XDG_DATA_HOME:-$HOME/.local/share}/command-and-conquer-omarchy/launch.sh" --verify
bash "${XDG_DATA_HOME:-$HOME/.local/share}/command-and-conquer-omarchy/launch.sh"
```

The previous OpenRA installation, maps and saves are left intact. Omarchy keeps its own settings and saves. This is still a preview: a full XPS match and visual review remain required.
