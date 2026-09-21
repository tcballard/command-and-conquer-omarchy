#!/usr/bin/env python3
"""
Generates map.bin and map.yaml for "Red Alert: Omarchy Edition".

map.bin follows OpenRA.Game/Map/Map.cs SaveBinaryData() (release-20250330):

    byte   TileFormat (2)
    ushort MapSize.X, ushort MapSize.Y
    uint   tilesOffset (17), uint heightsOffset (0: RA has no height layer),
    uint   resourcesOffset (17 + 3 * W * H)
    tiles:     for x: for y: ushort templateId, byte templateIndex
    resources: for x: for y: byte resourceType, byte density

Template ids and indices are taken from mods/ra/tilesets/temperat.yaml.
The pontoon bridge (templates 238/381 -> 241 chain -> 235/380) plus its shore
tiles is a verbatim 20x16 copy of the tile *ids* from the shipped map
mods/ra/maps/soviet-06a (cells x=70..89, y=18..33). No art is copied; the ids
just point at the engine's own tileset. The engine's LegacyBridgeLayer spawns
the destroyable br1/br2/br3 actors from those templates at load time.
"""
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "omarchy-edition")

W = H = 64
BOUNDS = (2, 2, 60, 60)  # left, top, width, height -- must not touch the map edge (CheckMapCordon)

# Tileset templates (mods/ra/tilesets/temperat.yaml)
T_CLEAR = 255       # clear1.tem, 1x1, PickAny, 16 variants
T_WATER2 = 2        # w2.tem, 2x2 water
ORE = 1             # ResourceLayer ResourceIndex for Ore (mods/ra/rules/world.yaml)
ORE_DENSITY = 12    # MaxDensity for Ore

# Donor chunk copied from mods/ra/maps/soviet-06a map.bin, x=70..89, y=18..33.
DONOR_CHUNK = [
    [(2,0), (1,0), (1,0), (1,0), (2,0), (2,1), (2,1), (2,0), (2,1), (17,0), (17,1), (17,2), (17,3), (255,9), (255,0), (255,5), (214,0), (206,6), (206,7), (255,1)],
    [(2,2), (1,0), (2,2), (2,0), (2,1), (2,1), (2,3), (2,2), (2,3), (2,1), (17,6), (17,7), (17,8), (255,7), (255,2), (255,2), (214,2), (214,3), (255,14), (218,0)],
    [(2,0), (2,1), (1,0), (2,2), (2,3), (2,1), (2,0), (2,0), (2,1), (2,3), (2,1), (17,12), (17,13), (380,0), (235,1), (235,2), (380,3), (380,4), (55,0), (55,1)],
    [(2,2), (2,3), (2,1), (2,2), (2,3), (2,3), (2,0), (2,0), (2,1), (2,3), (2,3), (2,1), (46,0), (235,4), (235,5), (235,6), (235,7), (380,9), (55,3), (55,4)],
    [(2,2), (2,3), (2,3), (2,0), (2,1), (2,2), (2,2), (2,2), (2,3), (2,0), (2,1), (2,1), (241,0), (241,1), (235,9), (235,10), (235,11), (380,14), (55,6), (55,7)],
    [(2,1), (2,0), (2,1), (2,0), (2,1), (2,0), (2,1), (2,2), (2,3), (2,0), (2,1), (241,0), (241,1), (241,5), (241,6), (241,7), (2,0), (2,1), (2,1), (66,0)],
    [(2,3), (2,2), (2,3), (2,2), (2,3), (2,2), (2,3), (2,2), (2,3), (2,2), (241,0), (241,1), (241,5), (241,6), (241,7), (2,3), (2,2), (2,3), (2,3), (66,2)],
    [(2,1), (2,0), (2,1), (2,1), (2,0), (2,1), (2,0), (2,1), (2,2), (241,0), (241,1), (241,5), (241,6), (241,7), (2,1), (2,3), (2,2), (2,3), (2,1), (67,0)],
    [(2,3), (2,2), (2,0), (2,1), (2,0), (2,1), (2,1), (2,3), (241,0), (241,1), (241,5), (241,6), (241,7), (2,2), (2,3), (2,3), (2,1), (2,2), (2,3), (67,3)],
    [(25,1), (25,2), (2,2), (2,3), (2,2), (2,3), (2,3), (241,0), (241,1), (241,5), (241,6), (241,7), (1,0), (2,0), (2,1), (2,3), (2,3), (2,1), (2,3), (2,3)],
    [(25,6), (25,7), (25,8), (25,9), (1,0), (1,0), (241,0), (241,1), (241,5), (241,6), (241,7), (2,0), (2,1), (2,2), (2,3), (2,2), (2,3), (2,3), (2,2), (2,3)],
    [(25,11), (25,12), (25,13), (25,14), (1,0), (238,1), (238,2), (241,5), (241,6), (241,7), (2,0), (2,1), (2,0), (2,0), (2,1), (2,0), (2,0), (2,1), (2,0), (2,0)],
    [(255,2), (25,17), (25,18), (25,19), (238,5), (238,6), (238,7), (238,8), (238,9), (26,0), (26,1), (2,3), (2,2), (1,0), (2,3), (1,0), (2,2), (1,0), (1,0), (1,0)],
    [(255,4), (25,22), (25,23), (25,24), (381,0), (238,11), (238,12), (238,13), (381,4), (26,3), (26,4), (26,5), (2,1), (2,0), (2,1), (2,1), (2,0), (2,1), (2,0), (2,1)],
    [(255,8), (255,14), (255,1), (211,0), (211,1), (107,0), (107,1), (107,2), (107,3), (255,3), (26,7), (26,8), (25,0), (25,1), (25,2), (2,3), (2,2), (2,3), (2,2), (2,3)],
    [(255,9), (255,5), (207,1), (207,2), (211,3), (107,4), (107,5), (107,6), (107,7), (255,12), (255,6), (26,11), (25,5), (25,6), (25,7), (25,8), (25,9), (2,1), (2,0), (2,1)],
]
CHUNK_W, CHUNK_H = 20, 16
CHUNK_X, CHUNK_Y = 36, 36  # top-left of the donor chunk in this map

