#!/usr/bin/env python3
"""
Art for "Red Alert: Omarchy Edition", generated from the official Omarchy
logo (https://omarchy.org/brand/omarchy-logo.svg, fill #9ECE6A). Nothing here
derives from EA's Red Alert assets.

* rasterize_logo():   even-odd scanline rasterization of the logo path
                      (the path is axis-aligned, so no curve support needed).
* write_shp():        Westwood ShpTD writer, matching
                      OpenRA.Mods.Cnc/SpriteLoaders/ShpTDLoader.cs
                      (header, 8-byte frame table, two trailer entries) with
                      LCW/Format80 frame data as decoded by
                      OpenRA.Mods.Cnc/FileFormats/LCWCompression.cs.
* logo_image():       RGBA PIL image of the logo for the map preview.

The in-game sprite is drawn only with palette indices 80-95, which
PlayerColorPalette (mods/ra/rules/palettes.yaml, RemapIndex 80..95) remaps to
the owner's colour, so the sign takes the Omarchians' green automatically.
"""
import os
import re
import struct

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

# Verbatim path data of omarchy-logo.svg (viewBox 0 0 1200 1200, fill-rule evenodd).
LOGO_PATH = (
    "m1200 1200h-480v-80h400v-1040h-479.996v160h-400v720h720v-720h-80v-80h159.996"
    "v880h-400v160h-640v-1200h1200zm-1120-80h480v-80h-400l.004-400h-80.004zm0-560"
    "h80.004v-400h400v-80h-480.004z"
)
LOGO_GREEN = (0x9E, 0xCE, 0x6A)
OMARCHY_BG = (0x1A, 0x1B, 0x26)   # site background (Tokyo Night)
VIEWBOX = 1200.0


def parse_path(d):
    """Returns a list of closed polygons (lists of (x, y)) from M/m/H/h/V/v/L/l/Z/z data."""
    tokens = re.findall(r"[MmHhVvLlZz]|-?\d*\.?\d+", d)
    polys, cur, start = [], [], (0.0, 0.0)
    x = y = 0.0
    i = 0
    cmd = None
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    polys.append(cur)
                cur = []
                x, y = start
            continue
        if cmd in "Mm":
            nx, ny = float(tokens[i]), float(tokens[i + 1])
            i += 2
            if cmd == "m":
                nx, ny = x + nx, y + ny
            if cur:
                polys.append(cur)
            cur = [(nx, ny)]
            x, y = start = nx, ny
            cmd = "l" if cmd == "m" else "L"   # subsequent pairs are implicit lineto
        elif cmd in "Ll":
            nx, ny = float(tokens[i]), float(tokens[i + 1])
            i += 2
            if cmd == "l":
                nx, ny = x + nx, y + ny
            x, y = nx, ny
            cur.append((x, y))
        elif cmd in "Hh":
            nx = float(tokens[i])
            i += 1
            x = x + nx if cmd == "h" else nx
            cur.append((x, y))
        elif cmd in "Vv":
            ny = float(tokens[i])
            i += 1
            y = y + ny if cmd == "v" else ny
            cur.append((x, y))
        else:
            raise ValueError(f"unsupported path command {cmd}")
    if cur:
        polys.append(cur)
    return polys


def inside_evenodd(polys, px, py):
    crossings = 0
    for poly in polys:
        n = len(poly)
        for k in range(n):
            (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % n]
            if (y1 > py) != (y2 > py):
                xi = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                if xi > px:
                    crossings += 1
    return crossings % 2 == 1


def rasterize_logo(size, supersample=4):
    """Coverage grid [y][x] in 0..1 for the logo scaled to size x size pixels."""
    polys = parse_path(LOGO_PATH)
    cov = [[0.0] * size for _ in range(size)]
    ss = supersample
    for y in range(size):
        for x in range(size):
            hits = 0
            for sy in range(ss):
                for sx in range(ss):
                    px = (x + (sx + 0.5) / ss) * VIEWBOX / size
                    py = (y + (sy + 0.5) / ss) * VIEWBOX / size
                    if inside_evenodd(polys, px, py):
                        hits += 1
            cov[y][x] = hits / (ss * ss)
    return cov


def logo_image(size, colour=LOGO_GREEN):
    cov = rasterize_logo(size)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    for y in range(size):
        for x in range(size):
            a = int(round(cov[y][x] * 255))
            if a:
                px[x, y] = (colour[0], colour[1], colour[2], a)
    return img


# --------------------------------------------------------------------------
# ShpTD writer
# --------------------------------------------------------------------------
def lcw_encode(data):
    """Valid LCW stream using only 'copy literal' (0x80|n) and 'fill' (0xFE) commands."""
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        # run of identical bytes
        j = i
        while j < n and data[j] == data[i] and j - i < 0xFFFF:
            j += 1
        if j - i >= 4:
            out += struct.pack("<BHB", 0xFE, j - i, data[i])
            i = j
            continue
        # literal chunk up to 63 bytes, stopping before a run of >= 4
        k = i
        while k < n and k - i < 63:
            r = k
            while r < n and data[r] == data[k] and r - k < 4:
                r += 1
            if r - k >= 4:
                break
            k += 1
        if k == i:
            k = i + 1
        out.append(0x80 | (k - i))
        out += data[i:k]
        i = k
    out.append(0x80)  # terminator (copy count 0)
    return bytes(out)


