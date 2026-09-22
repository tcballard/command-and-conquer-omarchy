Build a base, harvest packages, and send DHH and the coding agents against The Walled Garden.

This preview opens directly into the Package Conflict skirmish lobby. The Omarchy launcher has one playable map, no map-change button, and a simple Skirmish / Settings / Quit menu. Original artwork for both factions and the dedicated mod are included in one installer for your x86_64 Omarchy / Arch PC.

## Install

Download **install-omarchy-edition.sh** below, then run:

```bash
bash ~/Downloads/install-omarchy-edition.sh
```

Or download and verify it from your terminal:

```bash
mkdir -p ~/Downloads/omarchy-edition-preview
cd ~/Downloads/omarchy-edition-preview
curl -fLO https://github.com/tcballard/command-and-conquer-omarchy/releases/download/v0.0.1-preview.2/install-omarchy-edition.sh
curl -fLO https://github.com/tcballard/command-and-conquer-omarchy/releases/download/v0.0.1-preview.2/install-omarchy-edition.sh.sha256
sha256sum --check install-omarchy-edition.sh.sha256 && bash install-omarchy-edition.sh
```

The installer includes the map and all custom artwork, installs OpenRA if missing, and adds **Command & Conquer: Omarchy Edition** to your app menu. Run it without sudo; it will request your password if OpenRA needs installing.

Let OpenRA install its Red Alert content if prompted. The downloader returns to the **Package Conflict skirmish lobby**. Take the green slot and add Normal AI in the pink Walled Garden slot. Steam and Yuri's Revenge are not required.

## Preview status

Automated map, sprite, packaging and isolated installer tests pass. Actual XPS installation, desktop launch and a full match still need on-device testing. Animations and balance are a first pass. Terrain, sounds and the underlying game remain OpenRA Red Alert; this is not a standalone original engine. Requires OpenRA 20250330; incompatible versions are rejected without a downgrade.

## Remove

```bash
bash ~/Downloads/install-omarchy-edition.sh --uninstall
```

Adjust the path if you used the terminal-download directory above. OpenRA, its content, saves and other maps are kept. An earlier Package Conflict map is restored if this installer replaced one.
