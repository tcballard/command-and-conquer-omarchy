"""Installed-bundle lifecycle; the real engine roster check is also run in CI."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_installer import build


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home with spaces'
        self.home.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.calls = self.root / 'calls'
        self.env = dict(os.environ, HOME=str(self.home), XDG_DATA_HOME=str(self.home / 'data'),
                        XDG_CONFIG_HOME=str(self.home / 'config'), PATH=str(self.bin) + ':' + os.environ['PATH'],
                        CALLS=str(self.calls))
        self.script(self.bin / 'id', 'echo 1000')
        self.script(self.bin / 'uname', 'echo x86_64')
        self.script(self.bin / 'pacman', 'echo "System OpenRA must not be used" >&2; exit 99')
        self.script(self.bin / 'update-desktop-database', 'exit 0')
        self.bundle = self.root / 'bundle'
        (self.bundle / 'mods/omarchy').mkdir(parents=True)
        (self.bundle / 'mods/omarchy/mod.yaml').write_text('Assemblies: OpenRA.Mods.Omarchy.dll\n')
        (self.bundle / 'libhostfxr.so').write_bytes(b'test runtime')
        (self.bundle / 'OMARCHY_VERSION').write_text('v0.0.1-preview.7\n')
        self.script(self.bundle / 'OpenRA', 'printf "%s\\n" "$@" > "$CALLS.args"')
        self.script(self.bundle / 'OpenRA.Utility', 'test "${FAIL_CHECK:-0}" = 0; printf "%s\\n" "$*" >> "$CALLS"')
        self.write_manifest()
        self.installer = build(self.bundle, self.root / 'installer.sh')
        self.app = self.home / 'data/command-and-conquer-omarchy'
        self.desktop = self.home / 'data/applications/command-and-conquer-omarchy.desktop'

    def script(self, path, body):
        path.write_text('#!/bin/sh\nset -eu\n' + body + '\n')
        path.chmod(0o755)

    def write_manifest(self):
        (self.bundle / 'SHA256SUMS').write_text(''.join(
            f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(self.bundle)}\n'
            for p in sorted(self.bundle.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS'))

    def run_installer(self, *args, ok=True):
        result = subprocess.run(['bash', str(self.installer), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_fresh_install_launch_reinstall_verify_remove_preserves_other_data(self):
        stock = self.home / 'config/openra/maps/ra/release-20250330/omarchy-skirmish.oramap'
        stock.parent.mkdir(parents=True)
        stock.write_bytes(b'old user map')
        self.run_installer()
        args = Path(str(self.calls) + '.args').read_text()
        self.assertIn('Game.Mod=omarchy\n', args)
        self.assertNotIn('/usr/lib/openra', args)
        self.assertIn('Engine.SupportDir=' + str(self.app / 'support'), args)
        self.assertIn('mods/omarchy/omarchy-icon.png', self.desktop.read_text())
        self.assertTrue(os.access(self.app / 'current/OpenRA', os.X_OK))
        previous = (self.app / 'current').resolve()
        self.run_installer('--no-launch')
        self.assertNotEqual(previous, (self.app / 'current').resolve())
        subprocess.run(['bash', str(self.app / 'launch.sh'), '--verify'], env=self.env, check=True, capture_output=True)
        bad = subprocess.run(['bash', str(self.app / 'launch.sh'), 'Game.Mod=ra'], env=self.env, capture_output=True)
        self.assertNotEqual(bad.returncode, 0)
        save = self.app / 'support/save'
        save.write_text('keep')
        self.run_installer('--uninstall')
        self.assertFalse(self.desktop.exists())
        self.assertFalse((self.app / 'current').exists())
        self.assertEqual(stock.read_bytes(), b'old user map')
        self.assertEqual(save.read_text(), 'keep')

    def test_failed_roster_check_retains_previous_install(self):
        self.run_installer('--no-launch')
        old = (self.app / 'current').resolve()
        self.env['FAIL_CHECK'] = '1'
        self.run_installer('--no-launch', ok=False)
        self.assertEqual((self.app / 'current').resolve(), old)

    def test_existing_random_player_is_restored_to_omarchy(self):
        self.run_installer('--no-launch')
        skirmish = self.app / 'support/skirmish.omarchy.yaml'
        skirmish.write_text('Player: Multi0\n\tFaction: Random\nBots:\n\trush: Multi1\n\t\tFaction: soviet\n')
        subprocess.run(['bash', str(self.app / 'launch.sh')], env=self.env, check=True, capture_output=True)
        self.assertEqual(skirmish.read_text(),
                         'Player: Multi0\n\tFaction: allies\nBots:\n\trush: Multi1\n\t\tFaction: soviet\n')

    def test_missing_runtime_or_corrupt_installed_payload_is_rejected(self):
        (self.bundle / 'libhostfxr.so').unlink()
        with self.assertRaises(FileNotFoundError):
            build(self.bundle, self.installer)
        (self.bundle / 'libhostfxr.so').write_bytes(b'wrong runtime')
        build(self.bundle, self.installer)
        self.run_installer('--no-launch', ok=False)
        self.assertFalse(self.app.exists())

    def test_embedded_corruption_rejected_and_package_reproducible(self):
        before = self.installer.read_bytes()
        build(self.bundle, self.installer)
        self.assertEqual(before, self.installer.read_bytes())
        header, data = before.split(b'__OMARCHY_PAYLOAD__\n')
        self.installer.write_bytes(header + b'A' + data[1:])
        self.run_installer('--no-launch', ok=False)
        self.assertFalse(self.app.exists())

    def test_root_refused(self):
        self.script(self.bin / 'id', 'echo 0')
        self.run_installer('--no-launch', ok=False)
        self.assertFalse(self.app.exists())


if __name__ == '__main__':
    unittest.main()
