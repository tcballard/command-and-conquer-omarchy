# Omarchy Skirmish

**Package Conflict** is a two-player land skirmish for OpenRA Red Alert
`release-20250330`: Omarchians versus **The Walled Garden**.
Build a base, harvest, train DHH and launch the coding agents. Normal
skirmish victory rules apply. There are no missions, waves or deadlines.

## Play on Omarchy

Download **[install-omarchy-edition.sh](https://github.com/tcballard/command-and-conquer-omarchy/releases/download/v0.0.1-preview.2/install-omarchy-edition.sh)** from the preview release,
then run it as your normal user:

```sh
bash ~/Downloads/install-omarchy-edition.sh
```

This single file includes the compiled map and all custom artwork. It installs
OpenRA through pacman if missing, checks for version `20250330`, installs the
map for your user and adds **Command & Conquer: Omarchy Edition** to the app
menu. No Git, Python or source checkout is needed. Internet and sudo are only
needed for installing the OpenRA package; OpenRA may also download its Red
Alert content on first launch. Complete that content setup when prompted.
The installer does not bundle the original game files or automatically start
a match. It opens the dedicated Omarchy lobby directly. There is one playable
map and no map-change button, campaign browser, multiplayer browser or editor
entry point. Leaving the lobby shows Skirmish, Settings and Quit. The standard
OpenRA launcher remains available separately.

Run the same installer again to update its map. Use `--no-launch` to install
without opening the game. A different OpenRA release is rejected without
silently downgrading it. This development installer targets x86_64 Omarchy /
Arch; its portable lifecycle tests pass, but installation and desktop launch
on an actual XPS remain untested.

To remove it:

```sh
bash ~/Downloads/install-omarchy-edition.sh --uninstall
```

Or run `bash "${XDG_DATA_HOME:-$HOME/.local/share}/command-and-conquer-omarchy/uninstall.sh"`.
Removal keeps OpenRA, downloaded content, saves and other maps. If this
installer replaced an earlier Package Conflict map, that copy is restored.
If you have edited the installed map, removal stops and preserves it; move
that file aside before retrying. Both XDG and legacy `~/.openra` paths work. The dedicated mod keeps its own
settings, saves and replays under the app's `support` directory and shares
only the existing Red Alert content directory. Uninstall preserves that
support directory. This is a focused launcher, not a restriction on what
you can do with a separately launched OpenRA or edited source code.

### Build from source

```sh
sudo pacman -S --needed python python-pillow
python tools/build_skirmish.py
# Requires the pinned OpenRA source and its build toolchain:
git clone --branch release-20250330 --depth 1 https://github.com/OpenRA/OpenRA.git engine
(cd engine && dotnet build -c Release -p:TargetPlatform=unix-generic)
dotnet build mod/OpenRA.Mods.Omarchy -c Release -p:EngineDir="$PWD/engine/bin" -o build/menu
python tools/build_omarchy_mod.py engine build/menu/OpenRA.Mods.Omarchy.dll
python tools/build_installer.py
bash build/install-omarchy-edition.sh
```

The build also writes a SHA-256 sidecar. Both outputs are deterministic for
the same map and installer source. The checksum detects download damage;
it is not a publisher signature. The older map-only developer installer
remains available: `sh tools/install_skirmish.sh [--dest MAP_DIRECTORY]`.

Launch **Command & Conquer: Omarchy Edition** from your app menu.
**Package Conflict** opens directly in the skirmish lobby. Take the green Omarchian slot and
put **Normal AI** in the pink Walled Garden slot. Both slots must be occupied.
Default cash is $10,000 with Light Support starting units. Rush and Turtle
AI also work with the map rules; avoid Naval AI on this land map. Two humans
can play too. Factions, colours and starting positions are fixed.

Steam and Yuri's Revenge are not required.

## What's custom

- Buildings and defences, with construction reveals, damaged states,
  production/activity animation, storage stages and connected wall pieces.
- Vehicles with 32 directional frames, independent tank turrets, transport
  ramps, harvesting/docking animation and matching recoverable wrecks.
- Coding-agent helicopters, transports, strike jets and support aircraft;
  rotor animation and matching crash sprites.
- Infantry with eight authored directions, generated walking, firing,
  prone, parachuting and death states, including DHH and Antivirus dogs.
- Illustrated faction-specific production icons, a self-contained custom
  palette and player-colour accents.

The two factions keep stock actor IDs so AI, factories, captured structures,
harvesters and MCV deployment remain compatible. Six country-exclusive units
are unlocked for the map's two fixed factions; their tech requirements remain.
DHH retains Tanya's normal tech requirements, cost and one-unit limit.
Most combat values remain stock; the existing light/heavy tank speed changes
remain. The symmetric map has six regenerating ore mines and a central village.

## Current limits

This is a complete first-pass visual set for the listed land-and-air roster,
not a standalone engine or a fully original game. Terrain, neutral scenery,
sounds, projectiles, global effects, naval units and stock UI remain Red Alert.
Some specialist vehicles use adapted chassis from the same original atlas.
The full inventory is in [assets/ROSTER.md](assets/ROSTER.md).

Animations are deliberately simple: deployment reveals, colour pulses,
articulated infantry strides, recoil and collapse. They are not hand-drawn
frame-by-frame animations. Building footprints, exits, occlusion, rotating
parts and the overall style still need an in-game visual pass.

Shared actors have faction-specific battlefield names and icons. OpenRA's
stock production tooltip takes one static name: shared sidebar tooltip
headings can still show the Omarchian name, while descriptions use stock
unit roles. Disguised spies retain the engine's disguise tooltip behaviour.
Harvester cargo pips show fullness; the body keeps its faction appearance
instead of changing to stock ore-truck artwork. The archived mission keeps
its old names and is not loaded by this skirmish.

## Validation and playtest

Run `python -m unittest discover -s tests -v`. This checks the symmetric
economy, routes, deployment space, binary map, names, all roster assets,
sequence bounds, SHP round-trips and reproducible packaging.

CI also builds pinned OpenRA, runs map YAML lint with warnings as errors,
and decodes every generated SHP through OpenRA's own loader. It compares
exported pixels, palette, dimensions and visible frame counts. The workflow
publishes an installable map and art previews.

Before treating the build as playtested, complete a match on the XPS:

1. Deploy both bases; watch the AI build, harvest and attack.
2. Build the tech tree, tanks, aircraft and DHH. Watch turns, turrets and rotors.
3. Damage, repair, sell and destroy buildings. Check entrances and overlays.
4. Unload transports, harvest, capture factories and recover wrecks.
5. Finish a match and check victory/defeat, visibility and balance.

Asset previews and automated checks are not gameplay evidence.
