#!/usr/bin/env python3
"""Start the release client with software GL and verify its Omarchy lobby connection."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import zipfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument('bundle', type=Path)
    p.add_argument('--content', type=Path)
    a = p.parse_args()
    bundle = a.bundle.resolve()
    with tempfile.TemporaryDirectory(prefix='omarchy-smoke-') as tmp:
        root = Path(tmp)
        archive = a.content
        if archive is None:
            archive = root / 'ra.zip'
            mirrors = urllib.request.urlopen('https://www.openra.net/packages/ra-quickinstall-mirrors.txt', timeout=30).read().decode().splitlines()
            for url in mirrors:
                if not url.startswith('https://'):
                    continue
                try:
                    with urllib.request.urlopen(url, timeout=60) as response:
                        archive.write_bytes(response.read())
                    if hashlib.sha1(archive.read_bytes()).hexdigest() == '44241f68e69db9511db82cf83c174737ccda300b':
                        break
                except Exception as exc:
                    print(f'Mirror unavailable: {exc}', flush=True)
        if not archive.is_file() or hashlib.sha1(archive.read_bytes()).hexdigest() != '44241f68e69db9511db82cf83c174737ccda300b':
            raise RuntimeError('Pinned upstream Red Alert content checksum did not match')
        support = root / 'support'
        with zipfile.ZipFile(archive) as z:
            z.extractall(support / 'Content/ra/v2')
        env = dict(os.environ, SDL_VIDEODRIVER='offscreen', SDL_AUDIODRIVER='dummy',
                   ALSOFT_DRIVERS='null', LIBGL_ALWAYS_SOFTWARE='1')
        command = [str(bundle / 'OpenRA'), 'Game.Mod=omarchy', f'Engine.SupportDir={support}',
                   'Graphics.Mode=Windowed', 'Graphics.WindowedSize=1280,720',
                   'Game.FetchNews=false', 'Debug.CheckVersion=false']
        try:
            result = subprocess.run(command, cwd=bundle, env=env, capture_output=True, timeout=25)
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or b'').decode(errors='replace')
        else:
            raise RuntimeError(f'Game exited before lobby check: {result.returncode}\n{result.stdout.decode()}\n{result.stderr.decode()}')
        server = (support / 'Logs/server.log').read_text()
        if 'Loading mod: omarchy' not in output or 'Initial mod: omarchy' not in server or 'has joined the game' not in server:
            raise RuntimeError('Client did not enter the bundled Omarchy lobby\n' + output + '\n' + server)
        exceptions = support / 'Logs/exception.log'
        if exceptions.exists() and exceptions.stat().st_size:
            raise RuntimeError(exceptions.read_text())
        print('Real bundled client rendered with software OpenGL and joined the Omarchy skirmish lobby.')
        print(server)


if __name__ == '__main__':
    main()
