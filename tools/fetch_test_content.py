#!/usr/bin/env python3
"""Fetch the pinned upstream RA test data via OpenRA's official mirror list."""
import hashlib
from pathlib import Path
import sys
import urllib.request

out = Path(sys.argv[1])
expected = '44241f68e69db9511db82cf83c174737ccda300b'
mirrors = urllib.request.urlopen('https://www.openra.net/packages/ra-quickinstall-mirrors.txt', timeout=30).read().decode().splitlines()
for url in mirrors:
    if not url.startswith('https://'):
        continue
    try:
        data = urllib.request.urlopen(url, timeout=90).read()
        if hashlib.sha1(data).hexdigest() == expected:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            break
    except OSError:
        continue
else:
    raise SystemExit('Could not fetch checksum-verified test content')
