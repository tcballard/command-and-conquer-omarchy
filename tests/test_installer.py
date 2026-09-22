"""Exercise installer lifecycle in isolated homes with mocked system commands."""
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
        self.state = self.root / 'installed'
        self.calls = self.root / 'calls'
        self.env = dict(os.environ, HOME=str(self.home),
                        XDG_CONFIG_HOME=str(self.home / 'config'),
                        XDG_DATA_HOME=str(self.home / 'data'),
                        PATH=str(self.bin) + ':' + os.environ['PATH'],
                        INSTALL_STATE=str(self.state), CALLS=str(self.calls))
        self.mock('id', 'echo 1000')
        self.mock('uname', 'echo x86_64')
        self.mock('pacman', '''
if [ "$1" = -Q ]; then
  [ -f "$INSTALL_STATE" ] || exit 1
  printf 'openra %s\\n' "${MOCK_VERSION:-20250330-3}"
else
  printf '%s\\n' "$*" >> "$CALLS"
  touch "$INSTALL_STATE"
fi''')
        self.mock('sudo', 'exec "$@"')
        self.mock('openra-ra', 'printf "launch\\n" >> "$CALLS"')
        self.mock('update-desktop-database', 'exit 0')
        self.payload = self.root / 'map.oramap'
        self.payload.write_bytes(b'custom map test fixture\x00\xff')
        self.installer = build(self.payload, self.root / 'installer.sh')
        self.app = self.home / 'data/command-and-conquer-omarchy'
        self.map = self.home / 'config/openra/maps/ra/release-20250330/omarchy-skirmish.oramap'
        self.desktop = self.home / 'data/applications/command-and-conquer-omarchy.desktop'

    def mock(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/sh\nset -eu\n' + body + '\n')
        path.chmod(0o755)

    def run_installer(self, *args, ok=True):
        result = subprocess.run(['bash', str(self.installer), *args], env=self.env,
                                capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def test_fresh_install_launch_reinstall_remove_preserves_other_data(self):
        other = self.home / 'config/openra/saves/keep'
        other.parent.mkdir(parents=True)
        other.write_text('save')
        self.run_installer()
        self.assertEqual(self.map.read_bytes(), self.payload.read_bytes())
        self.assertIn('Name=Command & Conquer: Omarchy Edition', self.desktop.read_text())
        self.assertEqual(self.calls.read_text().splitlines(), ['-S --needed openra', 'launch'])
        self.run_installer('--no-launch')
        self.assertEqual(len(self.calls.read_text().splitlines()), 2)
        self.run_installer('--uninstall')
        self.assertFalse(self.map.exists())
        self.assertFalse(self.desktop.exists())
        self.assertTrue(self.state.exists())
        self.assertEqual(other.read_text(), 'save')
        self.run_installer('--uninstall')

    def test_legacy_home_and_previous_map_restored(self):
        self.map = self.home / '.openra/maps/ra/release-20250330/omarchy-skirmish.oramap'
        self.map.parent.mkdir(parents=True)
        self.map.write_bytes(b'previous build')
        self.run_installer('--no-launch')
        self.run_installer('--no-launch')
        self.assertEqual(self.map.read_bytes(), self.payload.read_bytes())
        self.run_installer('--uninstall')
        self.assertEqual(self.map.read_bytes(), b'previous build')

    def test_modified_map_is_preserved_on_removal(self):
        self.run_installer('--no-launch')
        self.map.write_bytes(b'user edit')
        self.run_installer('--uninstall', ok=False)
        self.assertEqual(self.map.read_bytes(), b'user edit')
        self.assertTrue((self.app / 'uninstall.sh').exists())

    def test_incompatible_engine_and_root_refused(self):
        self.state.touch()
        self.env['MOCK_VERSION'] = '20990101-1'
        self.run_installer('--no-launch', ok=False)
        self.assertFalse(self.app.exists())
        self.mock('id', 'echo 0')
        self.run_installer('--no-launch', ok=False)
        self.assertFalse(self.app.exists())

    def test_corruption_fails_before_package_install_and_build_is_reproducible(self):
        before = self.installer.read_bytes()
        build(self.payload, self.installer)
        self.assertEqual(before, self.installer.read_bytes())
        header, data = before.split(b'__OMARCHY_PAYLOAD__\n')
        self.installer.write_bytes(header + b'A' + data[1:])
        self.run_installer('--no-launch', ok=False)
        self.assertFalse(self.state.exists())
        self.assertFalse(self.app.exists())


if __name__ == '__main__':
    unittest.main()
