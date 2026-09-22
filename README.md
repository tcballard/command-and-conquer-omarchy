# Command & Conquer: Omarchy Edition

Build the ISO. Harvest packages. Send DHH and the coding agents into battle.

An Omarchy-themed **OpenRA Red Alert skirmish**, built for fun. The green
Omarchians face **The Walled Garden**: Bloatware tanks, Forced Update jets,
Telemetry, and a particularly aggressive Antivirus.

**Package Conflict** gives both sides room to build, equal ore fields and
normal skirmish AI. No scripted waves or campaign countdown.

**[Install and play →](SKIRMISH.md)**

## A custom army on both sides

![Custom roster asset preview; not an in-game screenshot](assets/previews/roster.png)

Original building, vehicle, aircraft and infantry artwork, illustrated build
icons, rotating tank turrets, aircraft rotors, damage states and matching
wrecks. The coding-agent helicopters and long-haired DHH are in the build.
Animations are a first pass; a complete XPS match still needs to verify the
presentation and balance.

Requires OpenRA Red Alert `release-20250330` and its game content. Terrain,
sound, projectiles and the underlying game still use the Red Alert foundation.
This is not Red Alert 2 or Yuri's Revenge.

## Make it yours

Names live in `tools/skirmish_roster.py`. The [art sources](assets/README.md)
and sprite compiler are included, so everything can be rebuilt with Python
and Pillow. Run `sh tools/install_skirmish.sh` from a complete checkout.

The earlier mission remains archived in `omarchy-edition/`.
[INSTALL.md](INSTALL.md) and [NOTES.md](NOTES.md) describe that prototype;
[SKIRMISH.md](SKIRMISH.md) describes the current game and its testing limits.
