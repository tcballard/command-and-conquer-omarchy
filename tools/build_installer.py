#!/usr/bin/env python3
"""Wrap the prebuilt custom map in a deterministic, self-contained Bash installer."""
import base64
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(map_path=None, output=None):
    map_path = map_path or ROOT / 'build/omarchy-skirmish.oramap'
    output = output or ROOT / 'build/install-omarchy-edition.sh'
    payload = map_path.read_bytes()
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