# Water templates present in the donor chunk (everything else in it is land/shore/bridge)
WATER_TEMPLATES = {1, 2}


def clear_tile(x, y):
    # Same variant selection the engine applies for index 255 (Map.cs LoadBinaryData)
    return (T_CLEAR, (x % 4) + (y % 4) * 4)


def water_tile(x, y):
    return (T_WATER2, (x % 2) + (y % 2) * 2)


def in_chunk(x, y):
    return CHUNK_X <= x < CHUNK_X + CHUNK_W and CHUNK_Y <= y < CHUNK_Y + CHUNK_H


def chunk_is_water(lx, ly):
    return DONOR_CHUNK[ly][lx][0] in WATER_TEMPLATES


def in_band(x, y):
    """Diagonal river: 7 cells wide along y = x."""
    return abs(y - x) <= 3


def in_ford(x, y):
    """The single land choke through the river (north-west half of the diagonal)."""
    return 25 <= x + y <= 35


# --------------------------------------------------------------------------
# Terrain
# --------------------------------------------------------------------------
def build_terrain():
    water = [[False] * H for _ in range(W)]

    for x in range(W):
        for y in range(H):
            if in_band(x, y) and not in_ford(x, y):
                water[x][y] = True

    # Blend the river into the donor chunk by projecting the chunk's edge
    # water-ness a few cells outward on all four sides.
    for d in range(1, 5):
        for ly in range(CHUNK_H):
            if chunk_is_water(0, ly):
                water[CHUNK_X - d][CHUNK_Y + ly] = True
            if chunk_is_water(CHUNK_W - 1, ly):
                water[CHUNK_X + CHUNK_W - 1 + d][CHUNK_Y + ly] = True
        for lx in range(CHUNK_W):
            if chunk_is_water(lx, 0):
                water[CHUNK_X + lx][CHUNK_Y - d] = True
            if chunk_is_water(lx, CHUNK_H - 1):
                water[CHUNK_X + lx][CHUNK_Y + CHUNK_H - 1 + d] = True

    # Two majority-smoothing passes outside the chunk to round off steps.
    for _ in range(2):
        nxt = [row[:] for row in water]
        for x in range(1, W - 1):
            for y in range(1, H - 1):
                if in_chunk(x, y) or in_ford(x, y):
                    continue
                n = sum(1 for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if (dx or dy) and water[x + dx][y + dy])
                if not water[x][y] and n >= 5:
                    nxt[x][y] = True
                elif water[x][y] and n <= 3:
                    nxt[x][y] = False
        water = nxt

    tiles = [[None] * H for _ in range(W)]
    for x in range(W):
        for y in range(H):
            if in_chunk(x, y):
                tiles[x][y] = DONOR_CHUNK[y - CHUNK_Y][x - CHUNK_X]
            elif water[x][y]:
                tiles[x][y] = water_tile(x, y)
            else:
                tiles[x][y] = clear_tile(x, y)
    return tiles


