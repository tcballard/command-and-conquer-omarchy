#!/bin/sh
# Build and install the skirmish for the current user; no root writes.
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -gt 0 ]; then
  if [ "$#" -ne 2 ] || [ "$1" != "--dest" ]; then
    echo "Usage: sh tools/install_skirmish.sh [--dest MAP_DIRECTORY]" >&2
    exit 2
  fi
  map_dir=$2
else
  map_dir="${XDG_CONFIG_HOME:-$HOME/.config}/openra/maps/ra/release-20250330"
  if [ -d "$HOME/.openra" ]; then
    map_dir="$HOME/.openra/maps/ra/release-20250330"
  fi
fi
python3 -c 'from PIL import Image' 2>/dev/null || {
  echo "Install Python and Pillow first: sudo pacman -S --needed python python-pillow" >&2
  exit 1
}
python3 "$repo_dir/tools/build_skirmish.py"
mkdir -p "$map_dir"
staged_map=$(mktemp "$map_dir/.omarchy-skirmish.XXXXXX")
trap 'rm -f "$staged_map"' EXIT HUP INT TERM
install -m 644 "$repo_dir/build/omarchy-skirmish.oramap" "$staged_map"
mv -f "$staged_map" "$map_dir/omarchy-skirmish.oramap"
printf 'Installed: %s/omarchy-skirmish.oramap\n' "$map_dir"
echo "Open OpenRA Red Alert release-20250330 → Singleplayer → Skirmish."
echo "Choose Package Conflict, take the green slot, and add Normal AI in the pink slot."
