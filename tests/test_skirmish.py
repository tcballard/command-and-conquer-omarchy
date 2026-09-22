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
import build_roster_art as art
import json
import build_art


class SkirmishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / 'map'
        sk.generate(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

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
            out = self.output
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
            # Only the six country-exclusive units are unlocked for our fixed two factions.
            self.assertEqual(rules.count("\t\tPrerequisites:"), len(sk.roster.PREREQUISITES))
            for actor, prerequisite in sk.roster.PREREQUISITES.items():
                self.assertIn(f"Prerequisites: {prerequisite}", rules)
            self.assertNotIn("commie", rules.lower())
            self.assertNotIn("Commies", (out / "omarchy.ftl").read_text())
            strings = (out / "omarchy.ftl").read_text()
            keys = set(re.findall(r"^([a-z][\w-]*) =", strings, re.M))
            for key in re.findall(r"(?:Name|Description): ([\w-]+)\.(?:name|description)", rules):
                self.assertIn(key, keys)

    def test_archive_is_reproducible_and_contains_all_referenced_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "map"
            out = self.output
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
                manifest=json.loads((out/'art-manifest.json').read_text())
                self.assertEqual(set(manifest), {f'{side}-{actor}' for side,entries in sk.roster.SIDES.items() for actor,*_ in entries})
                for name,meta in manifest.items():
                    sprite=archive.read(f'{name}.shp')
                    count=struct.unpack_from('<H',sprite)[0]
                    width,height=struct.unpack_from('<HH',sprite,6)
                    self.assertEqual(count,meta['frames'])
                    self.assertEqual([width,height],meta['size'])
                    decoded=[]
                    for i in range(count):
                        offset=struct.unpack_from('<I',sprite,14+i*8)[0]&0xffffff
                        frame=build_art.lcw_decode(sprite[offset:],width*height)
                        self.assertEqual(len(frame),width*height)
                        decoded.append(frame)
                    for seq,fields in meta['sequences'].items():
                        self.assertLess(fields['Start']+fields['Length']*fields['Facings']-1,count,(name,seq))
                    seq='stand' if meta['kind']=='infantry' else 'idle'
                    start=meta['sequences'][seq]['Start']
                    self.assertTrue(any(decoded[start]),name)
                    if meta['kind']!='building':
                        facings=meta['sequences'][seq]['Facings']
                        self.assertGreaterEqual(facings,8)
                        self.assertNotEqual(decoded[start],decoded[start+facings//2],name)
                    else:
                        damaged=meta['sequences']['damaged-idle']['Start']
                        self.assertNotEqual(decoded[start],decoded[damaged],name)

    def test_complete_roster_and_icons(self):
        icons=art.icon_images()
        for side,entries in sk.roster.SIDES.items():
            for actor,*_ in entries:
                if actor not in sk.roster.SUPPORT:
                    self.assertIn((side,actor),icons)
                source=art.source(side,actor)
                self.assertIsNotNone(source.getchannel('A').getbbox())
        self.assertNotEqual(icons['omarchy','e1'].tobytes(),icons['garden','e1'].tobytes())
        rules=sk.rules()
        self.assertIn('ImageByFullness:\n',rules)
        self.assertNotIn('WithHarvesterSpriteBody@',rules) # docking requires a single body
        self.assertIn('HELI.Husk:',rules)
        self.assertIn('garden-badr-wreck',rules)


if __name__ == "__main__":
    unittest.main()
