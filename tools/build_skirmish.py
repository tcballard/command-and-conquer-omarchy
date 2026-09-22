#!/usr/bin/env python3
"""Build the skirmish from the roster and committed icons; no EA build inputs needed."""
import argparse
from pathlib import Path
import struct
import zipfile

import build_art
import build_text
import roster
import build_skirmish_art

ROOT = Path(__file__).resolve().parent.parent
SIZE = 96
BOUNDS = (2, 2, 92, 92)
SPAWNS = ((18, 73), (77, 22))
ORE_CENTRES = ((30, 74), (18, 57), (38, 48))


def scenery():
    """Mirrored central settlement and rocky flanks; buildings use 2x2 footprints."""
    buildings = [("v02", 44, 40), ("v02", 50, 54),
                 ("v03", 40, 38), ("v03", 54, 56)]
    rocks, rough = set(), set()
    for x in range(25, 30):
        for y in range(34, 40):
            if (x + y) % 3 != 0:
                rocks.add((x, y))
                rocks.add(mirror((x, y)))
    for x in range(38, 49):
        for y in range(29, 36):
            if (x - 43) ** 2 + (y - 32) ** 2 < 28 and (x * 11 + y * 7) % 4:
                rough.add((x, y))
                rough.add(mirror((x, y)))
    return buildings, rocks, rough


def blocked_cells(mines, trees):
    buildings, rocks, _ = scenery()
    blocked = {(x, y + 1) for x, y in trees} | set(mines) | rocks
    for _, x, y in buildings:
        blocked.update((x + dx, y + dy) for dx in range(2) for dy in range(2))
    return blocked


def mirror(cell):
    return SIZE - 1 - cell[0], SIZE - 1 - cell[1]


def layout():
    """Rotationally symmetric economy and trees, with open paths between bases."""
    resources = {}
    mines = []
    for centre in ORE_CENTRES:
        for cx, cy in (centre, mirror(centre)):
            mines.append((cx, cy))
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    if dx * dx + dy * dy <= 16 and (dx or dy):
                        resources[cx + dx, cy + dy] = (1, 12)
    trees = set()
    for cx, cy in ((9, 34), (26, 12), (12, 85), (44, 21)):
        for dx, dy in ((0, 0), (2, 0), (4, 1), (0, 3), (3, 4)):
            # t01's occupied cell is one row below its origin.
            cell = (cx + dx, cy + dy)
            trees.add(cell)
            trees.add((SIZE - 1 - cell[0], SIZE - 3 - cell[1]))
    return resources, mines, sorted(trees)


def rules():
    # Retain stock actor IDs, prerequisites, transformations and AI modules.
    # Mission-only variants (.COMMIE) are deliberately not inherited.
    out = ["""Player:
	PlayerResources:
		DefaultCash: 10000

World:
	Faction@allies:
		Name: faction-omarchians.name
	Faction@soviet:
		Name: faction-commies.name
	SpawnStartingUnits:
		StartingUnitsClass: light
	PaletteFromFile@OMARCHY:
		Name: omarchy-art
		Filename: omarchy-art.pal
	PlayerColorPalette@OMARCHY:
		BasePalette: omarchy-art
		BaseName: omarchy-player
		RemapIndex: 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95
"""]
    omarchy = {entry[0]: entry for entry in roster.OMARCHY}
    commies = {entry[0]: entry for entry in roster.COMMIE}
    for actor in sorted(omarchy.keys() | commies.keys()):
        ours = omarchy.get(actor)
        theirs = commies.get(actor)
        side = "omarchy" if ours else "commie"
        entry = ours or theirs
        block = f"{actor.upper()}:\n\tTooltip:\n\t\tName: {side}-{actor}.name\n"
        if ours and theirs:
            block += ("\t\tRequiresCondition: !omarchy-soviet-owner\n"
                      "\tGrantConditionOnFaction@OMARCHYSIDE:\n"
                      "\t\tCondition: omarchy-soviet-owner\n"
                      "\t\tFactions: soviet, russia, ukraine\n"
                      "\t\tResetOnOwnerChange: True\n"
                      "\tTooltip@COMMIE:\n"
                      f"\t\tName: commie-{actor}.name\n"
                      "\t\tRequiresCondition: omarchy-soviet-owner\n")
        # BADR is a support aircraft, not a buildable unit.
        if actor != "badr":
            block += "\tBuildable:\n\t\tIconPalette: omarchy-art\n"
            if entry[2]:
                block += f"\t\tDescription: {side}-{actor}.description\n"
            block += f"\tRenderSprites:\n\t\tImage: {side}-{actor}\n"
            if ours and theirs:
                block += "\t\tFactionImages:\n"
                for faction in ("soviet", "russia", "ukraine"):
                    block += f"\t\t\t{faction}: commie-{actor}\n"
            if actor == "fact":
                block += ("\t\tPlayerPalette: omarchy-player\n"
                          "\tWithDeathAnimation:\n\t\tDeathSequencePalette: omarchy-player\n")
        if actor in roster.SPEED_TWEAKS:
            block += f"\tMobile:\n\t\tSpeed: {roster.SPEED_TWEAKS[actor]}\n"
        if actor in roster.OMARCHY_POWERS:
            trait = roster.OMARCHY_POWERS[actor][0]
            block += (f"\t{trait}:\n\t\tName: omarchy-power-{actor}.name\n"
                      f"\t\tDescription: omarchy-power-{actor}.description\n")
        out.append(block)
    # DHH uses stock Tanya prerequisites, cost and one-unit limit. No timed spawn.
    # Naval production is left untouched: this land map has no buildable coast.
    return "\n".join(out)


