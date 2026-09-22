#!/usr/bin/env python3
"""Wrap the prebuilt custom map in a deterministic, self-contained Bash installer."""
import base64
import hashlib
import io
import tarfile
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(map_path=None, output=None, mods=None):
    map_path = map_path or ROOT / 'build/omarchy-skirmish.oramap'
    output = output or ROOT / 'build/install-omarchy-edition.sh'
    mods = mods or ROOT / 'build/mods'
    if not (mods / 'omarchy/OpenRA.Mods.Omarchy.dll').is_file():
        raise FileNotFoundError('Build the Omarchy mod and menu assembly before packaging the installer.')
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w') as archive:
        entries = [('map.oramap', map_path)]
        entries += [('mods/' + str(p.relative_to(mods)), p) for p in sorted(mods.rglob('*'))
                    if p.is_file() and p != mods / 'omarchy/mod.yaml']
        for name, path in entries:
            data = path.read_bytes()
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o644
            item.mtime = 0
            archive.addfile(item, io.BytesIO(data))
    payload = gzip.compress(raw.getvalue(), mtime=0)
    template = (ROOT / 'packaging/install.sh.in').read_text()
    header = template.replace('@MAP_SHA@', hashlib.sha256(payload).hexdigest())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(header.encode() + base64.encodebytes(payload))
    output.chmod(0o755)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.sh.sha256').write_text(f'{digest}  {output.name}\n')
    return output


if __name__ == '__main__':
    print(build())
