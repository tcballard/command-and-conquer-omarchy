#!/usr/bin/env python3
"""Stage the pinned self-contained Linux engine with only the Omarchy entry point."""
import argparse
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = 'v0.1.0'


def build(engine, published, mods, output):
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(published, output)
    for required in ('OpenRA', 'OpenRA.Utility', 'libhostfxr.so', 'OpenRA.Game.dll'):
        if not (output / required).is_file():
            raise RuntimeError('Missing self-contained engine component: ' + required)
    for filename in ('AUTHORS', 'COPYING', 'global mix database.dat'):
        shutil.copyfile(engine / filename, output / filename)
    (output / 'VERSION').write_text('release-20250330\n')
    (output / 'OMARCHY_VERSION').write_text(VERSION + '\n')
    shutil.copytree(engine / 'glsl', output / 'glsl')
    for name in ('common', 'common-content', 'ra', 'ra-content'):
        shutil.copytree(engine / 'mods' / name, output / 'mods' / name)
    # RA supplies shared rules/content but is never offered as a playable mod.
    ra = output / 'mods/ra'
    shutil.rmtree(ra / 'maps')
    manifest = (ra / 'mod.yaml').read_text().replace('{DEV_VERSION}', 'release-20250330')
    manifest = manifest.replace('Metadata:\n', 'Metadata:\n\tHidden: true\n')
    (ra / 'mod.yaml').write_text(manifest)
    shutil.copytree(mods, output / 'mods', dirs_exist_ok=True)
    omarchy = output / 'mods/omarchy'
    shutil.copyfile(omarchy / 'OpenRA.Mods.Omarchy.dll', output / 'OpenRA.Mods.Omarchy.dll')
    manifest = (omarchy / 'mod.yaml.in').read_text().replace('@OMARCHY_DLL@', 'OpenRA.Mods.Omarchy.dll')
    (omarchy / 'mod.yaml').write_text(manifest)
    (omarchy / 'mod.yaml.in').unlink()
    (omarchy / 'OpenRA.Mods.Omarchy.dll').unlink()
    (output / 'SOURCE.txt').write_text(
        'OpenRA engine: https://github.com/OpenRA/OpenRA/tree/release-20250330\n'
        'License: GPL-3.0-or-later; see COPYING.\n'
        'Omarchy source and build scripts: https://github.com/tcballard/command-and-conquer-omarchy/tree/' + VERSION + '\n'
        'Red Alert content is downloaded by the upstream content installer on first launch; not included here.\n')
    entries = []
    for path in sorted(output.rglob('*')):
        if path.is_file():
            entries.append(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output)}\n')
    (output / 'SHA256SUMS').write_text(''.join(entries))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('engine', type=Path)
    p.add_argument('published', type=Path)
    p.add_argument('--mods', type=Path, default=ROOT / 'build/mods')
    p.add_argument('--output', type=Path, default=ROOT / 'build/bundle')
    a = p.parse_args()
    print(build(a.engine, a.published, a.mods, a.output))