def map_yaml(mines, trees):
    out = ["""MapFormat: 12
RequiresMod: ra
Title: Omarchy Skirmish - Package Conflict
Author: Omarchians
Tileset: TEMPERAT
MapSize: 96,96
Bounds: 2,2,92,92
Visibility: Lobby
Categories: Conquest
LockPreview: True

Players:
	PlayerReference@Neutral:
		Name: Neutral
		OwnsWorld: True
		NonCombatant: True
		Faction: allies
	PlayerReference@Multi0:
		Name: Multi0
		Playable: True
		Required: True
		LockFaction: True
		Faction: allies
		LockColor: True
		Color: 9ECE6A
		LockSpawn: True
		Spawn: 1
		LockTeam: True
		Team: 0
	PlayerReference@Multi1:
		Name: Multi1
		Playable: True
		Required: True
		LockFaction: True
		Faction: soviet
		LockColor: True
		Color: F7768E
		LockSpawn: True
		Spawn: 2
		LockTeam: True
		Team: 0

Actors:
"""]
    for index, (x, y) in enumerate(SPAWNS):
        out.append(f"\tSpawn{index}: mpspawn\n\t\tOwner: Neutral\n\t\tLocation: {x},{y}\n")
    for index, (x, y) in enumerate(mines):
        out.append(f"\tMine{index}: mine\n\t\tOwner: Neutral\n\t\tLocation: {x},{y}\n")
    for index, (x, y) in enumerate(trees):
        out.append(f"\tTree{index}: t01\n\t\tOwner: Neutral\n\t\tLocation: {x},{y}\n")
    for index, (actor, x, y) in enumerate(scenery()[0]):
        out.append(f"\tVillage{index}: {actor}\n\t\tOwner: Neutral\n\t\tLocation: {x},{y}\n")
    out.append("\nRules: rules.yaml\nSequences: sequences.yaml\nFluentMessages: omarchy.ftl\n")
    return "".join(out)


def write_bin(path, resources):
    result = bytearray(struct.pack("<BHHIII", 2, SIZE, SIZE, 17, 0, 17 + 3 * SIZE * SIZE))
    _, rocks, rough = scenery()
    for x in range(SIZE):
        for y in range(SIZE):
            tile = (216, 0) if (x, y) in rocks else (580, 0) if (x, y) in rough else (255, x % 4 + y % 4 * 4)
            result.extend(struct.pack("<HB", *tile))
    for x in range(SIZE):
        for y in range(SIZE):
            result.extend(bytes(resources.get((x, y), (0, 0))))
    path.write_bytes(result)


def generate(output):
    output.mkdir(parents=True, exist_ok=True)
    resources, mines, trees = layout()
    write_bin(output / "map.bin", resources)
    (output / "map.yaml").write_text(map_yaml(mines, trees))
    (output / "rules.yaml").write_text(rules())
    # Mission messages aren't loaded: keep only reusable names and descriptions.
    strings = build_text.ftl().split("## Objectives", 1)[0]
    (output / "omarchy.ftl").write_text(strings)
    cells = {(x, y): (40, 68, 40) for x in range(SIZE) for y in range(SIZE)}
    for cell in resources:
        cells[cell] = (148, 128, 96)
    for x, y in trees:
        cells[x, y + 1] = (28, 32, 36)
    buildings, rocks, rough = scenery()
    for cell in rough:
        cells[cell] = (90, 83, 65)
    for cell in rocks:
        cells[cell] = (91, 95, 102)
    for _, x, y in buildings:
        for dx in range(2):
            for dy in range(2):
                cells[x + dx, y + dy] = (190, 181, 158)
    for (x, y), colour in zip(SPAWNS, ((158, 206, 106), (247, 118, 142))):
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                cells[x + dx, y + dy] = colour
    build_art.build_preview(output / "map.png", cells, BOUNDS, scale=4, logo_px=48)
    build_skirmish_art.build(output)


def package(output, destination):
    assets = [output / f"{side}-{actor}-icon.shp" for side, actor in build_skirmish_art.icon_images()]
    assets += [output / f"{side}-yard.shp" for side in ("omarchy", "commie")]
    if not assets or not (output / "sequences.yaml").is_file():
        raise SystemExit("Build the original artwork before packaging.")
    allowed = {"map.yaml", "map.bin", "map.png", "rules.yaml", "sequences.yaml", "omarchy.ftl", "omarchy-art.pal"}
    allowed.update(asset.name for asset in assets)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(allowed):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (output / name).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "omarchy-skirmish")
    parser.add_argument("--generate-only", action="store_true", help="Generate terrain, rules and artwork without the final archive")
    args = parser.parse_args()
    generate(args.output)
    if not args.generate_only:
        target = args.output.parent / "omarchy-skirmish.oramap"
        package(args.output, target)
        print(target)


if __name__ == "__main__":
    main()
