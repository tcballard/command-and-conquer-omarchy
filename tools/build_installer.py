#!/usr/bin/env python3
"""Wrap the complete pinned engine + Omarchy mod in a single installer."""
import base64
import gzip
import hashlib
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(bundle=None, output=None):
    bundle = bundle or ROOT / 'build/bundle'
    output = output or ROOT / 'build/install-omarchy-edition.sh'
    for name in ('OpenRA', 'OpenRA.Utility', 'libhostfxr.so', 'SHA256SUMS', 'OMARCHY_VERSION', 'mods/omarchy/mod.yaml'):
        if not (bundle / name).is_file():
            raise FileNotFoundError('Build the complete bundled engine first: missing ' + name)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w') as archive:
        for path in sorted(bundle.rglob('*')):
            if not path.is_file():
                continue
            item = tarfile.TarInfo('engine/' + str(path.relative_to(bundle)))
            data = path.read_bytes()
            item.size = len(data)
            item.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
            item.mtime = 0
            archive.addfile(item, io.BytesIO(data))
    payload = gzip.compress(raw.getvalue(), mtime=0)
    template = (ROOT / 'packaging/install.sh.in').read_text()
    header = template.replace('@PAYLOAD_SHA@', hashlib.sha256(payload).hexdigest())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(header.encode() + base64.encodebytes(payload))
    output.chmod(0o755)
    output.with_suffix('.sh.sha256').write_text(f'{hashlib.sha256(output.read_bytes()).hexdigest()}  {output.name}\n')
    return output


if __name__ == '__main__':
    print(build())
