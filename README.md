# Red Alert: Omarchy Edition

A single scripted single-player mission for stock OpenRA Red Alert
(release-20250330): the Omarchians versus the Commies. One `.oramap`, no
engine changes, no bundled art. Text, numbers and a Lua script only.

* `omarchy-edition.oramap` — the deliverable. See `INSTALL.md`.
* `omarchy-edition/` — the unzipped source (`map.yaml`, `map.bin`,
  `rules.yaml`, `omarchy.ftl`, `omarchy.lua`).
* `tools/build_map.py` — deterministic generator for `map.bin` and
  `map.yaml`; `tools/package.sh` regenerates and zips.
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
