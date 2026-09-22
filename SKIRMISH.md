# Omarchy Skirmish

Build your base. Harvest packages. Send the coding agents in.

**Package Conflict** is a two-player land skirmish for stock OpenRA Red Alert
`release-20250330`. Play the green Omarchians against a Soviet AI opponent,
with the existing Omarchy roster and custom sidebar icons. DHH is trainable
from the barracks once you have Neovim, using Tanya's normal cost and one-unit
limit. There are no scripted waves, mission objectives or Five-Year Plan
deadline. The normal skirmish victory rules apply.

## Play on Omarchy

Install OpenRA and its Red Alert content first. In a complete checkout:

```sh
sudo pacman -S --needed openra python-pillow
python tools/build_skirmish.py
```

Copy `build/omarchy-skirmish.oramap` into your OpenRA map directory. For a
normal current installation:

```sh
map_dir="${XDG_CONFIG_HOME:-$HOME/.config}/openra/maps/ra/release-20250330"
if [ -d "$HOME/.openra" ]; then
  map_dir="$HOME/.openra/maps/ra/release-20250330"
fi
mkdir -p "$map_dir"
cp build/omarchy-skirmish.oramap "$map_dir/"
```

Restart OpenRA Red Alert, open **Singleplayer → Skirmish**, and select
**Omarchy Skirmish - Package Conflict**. Take the first (green Omarchian)
slot and put **Normal AI** in the second (pink Commie) slot. Both slots
must be occupied. Starting cash defaults to $10,000 and starting units to
Light Support; both remain adjustable. Rush AI and Turtle AI are also
available. Avoid Naval AI on this land map.

The same map can be hosted for two humans. Factions, colours and starting
positions are fixed for this first version. Steam and Yuri's Revenge are
not required for this OpenRA map.

## What carries over

- The roster, humour, Omarchy colours, logo preview and 43 custom sidebar icons.
- Standard Red Alert economy, build prerequisites and bot modules. Shared
  units keep their original actor IDs so AI production, harvesting, MCV
  deployment and captured factories still use the stock rules.
- Shared units get faction-dependent names on the battlefield. The shared
  build-menu names, descriptions and icons currently use the Omarchian
  version on both sides; a fully separate Soviet palette is future work.
- A larger, rotationally symmetric battlefield, six regenerating ore mines
  and open ground between bases. No prebuilt campaign bases or free waves.

The older mission remains in `omarchy-edition/` as the artwork source and
an archive of the prototype. Its mission script is not included in this map.

## Custom artwork next

Keep the small sprites readable and recognisably Red Alert. Suggested first
set: an Omarchy construction yard, a terminal-inspired light tank, a coding
agent aircraft and a DHH hero sprite. Each needs the actual in-game facing,
animation and team-colour frames, not just a promotional illustration.
The existing terminal-style build icons already give us a visual direction.
New artwork should be original and its source/licence recorded with it.

## Validation

`python -m unittest discover -s tests -v` checks equal starting resources,
clear deployment areas, ground routes, binary resource placement, Fluent
references and reproducible packaging with all referenced icons present.
GitHub Actions additionally builds OpenRA `release-20250330` and runs the
engine's YAML lint with warnings treated as errors. A passing run provides
the installable `omarchy-skirmish` artifact.

These are not playtest claims. Before calling this ready: play a complete
match on the XPS, observe the AI deploy/build/harvest/attack, train DHH and
the aircraft, and check victory/defeat and battlefield tooltips. Balance
and the visual feel still need that playtest.
