"""Checks the economy, access routes and packaged skirmish boundary."""
from collections import deque
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_skirmish as sk
import build_skirmish_art as art
import build_art


class SkirmishTests(unittest.TestCase):
    def test_equal_economy_and_clear_starting_areas(self):
        resources, mines, trees = sk.layout()
        self.assertEqual(resources, {sk.mirror(k): v for k, v in resources.items()})
        self.assertEqual(set(mines), {sk.mirror(k) for k in mines})
        blocked = sk.blocked_cells(mines, trees)
        self.assertEqual(blocked, {sk.mirror(k) for k in blocked})
        self.assertFalse(blocked & set(resources))
        for sx, sy in sk.SPAWNS:
            for dx in range(-6, 7):
                for dy in range(-6, 7):
                    self.assertNotIn((sx + dx, sy + dy), blocked | set(resources))

    def test_ground_routes_reach_enemy_and_every_ore_field(self):
        resources, mines, trees = sk.layout()
        blocked = sk.blocked_cells(mines, trees)
        queue = deque([sk.SPAWNS[0]])
        seen = set(queue)
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                cell = x + dx, y + dy
                if 2 <= cell[0] < 94 and 2 <= cell[1] < 94 and cell not in blocked and cell not in seen:
                    seen.add(cell)
                    queue.append(cell)
        self.assertIn(sk.SPAWNS[1], seen)
        self.assertTrue(set(resources) <= seen)

    def test_binary_and_rules_are_skirmish_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            sk.generate(out)
            data = (out / "map.bin").read_bytes()
            kind, width, height, tiles, heights, resources = struct.unpack_from("<BHHIII", data)
            self.assertEqual((kind, width, height, tiles, heights), (2, 96, 96, 17, 0))
            self.assertEqual(resources, 17 + 3 * width * height)
            self.assertEqual(len(data), resources + 2 * width * height)
            expected, _, _ = sk.layout()
            for x in range(width):
                for y in range(height):
                    offset = resources + 2 * (x * height + y)
                    self.assertEqual(tuple(data[offset:offset + 2]), expected.get((x, y), (0, 0)))
            rules = (out / "rules.yaml").read_text()
            manifest = (out / "map.yaml").read_text()
            for forbidden in ("LuaScript", "MissionData", "CampaignAI", "~disabled", ".COMMIE:"):
                self.assertNotIn(forbidden, rules)
            self.assertNotIn("campaign", manifest)
            self.assertEqual(manifest.count(": mpspawn"), 2)
            self.assertEqual(manifest.count("Playable: True"), 2)
            self.assertNotIn("Prerequisites:", rules)  # stock production/AI compatibility
            strings = (out / "omarchy.ftl").read_text()
            keys = set(re.findall(r"^([a-z][\w-]*) =", strings, re.M))
            for key in re.findall(r"(?:Name|Description): ([\w-]+)\.(?:name|description)", rules):
                self.assertIn(key, keys)

    def test_archive_is_reproducible_and_contains_all_referenced_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "map"
            sk.generate(out)
            first, second = Path(tmp) / "first.oramap", Path(tmp) / "second.oramap"
            sk.package(out, first)
            sk.package(out, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())
                self.assertFalse(any("/" in n or n.endswith(".lua") for n in names))
                sequences = archive.read("sequences.yaml").decode()
                for name in re.findall(r"Filename: (\S+)", sequences):
                    self.assertIn(name, names)
                self.assertEqual(len(archive.read("omarchy-art.pal")), 768)
                self.assertLessEqual(max(archive.read("omarchy-art.pal")), 63)
                for side in ("omarchy", "commie"):
                    sprite = archive.read(f"{side}-yard.shp")
                    count = struct.unpack_from("<H", sprite)[0]
                    width, height = struct.unpack_from("<HH", sprite, 6)
                    self.assertEqual((count, width, height), (34, 96, 96))
                    decoded = []
                    for i in range(count):
                        offset = struct.unpack_from("<I", sprite, 14 + i * 8)[0] & 0xFFFFFF
                        frame = build_art.lcw_decode(sprite[offset:], width * height)
                        self.assertEqual(len(frame), width * height)
                        decoded.append(frame)
                    self.assertNotEqual(decoded[0], decoded[1])
                    self.assertLess(sum(bool(p) for p in decoded[2]), sum(bool(p) for p in decoded[13]))
                    self.assertTrue(any(80 <= p <= 95 for p in decoded[0]))
                    self.assertLess(sum(bool(p) for p in decoded[-1]), sum(bool(p) for p in decoded[1]))

    def test_original_sheet_and_faction_icon_coverage(self):
        images = art.yard_images()
        self.assertEqual(len(images), 4)
        for im in images:
            self.assertEqual(im.size, (96, 96))
            self.assertEqual(im.getchannel("A").getextrema(), (0, 255))
        icons = art.icon_images()
        for entries, side in ((sk.roster.OMARCHY, "omarchy"), (sk.roster.COMMIE, "commie")):
            for actor, *_ in entries:
                if actor != "badr":
                    self.assertIn((side, actor), icons)
        self.assertNotEqual(icons["omarchy", "e1"].tobytes(), icons["commie", "e1"].tobytes())


if __name__ == "__main__":
    unittest.main()
