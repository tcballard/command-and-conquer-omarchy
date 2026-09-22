#!/usr/bin/env python3
"""
Generates the Omarchian sidebar icons (64x48, Red Alert icon size) as
Westwood .shp files in the temperate palette, from tools/roster.py.

Design: a terminal tile. Tokyo Night background, a prompt glyph, the unit
name in JetBrains Mono, and the Red Alert role in dim text so a newcomer
still knows what the thing is. All original art; no EA pixels.

Build-time inputs (not shipped in the map):
  * temperat.pal  -- 768-byte VGA palette extracted from the game content
                     with `utility.sh ra --extract temperat.pal`; icons use
                     the `chrome` palette, which is this file
                     (mods/ra/rules/palettes.yaml, PaletteFromFile@chrome).
  * JetBrainsMono-*.ttf -- SIL OFL 1.1, Omarchy's own font.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_art  # noqa: E402
import roster     # noqa: E402

ICON_W, ICON_H = 64, 48
BG = (0x1A, 0x1B, 0x26)        # Tokyo Night background
FG = (0x9E, 0xCE, 0x6A)        # Omarchy green
DIM = (0x56, 0x5F, 0x89)       # Tokyo Night comment
PROMPT = (0x7A, 0xA2, 0xF7)    # Tokyo Night blue for the prompt glyph
EDGE = (0x24, 0x28, 0x3B)

TRANSPARENT = 0
SHADOW = 3          # chrome palette ShadowIndex
RESERVED = {TRANSPARENT, SHADOW}


def load_palette(path):
    raw = open(path, "rb").read()
    assert len(raw) == 768, "expected a 768-byte 6-bit VGA palette"
    return [(raw[i] * 255 // 63, raw[i + 1] * 255 // 63, raw[i + 2] * 255 // 63) for i in range(0, 768, 3)]


def nearest_index(palette, rgb, cache):
    if rgb in cache:
        return cache[rgb]
    best, bestd = 1, 1 << 30
    for i, p in enumerate(palette):
        if i in RESERVED:
            continue
        d = (p[0] - rgb[0]) ** 2 + (p[1] - rgb[1]) ** 2 + (p[2] - rgb[2]) ** 2
        if d < bestd:
            best, bestd = i, d
    cache[rgb] = best
    return best


def wrap_name(name, font, max_w, draw):
    """Split a name onto at most two lines that fit max_w pixels."""
    if draw.textlength(name, font=font) <= max_w:
        return [name]
    words = name.split(" ")
    if len(words) > 1:
        for cut in range(len(words) - 1, 0, -1):
            a, b = " ".join(words[:cut]), " ".join(words[cut:])
            if draw.textlength(a, font=font) <= max_w and draw.textlength(b, font=font) <= max_w:
                return [a, b]
    # hard split
    for cut in range(len(name) - 1, 1, -1):
        a, b = name[:cut], name[cut:]
        if draw.textlength(a, font=font) <= max_w and draw.textlength(b, font=font) <= max_w:
            return [a, b]
    return [name[:10], name[10:20]]


ICON_LABEL = {"agun": "Do Not Disturb"}   # shorter labels for the 64 px tile only


def wrap_lines(name, font, max_w, draw, max_lines=3):
    words = name.split(" ")
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
            while draw.textlength(cur, font=font) > max_w:      # single word too long: hard split
                cut = len(cur)
                while cut > 1 and draw.textlength(cur[:cut], font=font) > max_w:
                    cut -= 1
                lines.append(cur[:cut])
                cur = cur[cut:]
    if cur:
        lines.append(cur)
    return lines[:max_lines]


def render_icon(actor, name, role, fonts):
    bold, small = fonts
    img = Image.new("RGB", (ICON_W, ICON_H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, ICON_W - 1, ICON_H - 1], outline=EDGE)
    d.rectangle([1, 1, ICON_W - 2, 8], fill=EDGE)          # title bar
    d.ellipse([4, 3, 7, 6], fill=FG)                          # green dot
    prompt = "\u276f"
    if not small.getmask(prompt).getbbox():
        prompt = ">"
    d.text((11, 0), prompt, font=small, fill=PROMPT)
    label = ICON_LABEL.get(actor, name)
    lines = wrap_lines(label, bold, ICON_W - 4, d)
    y = 11
    for line in lines:
        d.text((2, y), line, font=bold, fill=FG)
        y += 10
    if role and len(lines) <= 2:
        d.text((3, ICON_H - 11), role, font=small, fill=DIM)
    return img


def quantize(img, palette, cache):
    px = img.load()
    out = bytearray(ICON_W * ICON_H)
    for y in range(ICON_H):
        for x in range(ICON_W):
            out[y * ICON_W + x] = nearest_index(palette, px[x, y], cache)
    return bytes(out)


def build_icons(out_dir, palette_path, font_dir):
    palette = load_palette(palette_path)
    bold = ImageFont.truetype(os.path.join(font_dir, "JetBrainsMono-Bold.ttf"), 9)
    small = ImageFont.truetype(os.path.join(font_dir, "JetBrainsMono-Regular.ttf"), 8)
    cache = {}
    sequences = []
    sheet = Image.new("RGB", (ICON_W * 8, ICON_H * ((len(roster.OMARCHY) + 7) // 8)), (0, 0, 0))
    for i, (actor, name, _desc, role) in enumerate(roster.OMARCHY):
        img = render_icon(actor, name, role, (bold, small))
        sheet.paste(img, ((i % 8) * ICON_W, (i // 8) * ICON_H))
        frame = quantize(img, palette, cache)
        fname = f"omarchy-{actor}-icon.shp"
        build_art.write_shp(os.path.join(out_dir, fname), ICON_W, ICON_H, [frame])
        sequences.append(f"{actor}:\n\ticon:\n\t\tFilename: {fname}\n")
    return sequences, sheet


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "icon-preview")
    os.makedirs(out, exist_ok=True)
    seqs, sheet = build_icons(out, sys.argv[2], sys.argv[3])
    sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
    sheet.save(os.path.join(out, "sheet.png"))
    print(f"{len(seqs)} icons -> {out}")
