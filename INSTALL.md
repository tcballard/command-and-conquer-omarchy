# Installing Red Alert: Omarchy Edition

Target: stock OpenRA **release-20250330** (the version Arch Linux ships as
`openra 20250330-5`; `pacman -S openra`). No engine changes, no extra mods.
You need the Red Alert game assets installed once through OpenRA's own
content prompt (it downloads the freeware assets on first launch).

## 1. Copy the map into the user maps directory

OpenRA reads user maps from `<SupportDir>/maps/<mod>/<version>/`. This comes
from `mods/ra/mod.yaml`:

```
MapFolders:
	ra|maps: System
	~^SupportDir|maps/ra/{DEV_VERSION}: User
```

The Arch package replaces `{DEV_VERSION}` with `release-20250330`
(`make version VERSION="release-${pkgver}"` in the PKGBUILD), and on Linux the
support directory is `$XDG_CONFIG_HOME/openra`, i.e. `~/.config/openra` by
default (`OpenRA.Game/Platform.cs`). If you still have a legacy `~/.openra`
directory from an old install, OpenRA keeps using that one instead.

```sh
mkdir -p ~/.config/openra/maps/ra/release-20250330
cp omarchy-edition.oramap ~/.config/openra/maps/ra/release-20250330/
```

For a different OpenRA version, substitute the version string shown in the
game's main menu (bottom right) for `release-20250330`.

## 2. Launch

```sh
openra-ra
```

(`openra-ra` is the launcher the Arch package installs. Any other install:
`launch-game.sh Game.Mod=ra` from the engine directory.)

## 3. Select the mission

Main menu -> **Singleplayer** -> **Missions**. The map declares
`Visibility: MissionSelector`, so it is listed by the mission browser in a
group called **Missions** underneath the stock Allied/Soviet campaigns
(`MissionBrowserLogic` puts every loose mission-visibility map there). Pick
**Red Alert: Omarchy Edition**, read the briefing, press Play.

The map is deliberately not visible in Skirmish / Custom Maps: it is a
scripted single-player mission with a locked faction and colour.

## Optional: verify the file before launching

If you have the engine source or an install that ships the utility:

```sh
./utility.sh ra --check-yaml /path/to/omarchy-edition.oramap
```

It should print only `Testing map: Red Alert: Omarchy Edition` and exit 0.
On Arch the engine lives under `/usr/lib/openra`; the equivalent is
`dotnet /usr/lib/openra/bin/OpenRA.Utility.dll ra --check-yaml <map>` run
from that directory (path may differ if the package layout changes).

## Uninstall

Delete the file from the maps directory. Nothing else is touched.
