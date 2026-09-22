#!/usr/bin/env python3
"""Decode every generated SHP using OpenRA, checking pixels, dimensions and frame count."""
import argparse
from pathlib import Path
import struct
import subprocess
from PIL import Image
import build_art


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine',type=Path)
    parser.add_argument('art',type=Path)
    args=parser.parse_args();engine=args.engine.resolve();art=args.art.resolve()
    palette=(art/'omarchy-art.pal').read_bytes()
    colours=[tuple(palette[i+k]*255//63 for k in range(3)) for i in range(0,768,3)]
    sprites=sorted(art.glob('*.shp'))
    # The generated manifest excludes stale artifacts from earlier builds.
    import json
    manifest=json.loads((art/'art-manifest.json').read_text())
    names=set(manifest)|{p.stem+'-icon' for p in sprites if p.stem in manifest and (art/(p.stem+'-icon.shp')).exists()}
    count=0
    for sprite in sprites:
        if sprite.stem not in names: continue
        subprocess.run([str(engine/'utility.sh'),'ra','--png',str(sprite),str(art/'omarchy-art.pal')],cwd=engine,check=True,stdout=subprocess.DEVNULL)
        data=sprite.read_bytes();frames=struct.unpack_from('<H',data)[0];w,h=struct.unpack_from('<HH',data,6)
        expected_files=[]
        for i in range(frames):
            offset=struct.unpack_from('<I',data,14+i*8)[0]&0xffffff
            expected=build_art.lcw_decode(data[offset:],w*h)
            png=engine/f'{sprite.stem}-{i:04d}.png'
            if not any(expected):
                if png.exists(): raise AssertionError(f'{png}: blank frame should be omitted')
                continue
            expected_files.append(png)
            with Image.open(png) as im:
                assert im.size==(w,h),(png,im.size,(w,h))
                for index,actual in zip(expected,im.convert('RGBA').getdata()):
                    assert (actual[3]>0)==bool(index),(png,'alpha mismatch')
                    if index: assert all(abs(actual[k]-colours[index][k])<=1 for k in range(3)),(png,'palette/pixel mismatch')
            count+=1
        actual=set(engine.glob(f'{sprite.stem}-*.png'))
        assert actual==set(expected_files),(sprite,'unexpected frames')
        for png in actual: png.unlink()
    print(f'OpenRA verified {len(names)} sprites and {count} visible frames pixel by pixel.')


if __name__=='__main__': main()
