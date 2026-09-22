#!/bin/sh
# Regenerates map.bin/map.yaml and packs omarchy-edition.oramap with all files
# at the archive root (same layout as the shipped .oramap files).
set -eu
: "${OMARCHY_PAL:?set OMARCHY_PAL to temperat.pal (utility.sh ra --extract temperat.pal)}"
: "${OMARCHY_FONTS:?set OMARCHY_FONTS to a directory containing JetBrainsMono-Bold.ttf and -Regular.ttf}"
cd "$(dirname "$0")/.."
python3 tools/build_map.py > /dev/null
rm -f omarchy-edition.oramap
cd omarchy-edition
zip -r ../omarchy-edition.oramap map.yaml map.bin map.png rules.yaml sequences.yaml *.ftl *.lua *.shp
cd ..
unzip -l omarchy-edition.oramap
