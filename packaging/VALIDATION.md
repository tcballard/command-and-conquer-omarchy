# Installer validation

Target: x86_64 Omarchy / Arch Linux, OpenRA 20250330.

Reproduced in the Linux build workspace:
- Five lifecycle tests: `python -m unittest discover -s tests -p test_installer.py -v`.
- Full map payload installed byte-for-byte into an isolated home, launcher invoked with a mocked OpenRA executable, then uninstalled.
- Bash syntax validation for the template and generated installer.
- Deterministic installer output and corrupt-payload rejection before dependency installation.

System package management, privilege prompts and GUI launch were mocked. This does not establish on-device compatibility.
Not run: real pacman installation, Omarchy app-menu launch, first-run Red Alert content setup, a complete XPS match, shellcheck or desktop-file-validate (the last two are unavailable here).

Historical game validation: base commit `101c11853aad28be8376855f664e507399c924b6` passed OpenRA strict map lint and pixel verification in [CI](https://github.com/tcballard/command-and-conquer-omarchy/actions/runs/35764007761). The installer leaves that map unchanged.

Package provenance: Arch official `openra` package and executable layout checked on 2026-09-22 at https://archlinux.org/packages/extra/x86_64/openra/ and its file list. Upstream launcher arguments checked at OpenRA/OpenRA tag `release-20250330`, `packaging/linux/openra.in`.

SHA-256 of tested inputs:
```
8e4bf7a97bb83343360a443d2a7f5037ed29a3fffbf3bf1b0500a90204b4ff42  packaging/install.sh.in
97badda4b3705dd034cec54ccef4db918a3fe7c9b1b581b2bbfc4126d29e9211  tools/build_installer.py
bbcba0d3175bd80c3fb20315ca7fb28793745d6878d4c79449e8b255086e3ec5  tests/test_installer.py
bf982a4ad4e6b470ae2278f4ab2eae1019ed6d70a3dcd3b8ab365ddb9d83b0cd  build/omarchy-skirmish.oramap
```
