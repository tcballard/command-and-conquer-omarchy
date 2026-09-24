<h1 align="center">Command & Conquer: Omarchy Edition</h1>

<p align="center"><strong>Build the ISO. Harvest packages. Send the coding agents into battle.</strong></p>

![Illustrated Omarchy Edition battlefield and title artwork](assets/github-social-preview.png)

An Omarchy-themed **OpenRA Red Alert skirmish** for x86_64 Omarchy. Play as the
green Omarchians against two AI opponents, **Reboot Required** and **The Walled
Orchard**, on the three-player **Package Conflict** map. Build a base and fight
with custom faction artwork, units and an Omarchy-styled interface.

**[Download the v0.1.0 installer →](https://github.com/tcballard/command-and-conquer-omarchy/releases/download/v0.1.0/install-omarchy-edition.sh)**

Run it as your normal user after downloading it to `~/Downloads`:

```bash
bash ~/Downloads/install-omarchy-edition.sh
```

The installer bundles the game, pinned engine and runtime. First launch may
download Red Alert terrain and sounds. Preview 8 played well on an Omarchy PC;
the [v0.1.0 release](https://github.com/tcballard/command-and-conquer-omarchy/releases/tag/v0.1.0)
also passed its client, installer and artwork checks. [Setup and uninstall](SKIRMISH.md)
· [Release notes](packaging/RELEASE-NOTES.md)

## A custom army on both sides

![Custom roster asset preview; not an in-game screenshot](assets/previews/roster.png)

Original building, vehicle, aircraft and infantry artwork, illustrated build
icons, rotating tank turrets, aircraft rotors, damage states and matching
wrecks. The coding-agent helicopters and long-haired DHH are in the build.
Animations are a first pass; a complete XPS match still needs to verify the
presentation and balance.

Includes OpenRA Red Alert `release-20250330`; its game content downloads on first launch. Terrain,
sound, projectiles and the underlying game still use the Red Alert foundation.
This is not Red Alert 2 or Yuri's Revenge.

## Make it yours

Names live in `tools/skirmish_roster.py`. The [art sources](assets/README.md)
and sprite compiler are included, so everything can be rebuilt with Python
and Pillow. Run `sh tools/install_skirmish.sh` from a complete checkout.

The earlier mission remains archived in `omarchy-edition/`.
[INSTALL.md](INSTALL.md) and [NOTES.md](NOTES.md) describe that prototype;
[SKIRMISH.md](SKIRMISH.md) describes the current game and its testing limits.
