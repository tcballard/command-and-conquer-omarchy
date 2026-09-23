#!/usr/bin/env python3
"""Draw original 30x15 flags in a power-of-two OpenRA chrome atlas."""
from pathlib import Path
from PIL import Image, ImageDraw

DEST = Path(__file__).resolve().parent.parent / 'mod/ui/omarchy-faction.png'
with Image.open(DEST) as original:
    omarchy = original.convert('RGBA').crop((0, 0, 30, 15))

atlas = Image.new('RGBA', (128, 16), (0, 0, 0, 0))
atlas.paste(omarchy, (0, 0))


def frame(x, tint):
    draw = ImageDraw.Draw(atlas)
    draw.rectangle((x, 0, x + 29, 14), fill='#141b1b', outline=tint)
    draw.rectangle((x + 2, 2, x + 27, 12), fill='#192327')
    return draw


# Reboot Required: circular update arrows with a deliberately unfinished progress trail.
draw = frame(32, '#ed7b8f')
draw.arc((39, 2, 51, 13), 205, 65, fill='#ed7b8f', width=2)
draw.polygon([(50, 3), (54, 4), (50, 7)], fill='#ed7b8f')
draw.point((37, 8), fill='#ed7b8f')
draw.point((36, 6), fill='#ed7b8f')

# The Walled Orchard: a stylised growing leaf enclosed by a small gate.
draw = frame(64, '#bb9af7')
draw.polygon([(76, 9), (77, 4), (81, 3), (83, 4), (82, 8), (79, 10)], fill='#9ece6a')
draw.line((78, 9, 84, 5), fill='#17241b')
draw.line((77, 10, 77, 12, 86, 12, 86, 5), fill='#bb9af7', width=1)
draw.line((84, 7, 84, 12), fill='#bb9af7', width=1)

# Combined mark for generic or random garden factions: update arc plus orchard gate.
draw = frame(96, '#a9b1a7')
draw.arc((99, 3, 110, 12), 185, 55, fill='#ed7b8f', width=2)
draw.polygon([(108, 3), (111, 4), (108, 6)], fill='#ed7b8f')
draw.polygon([(116, 8), (118, 4), (121, 4), (122, 8)], fill='#9ece6a')
draw.line((115, 5, 115, 12, 123, 12, 123, 5), fill='#bb9af7')

atlas.save(DEST, optimize=True)