def is_clear(tiles, x, y):
    return 0 <= x < W and 0 <= y < H and tiles[x][y][0] == T_CLEAR


# --------------------------------------------------------------------------
# Actors
# --------------------------------------------------------------------------
# Footprint dimensions from mods/ra/rules/structures.yaml (all footprint rows,
# including passable '=' bib rows, are reserved so buildings never overlap).
FOOTPRINTS = {
    "fact": (3, 4), "fact.commie": (3, 4),
    "powr": (2, 3), "powr.commie": (2, 3),
    "apwr": (3, 3),
    "proc": (3, 4),
    "tent": (2, 3), "barr": (2, 3),
    "weap": (3, 3), "weap.commie": (3, 3),
    "iron": (2, 2),
    "tsla": (1, 1), "ftur": (1, 1), "kenn": (1, 1), "brik": (1, 1),
}
# Trees: T01..T07 use footprint "__ x_" (2x2, only the bottom-left cell is occupied).
TREE_TYPES = ["t01", "t02", "t03", "t04", "t05", "t06", "t07"]


class Actors:
    def __init__(self, tiles):
        self.tiles = tiles
        self.entries = []
        self.reserved = {}
        self.counter = 0

    def _reserve(self, cells, who):
        for c in cells:
            if c in self.reserved:
                raise SystemExit(f"overlap at {c}: {who} vs {self.reserved[c]}")
            if not is_clear(self.tiles, *c):
                raise SystemExit(f"{who} at {c} is not on clear terrain (tile {self.tiles[c[0]][c[1]]})")
            self.reserved[c] = who

    def building(self, kind, x, y, owner, name=None):
        w, h = FOOTPRINTS[kind]
        cells = [(x + i, y + j) for i in range(w) for j in range(h)]
        name = name or self._auto()
        self._reserve(cells, name)
        self.entries.append((name, kind, {"Location": f"{x},{y}", "Owner": owner}))

    def unit(self, kind, x, y, owner, facing=None, subcell=None, name=None):
        name = name or self._auto()
        self._reserve([(x, y)], name)
        props = {"Location": f"{x},{y}", "Owner": owner}
        if subcell is not None:
            props["SubCell"] = str(subcell)
        if facing is not None:
            props["Facing"] = str(facing)
        self.entries.append((name, kind, props))

    def waypoint(self, name, x, y):
        if not (BOUNDS[0] <= x < BOUNDS[0] + BOUNDS[2] and BOUNDS[1] <= y < BOUNDS[1] + BOUNDS[3]):
            raise SystemExit(f"waypoint {name} outside bounds")
        self.entries.append((name, "waypoint", {"Location": f"{x},{y}", "Owner": "Neutral"}))

    def tree(self, kind, x, y):
        # occupied cell is (x, y + 1); the Location is the footprint's top-left
        name = self._auto()
        self._reserve([(x, y + 1)], name)
        self.entries.append((name, kind, {"Location": f"{x},{y}", "Owner": "Neutral"}))

    def _auto(self):
        self.counter += 1
        return f"Actor{self.counter}"


def in_rect(x, y, x0, y0, x1, y1):
    return x0 <= x <= x1 and y0 <= y <= y1


