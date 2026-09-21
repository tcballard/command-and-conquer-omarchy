#!/bin/sh
# Regenerates map.bin/map.yaml and packs omarchy-edition.oramap with all files
# at the archive root (same layout as the shipped .oramap files).
set -eu
cd "$(dirname "$0")/.."
python3 tools/build_map.py > /dev/null
rm -f omarchy-edition.oramap
cd omarchy-edition
zip -r ../omarchy-edition.oramap map.yaml map.bin rules.yaml *.ftl *.lua
cd ..
unzip -l omarchy-edition.oramap
