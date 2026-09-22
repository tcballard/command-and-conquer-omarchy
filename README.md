# Red Alert: Omarchy Edition

A single scripted single-player mission for stock OpenRA Red Alert
(release-20250330): the Omarchians versus the Commies. One `.oramap`, no
engine changes, no bundled art. Text, numbers and a Lua script only.

* `omarchy-edition.oramap` — the deliverable. See `INSTALL.md`.
* `omarchy-edition/` — the unzipped source (`map.yaml`, `map.bin`,
  `map.png`, `rules.yaml`, `sequences.yaml`, `omarchysign.shp`,
  `omarchy.ftl`, `omarchy.lua`).
* `tools/build_map.py` — deterministic generator for `map.bin`, `map.yaml`,
  `map.png` and the logo sprite; `tools/build_art.py` rasterizes the
  official Omarchy logo SVG and writes the Westwood `.shp`;
  `tools/package.sh` regenerates and zips. Requires Python 3 and Pillow.
* `NOTES.md` — what was verified against the engine source, what was not,
  deviations, confidence.

Rebuild:

```sh
sh tools/package.sh
```

Lint with an engine checkout at tag release-20250330:

```sh
TREAT_WARNINGS_AS_ERRORS=true ./utility.sh ra --check-yaml /path/to/omarchy-edition.oramap
```