def place_actors(tiles):
    a = Actors(tiles)

    # ---- Omarchian base (bottom-left) -------------------------------------
    a.building("fact", 12, 47, "Omarchy", name="ISO")
    a.building("powr", 8, 47, "Omarchy")
    a.building("powr", 8, 51, "Omarchy")
    a.building("proc", 17, 47, "Omarchy")       # spawns the free pacman -Syu truck (FreeActor)
    a.building("tent", 12, 52, "Omarchy")
    a.building("weap", 16, 52, "Omarchy")

    a.unit("e1", 11, 44, "Omarchy", facing=0, subcell=1)
    a.unit("e1", 12, 44, "Omarchy", facing=0, subcell=1)
    a.unit("e1", 13, 44, "Omarchy", facing=0, subcell=1)
    a.unit("e3", 15, 44, "Omarchy", facing=0, subcell=1)
    a.unit("e3", 16, 44, "Omarchy", facing=0, subcell=1)
    a.unit("1tnk", 14, 42, "Omarchy", facing=0)
    a.unit("1tnk", 18, 42, "Omarchy", facing=0)

    a.waypoint("WestEntry", 2, 56)
    a.waypoint("WestRally", 8, 56)

    # ---- The Commies (top-right), walled ----------------------------------
    a.building("fact.commie", 50, 6, "USSR", name="Compositor")
    a.building("iron", 55, 7, "USSR", name="FiveYearPlan")
    a.building("apwr", 44, 4, "USSR")
    a.building("apwr", 56, 12, "USSR")
    a.building("powr.commie", 47, 4, "USSR")
    a.building("powr.commie", 58, 4, "USSR")
    a.building("powr.commie", 54, 10, "USSR")
    a.building("barr", 44, 9, "USSR")
    a.building("weap.commie", 48, 12, "USSR")
    a.building("kenn", 53, 13, "USSR")
    a.building("tsla", 42, 14, "USSR")
    a.building("tsla", 46, 18, "USSR")
    a.building("tsla", 52, 19, "USSR")
    a.building("ftur", 41, 10, "USSR")
    a.building("ftur", 55, 19, "USSR")

    # Brick wall: west side x=39 (gate at y=15,16), south side y=23 (gate at x=48,49)
    for y in range(4, 24):
        if y in (15, 16):
            continue
        a.building("brik", 39, y, "USSR")
    for x in range(40, 59):
        if x in (48, 49):
            continue
        a.building("brik", x, 23, "USSR")

    for (x, y, f) in [(41, 15, 768), (41, 16, 768), (47, 21, 512), (50, 21, 512), (45, 20, 512), (43, 12, 768)]:
        a.unit("e1.cadre", x, y, "USSR", facing=f, subcell=1)
    a.unit("3tnk", 44, 16, "USSR", facing=640)
    a.unit("3tnk", 50, 17, "USSR", facing=640)
    a.unit("dog", 53, 15, "USSR", facing=512, subcell=1)
    a.unit("dog", 54, 15, "USSR", facing=512, subcell=1)

    a.waypoint("SovietSpawn", 47, 16)
    a.waypoint("ChokePoint", 15, 15)
    a.waypoint("BridgeNorth", 51, 37)
    a.waypoint("BridgeSouth", 37, 50)

    # ---- Trees (deterministic scatter) -------------------------------------
    rng = random.Random(0x0A4C)
    for x in range(BOUNDS[0], BOUNDS[0] + BOUNDS[2]):
        for y in range(BOUNDS[1], BOUNDS[1] + BOUNDS[3] - 1):
            if in_rect(x, y, 4, 40, 34, 61):        # Omarchian base + ore + reinforcement lane
                continue
            if in_rect(x, y, 36, 2, 61, 26):        # Commie base
                continue
            if in_rect(x, y, 30, 28, 61, 57):       # bridge chunk and its approaches
                continue
            if abs(x + y - 30) <= 8 and abs(y - x) <= 9:  # ford approaches
                continue
            if not (is_clear(tiles, x, y) and is_clear(tiles, x, y + 1)):
                continue
            if (x, y + 1) in a.reserved:
                continue
            if rng.random() < 0.05:
                a.tree(rng.choice(TREE_TYPES), x, y)

    return a