def lcw_decode(src, dest_len):
    """Reference decoder mirroring LCWCompression.DecodeInto, used for self-check."""
    dest = bytearray()
    p = 0
    while True:
        i = src[p]
        p += 1
        if (i & 0x80) == 0:
            second = src[p]
            p += 1
            count = ((i & 0x70) >> 4) + 3
            rpos = ((i & 0xF) << 8) + second
            if len(dest) + count > dest_len:
                return bytes(dest)
            srcidx = len(dest) - rpos
            for _ in range(count):
                dest.append(dest[srcidx])
                srcidx += 1
        elif (i & 0x40) == 0:
            count = i & 0x3F
            if count == 0:
                return bytes(dest)
            dest += src[p:p + count]
            p += count
        else:
            count3 = i & 0x3F
            if count3 == 0x3E:
                count, colour = struct.unpack_from("<HB", src, p)
                p += 3
                dest += bytes([colour]) * count
            else:
                if count3 == 0x3F:
                    count = struct.unpack_from("<H", src, p)[0]
                    p += 2
                else:
                    count = count3 + 3
                srcidx = struct.unpack_from("<H", src, p)[0]
                p += 2
                for _ in range(count):
                    dest.append(dest[srcidx])
                    srcidx += 1


def write_shp(path, width, height, frames):
    """frames: list of bytes objects of length width*height (palette indices, 0 = transparent)."""
    LCW = 0x80
    count = len(frames)
    header_len = 2 + 4 + 2 + 2 + 4
    table_len = 8 * count + 16
    data_start = header_len + table_len
    blobs = []
    for f in frames:
        assert len(f) == width * height
        enc = lcw_encode(f)
        assert lcw_decode(enc, len(f)) == bytes(f), "LCW round-trip failed"
        blobs.append(enc)
    out = bytearray()
    out += struct.pack("<H", count)
    out += struct.pack("<HH", 0, 0)
    out += struct.pack("<HH", width, height)
    out += struct.pack("<HH", 0, 0)
    offset = data_start
    for enc in blobs:
        out += struct.pack("<I", offset | (LCW << 24))
        out += struct.pack("<HH", 0, 0)
        offset += len(enc)
    eof = data_start + sum(len(b) for b in blobs)
    out += struct.pack("<I", eof)      # trailer entry 1: end-of-file offset (checked by IsShpTD)
    out += struct.pack("<HH", 0, 0)
    out += bytes(8)                    # trailer entry 2: zeros
    assert len(out) == data_start
    for enc in blobs:
        out += enc
    assert len(out) == eof
    with open(path, "wb") as fh:
        fh.write(out)


def logo_sign_frame(size, fill_index=82, shadow_index=91):
    """Palette-indexed frame: logo in a remappable index with a 1px drop shadow."""
    cov = rasterize_logo(size)
    frame = bytearray(size * size)
    solid = [[cov[y][x] >= 0.5 for x in range(size)] for y in range(size)]
    for y in range(size):
        for x in range(size):
            if solid[y][x]:
                frame[y * size + x] = fill_index
            elif x > 0 and y > 0 and solid[y - 1][x - 1]:
                frame[y * size + x] = shadow_index
    return bytes(frame)


def build_preview(png_path, cell_colours, bounds, scale, logo_px):
    """cell_colours: dict (x, y) -> (r, g, b) for every cell; bounds: (left, top, w, h)."""
    left, top, w, h = bounds
    img = Image.new("RGB", (w * scale, h * scale), OMARCHY_BG)
    px = img.load()
    for y in range(h):
        for x in range(w):
            c = cell_colours[(left + x, top + y)]
            for dy in range(scale):
                for dx in range(scale):
                    px[x * scale + dx, y * scale + dy] = c
    # Logo badge, bottom-right corner
    pad = logo_px // 8
    badge = logo_px + 2 * pad
    bx = img.width - badge - pad
    by = img.height - badge - pad
    draw = ImageDraw.Draw(img)
    draw.rectangle([bx, by, bx + badge - 1, by + badge - 1], fill=OMARCHY_BG, outline=LOGO_GREEN, width=2)
    logo = logo_image(logo_px)
    img.paste(logo, (bx + pad, by + pad), logo)
    img.save(png_path, "PNG", optimize=True)


if __name__ == "__main__":
    # Smoke test: round-trip a frame and print the sign as ASCII.
    size = 48
    frame = logo_sign_frame(size)
    for y in range(size):
        print("".join("#" if frame[y * size + x] == 82 else ("+" if frame[y * size + x] else ".") for x in range(size)))
    out = os.path.join(HERE, "omarchysign-test.shp")
    write_shp(out, size, size, [frame])
    print("wrote", out, os.path.getsize(out), "bytes")
    os.remove(out)
