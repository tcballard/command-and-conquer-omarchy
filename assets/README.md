# Artwork provenance

`source/construction-yards.png` is original generated artwork for this project, created with the built-in Imagegen tool on 22 September 2026. It contains healthy/damaged Omarchian and Commie construction yards on a transparent background. It contains no extracted EA sprites. It is a source sheet, not a game screenshot.

`tools/build_skirmish_art.py` crops the four cells, scales each pair together, converts them to a project-owned six-bit palette and writes the Westwood SHP files. The 34-frame sequences include healthy/damaged states, a simple bottom-to-top deployment, a production colour pulse and a dissolving wreck. These are deliberately simple first-pass animations. Team-colour pixels are mapped to palette indices 80–95.

The faction icons extend this repository's existing terminal-tile design. They use Pillow's bundled default font, so rebuilding needs neither EA palette files nor separately downloaded fonts. OpenRA and its separately installed game content remain required for the rest of the game.

`previews/` contains outputs from the asset/map builders. These previews are not captured gameplay. The builder reproduces them under `build/omarchy-skirmish/`; Pillow 12.1.0 is pinned in CI.

Original generation prompt:

Use case: stylized-concept. Asset type: production sprite sheet for an original humorous retro real-time strategy game, 'Command & Conquer: Omarchy Edition'. Create a 1024x1024 image with a genuinely transparent RGBA background, containing exactly FOUR independent building sprites arranged in a clean 2 by 2 grid of equal 512x512 cells. Each sprite centred within its own cell with generous transparent padding. Camera: classic 1990s Red Alert 1 style high overhead orthographic view with a little front wall visible; building footprints aligned horizontally/vertically, NOT diamond isometric. Crisp hand-painted pixel-art look, readable bulky shapes and restrained shading, no antialias blur. TOP LEFT: healthy Omarchian construction yard, dark navy industrial workshop, lime green roof panels, small construction crane, a large terminal screen showing a simple >_ glyph, concrete foundation. TOP RIGHT: exactly same Omarchian building in same position/scale with damaged roof, dark scorch marks and a bent crane, still recognisable, no smoke extending outside the footprint. BOTTOM LEFT: healthy opposing construction yard, bulky bureaucratic brutalist industrial office/factory with hot coral red roof accents, heavy concrete columns, satellite dish and small crane, identical footprint and camera. BOTTOM RIGHT: same opposing building damaged, roof broken and dark scorched areas. The healthy and damaged pair must have identical base alignment. Each building completely contained within its cell, no touching or overlaps. No grass, no terrain, no ground outside the rectangular concrete building foundation. No cast shadows outside foundation. No captions, no labels, no grid lines, no watermark, no readable words. Original designs; no copied game sprites. Restrict colour family to charcoal/navy, concrete grey, warm metal, lime green #9ECE6A and coral #F7768E. These sprites will be reduced to approximately 80 pixels square, so bold silhouettes and large features matter.


## Full roster expansion

The current skirmish compiler is `tools/build_roster_art.py`. The six vehicle,
building and infantry atlases in `source/` expand this initial construction-yard
pass into the full land-and-air roster. [ROSTER-ART.md](ROSTER-ART.md) records the
new prompts and import process; [ROSTER.md](ROSTER.md) lists every actor and any
chassis adaptations. `tools/build_skirmish_art.py` supplies the original yard
import and palette helpers; its standalone output is the earlier yard-only pass.

`tools/sequence_contract.json` records sequence-name requirements from the
OpenRA `release-20250330` sequence definitions. It contains names, not game art.
The engine remains the authority for YAML and SHP decoding checks.