def place_ore(tiles, actors):
    res = [[(0, 0)] * H for _ in range(W)]
    cx, cy = 27, 51
    count = 0
    for x in range(cx - 4, cx + 5):
        for y in range(cy - 4, cy + 5):
            if (x - cx) ** 2 + (y - cy) ** 2 <= 16 and is_clear(tiles, x, y) and (x, y) not in actors.reserved:
                res[x][y] = (ORE, ORE_DENSITY)
                count += 1
    return res, count


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------
def write_bin(path, tiles, res):
    out = bytearray()
    out += struct.pack("<B", 2)
    out += struct.pack("<HH", W, H)
    tiles_offset = 17
    heights_offset = 0
    resources_offset = 17 + 3 * W * H
    out += struct.pack("<III", tiles_offset, heights_offset, resources_offset)
    for x in range(W):
        for y in range(H):
            t, i = tiles[x][y]
            out += struct.pack("<HB", t, i)
    assert len(out) == resources_offset
    for x in range(W):
        for y in range(H):
            t, d = res[x][y]
            out += struct.pack("<BB", t, d)
    with open(path, "wb") as f:
        f.write(out)


MAP_YAML_HEAD = """MapFormat: 12

RequiresMod: ra

Title: Red Alert: Omarchy Edition

Author: Omarchians

Tileset: TEMPERAT

MapSize: {W},{H}

Bounds: {bounds}

Visibility: MissionSelector

Categories: Campaign

Players:
	PlayerReference@Neutral:
		Name: Neutral
		OwnsWorld: True
		NonCombatant: True
		Faction: allies
	PlayerReference@Omarchy:
		Name: Omarchy
		Playable: True
		AllowBots: False
		Required: True
		LockFaction: True
		Faction: allies
		LockColor: True
		Color: 7AA2F7
		LockSpawn: True
		LockTeam: True
		Enemies: USSR
	PlayerReference@USSR:
		Name: USSR
		Bot: campaign
		Faction: soviet
		Color: FE1100
		Enemies: Omarchy

Actors:
"""

MAP_YAML_TAIL = """
Rules: ra|rules/campaign-rules.yaml, ra|rules/campaign-tooltips.yaml, rules.yaml

FluentMessages: ra|fluent/lua.ftl, ra|fluent/campaign.ftl, omarchy.ftl
"""


def write_yaml(path, actors):
    lines = [MAP_YAML_HEAD.format(W=W, H=H, bounds=",".join(str(v) for v in BOUNDS))]
    for name, kind, props in actors.entries:
        lines.append(f"\t{name}: {kind}\n")
        for k, v in props.items():
            lines.append(f"\t\t{k}: {v}\n")
    lines.append(MAP_YAML_TAIL)
    with open(path, "w") as f:
        f.write("".join(lines))


def ascii_preview(tiles, res, actors):
    occ = {}
    for name, kind, props in actors.entries:
        x, y = map(int, props["Location"].split(","))
        occ[(x, y)] = kind
    for c in actors.reserved:
        occ.setdefault(c, "#")
    rows = []
    for y in range(H):
        row = ""
        for x in range(W):
            t = tiles[x][y][0]
            if (x, y) in occ:
                k = occ[(x, y)]
                row += "W" if k == "brik" else ("T" if k.startswith("t0") else ("w" if k == "waypoint" else "#"))
            elif res[x][y][0]:
                row += "o"
            elif t in WATER_TEMPLATES:
                row += "~"
            elif t == T_CLEAR:
                row += "."
            elif t in (241, 235, 238, 380, 381):
                row += "="
            else:
                row += ":"
        rows.append(f"{y:2d} {row}")
    return "\n".join(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tiles = build_terrain()
    actors = place_actors(tiles)
    res, ore_cells = place_ore(tiles, actors)
    write_bin(os.path.join(OUT_DIR, "map.bin"), tiles, res)
    write_yaml(os.path.join(OUT_DIR, "map.yaml"), actors)
    print(ascii_preview(tiles, res, actors))
    print(f"actors: {len(actors.entries)}, ore cells: {ore_cells}")


if __name__ == "__main__":
    main()
