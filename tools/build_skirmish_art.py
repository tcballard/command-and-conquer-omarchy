#!/usr/bin/env python3
"""Original yard sprites and two faction icon sets, using a self-owned VGA palette."""
from pathlib import Path
import colorsys

from PIL import Image, ImageDraw, ImageFont

import build_art
import build_icons
import roster

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets/source/construction-yards.png"
SPRITE_SIZE = (96, 96)
FRAME_COUNT = 34
GREEN = (158, 206, 106)
RED = (247, 118, 142)


def yard_images():
    sheet = Image.open(SOURCE).convert("RGBA")
    if sheet.getchannel("A").getextrema()[0] != 0:
        raise ValueError("The original yard sheet must have real transparency")
    width, height = sheet.size
    images = []
    for row in range(2):
        pair = [sheet.crop((col * width // 2, row * height // 2,
                            (col + 1) * width // 2, (row + 1) * height // 2))
                for col in range(2)]
        boxes = [im.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox() for im in pair]
        if not all(boxes):
            raise ValueError("Every sheet cell must contain a visible building")
        box = (min(b[0] for b in boxes), min(b[1] for b in boxes),
               max(b[2] for b in boxes), max(b[3] for b in boxes))
        scale = min(80 / (box[2] - box[0]), 88 / (box[3] - box[1]))
        size = (round((box[2] - box[0]) * scale), round((box[3] - box[1]) * scale))
        for im in pair:
            tile = im.crop(box).resize(size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", SPRITE_SIZE)
            canvas.alpha_composite(tile, ((96 - size[0]) // 2, 88 - size[1]))
            images.append(canvas)
    return images


def icon_images():
    fonts = (ImageFont.load_default(size=9), ImageFont.load_default(size=8))
    icons = {}
    for side, entries, accent in (("omarchy", roster.OMARCHY, GREEN), ("commie", roster.COMMIE, RED)):
        for actor, name, _desc, role in entries:
            if actor == "badr":
                continue
            img = Image.new("RGB", (64, 48), (26, 27, 38))
            draw = ImageDraw.Draw(img)
            draw.rectangle((0, 0, 63, 47), outline=accent)
            draw.rectangle((1, 1, 62, 8), fill=(36, 40, 59))
            draw.text((4, 0), ">_" if side == "omarchy" else "[!]", font=fonts[1], fill=accent)
            label = build_icons.ICON_LABEL.get(actor, name) if side == "omarchy" else name
            for line_no, line in enumerate(build_icons.wrap_lines(label, fonts[0], 60, draw)):
                draw.text((2, 10 + line_no * 10), line, font=fonts[0], fill=accent)
            if role and len(build_icons.wrap_lines(label, fonts[0], 60, draw)) < 3:
                draw.text((3, 37), role, font=fonts[1], fill=(145, 152, 177))
            icons[side, actor] = img
    return icons


def make_palette(images):
    # Quantize our own artwork, never the game's palette. 0 is transparent;
    # 80..95 are a dedicated player-colour ramp, matching the declared remap.
    sheet = Image.new("RGB", (256, 128 * ((len(images) + 1) // 2)))
    for i, im in enumerate(images):
        sheet.paste(im.convert("RGB"), ((i % 2) * 128, (i // 2) * 128))
    raw = sheet.quantize(colors=239, method=Image.Quantize.MEDIANCUT).getpalette()
    available = [i for i in range(1, 256) if not 80 <= i <= 95]
    palette = [(0, 0, 0)] * 256
    for n, index in enumerate(available):
        palette[index] = tuple(raw[n * 3:n * 3 + 3])
    for i in range(16):
        factor = 1.35 - i * 0.065
        palette[80 + i] = tuple(min(255, round(c * factor)) for c in GREEN)
    # Round-trip the exact six-bit values the engine will load.
    data = bytes(round(c * 63 / 255) for rgb in palette for c in rgb)
    return data, [tuple(data[i + k] * 255 // 63 for k in range(3)) for i in range(0, 768, 3)]


def indexed(im, palette, team_colours=False):
    result = bytearray()
    cache = {}
    for r, g, b, a in im.convert("RGBA").getdata():
        if a < 128:
            result.append(0)
            continue
        hue, saturation, value = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if team_colours and saturation > 0.3 and (0.18 < hue < 0.45 or hue > 0.9 or hue < 0.04):
            result.append(80 + max(0, min(15, round((1 - value) * 17))))
            continue
        rgb = (r, g, b)
        if rgb not in cache:
            candidates = range(1, 256) if not team_colours else [i for i in range(1, 256) if not 80 <= i <= 95]
            cache[rgb] = min(candidates, key=lambda i: sum((palette[i][k] - rgb[k]) ** 2 for k in range(3)))
        result.append(cache[rgb])
    return bytes(result)


def frames(healthy, damaged):
    """Idle/damaged, twelve deployment frames, two six-frame pulses, eight wreck frames."""
    result = [healthy, damaged]
    for n in range(12):
        cut = round(96 * (11 - n) / 12)
        result.append(bytes(96 * cut) + healthy[96 * cut:])
    for base in (healthy, damaged):
        for shift in (0, -1, -2, -2, -1, 0):
            result.append(bytes(max(80, pixel + shift) if 80 <= pixel <= 95 else pixel for pixel in base))
    for n in range(8):
        result.append(bytes(pixel if (i * 13 + i // 96 * 7) % 8 >= n else 0 for i, pixel in enumerate(damaged)))
    assert len(result) == FRAME_COUNT
    return result


def sprite_preview(frame, palette, size=SPRITE_SIZE):
    im = Image.new("RGBA", size)
    im.putdata([(*palette[p], 255) if p else (0, 0, 0, 0) for p in frame])
    return im


def sequence(side, actor):
    block = f"{side}-{actor}:\n\tInherits: {actor}\n"
    if actor == "fact":
        filename = f"{side}-yard.shp"
        block += (f"\tDefaults:\n\t\tFilename: {filename}\n\t\tOffset: 0,-4\n"
                  "\tidle:\n\t\tStart: 0\n"
                  "\tdamaged-idle:\n\t\tStart: 1\n"
                  f"\tmake:\n\t\tFilename: {filename}\n\t\tStart: 2\n\t\tLength: 12\n\t\tTick: 80\n"
                  "\tbuild:\n\t\tStart: 14\n\t\tLength: 6\n\t\tTick: 80\n"
                  "\tdamaged-build:\n\t\tStart: 20\n\t\tLength: 6\n\t\tTick: 80\n"
                  f"\tdead:\n\t\tFilename: {filename}\n\t\tStart: 26\n\t\tLength: 8\n\t\tTick: 80\n"
                  "\tbib:\n\t\tOffset: 0,0\n")
    block += f"\ticon:\n\t\tFilename: {side}-{actor}-icon.shp\n\t\tOffset: 0,0\n"
    return block


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    yards = yard_images()
    icons = icon_images()
    palette_bytes, palette = make_palette(yards + list(icons.values()))
    (output / "omarchy-art.pal").write_bytes(palette_bytes)
    sequences = []
    for (side, actor), icon in icons.items():
        build_art.write_shp(output / f"{side}-{actor}-icon.shp", 64, 48, [indexed(icon, palette)])
        sequences.append(sequence(side, actor))
    preview = Image.new("RGBA", (384, 192), (26, 27, 38, 255))
    for n, side in enumerate(("omarchy", "commie")):
        pair = [indexed(im, palette, team_colours=True) for im in yards[n * 2:n * 2 + 2]]
        build_art.write_shp(output / f"{side}-yard.shp", 96, 96, frames(*pair))
        preview_palette = palette[:]
        if side == "commie":
            for i in range(16):
                preview_palette[80 + i] = tuple(min(255, round(c * (1.35 - i * 0.065))) for c in RED)
        for col, frame in enumerate(pair):
            preview.alpha_composite(sprite_preview(frame, preview_palette), ((n * 2 + col) * 96, 48))
    preview.resize((768, 384), Image.Resampling.NEAREST).save(output / "yard-preview.png")
    icon_sheet = Image.new("RGB", (64 * 8, 48 * ((len(icons) + 7) // 8)), (26, 27, 38))
    for i, icon in enumerate(icons.values()):
        icon_sheet.paste(icon, ((i % 8) * 64, (i // 8) * 48))
    icon_sheet.save(output / "icon-preview.png")
    (output / "sequences.yaml").write_text("\n".join(sequences))


if __name__ == "__main__":
    build(ROOT / "build/omarchy-skirmish")
