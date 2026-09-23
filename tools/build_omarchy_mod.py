#!/usr/bin/env python3
"""Build an isolated Omarchy mod using the pinned OpenRA manifest and our map."""
import argparse
from pathlib import Path
import shutil
import re
import zipfile
import skirmish_roster as roster

ROOT = Path(__file__).resolve().parent.parent


def build(engine, dll, output):
    output.mkdir(parents=True, exist_ok=True)
    mod = output / 'omarchy'
    content = output / 'omarchy-content'
    mod.mkdir(exist_ok=True)
    content.mkdir(exist_ok=True)
    original = (engine / 'mods/ra/mod.yaml').read_text()
    # Upstream source tags have a development token; installed releases substitute it.
    manifest = original.replace('{DEV_VERSION}', 'release-20250330')
    manifest = manifest.replace('Title: mod-title', 'Title: omarchy-mod-title')
    manifest = manifest.replace('WindowTitle: mod-windowtitle', 'WindowTitle: omarchy-window-title')
    manifest = manifest.replace('\t\t$ra: ra', '\t\t$ra: ra\n\t\t$omarchy: omarchy')
    manifest = manifest.replace('ContentInstallerMod: ra-content', 'ContentInstallerMod: omarchy-content')
    if 'LoadScreen: LogoStripeLoadScreen\n\tImage: ra|uibits/loadscreen.png\n\tImage2x: ra|uibits/loadscreen-2x.png\n\tImage3x: ra|uibits/loadscreen-3x.png' not in manifest:
        raise RuntimeError('Pinned OpenRA loading screen declaration changed')
    manifest = manifest.replace('LoadScreen: LogoStripeLoadScreen\n\tImage: ra|uibits/loadscreen.png\n\tImage2x: ra|uibits/loadscreen-2x.png\n\tImage3x: ra|uibits/loadscreen-3x.png',
                                'LoadScreen: OmarchyCoverLoadScreen\n\tImage: omarchy|cover.png')
    begin = manifest.index('MapFolders:')
    end = manifest.index('\nRules:', begin)
    manifest = manifest[:begin] + 'MapFolders:\n\tomarchy|maps: System\n' + manifest[end:]
    manifest = manifest.replace('\tra|rules/fakes.yaml', '\tra|rules/fakes.yaml\n\tomarchy|roster/rules.yaml\n\tomarchy|rules.yaml')
    manifest = manifest.replace('\tra|sequences/decorations.yaml', '\tra|sequences/decorations.yaml\n\tomarchy|roster/sequences.yaml')
    manifest = manifest.replace('\t\t$omarchy: omarchy', '\t\t$omarchy: omarchy\n\t\tomarchy|roster')
    manifest = manifest.replace('Assemblies: OpenRA.Mods.Common.dll, OpenRA.Mods.Cnc.dll',
                                'Assemblies: OpenRA.Mods.Common.dll, OpenRA.Mods.Cnc.dll, @OMARCHY_DLL@')
    manifest = manifest.replace('\tcommon|chrome/mainmenu.yaml', '\tomarchy|menu.yaml')
    manifest = manifest.replace('\tra|fluent/rules.ftl', '\tra|fluent/rules.ftl\n\tomarchy|messages.ftl\n\tomarchy|roster/omarchy.ftl')
    manifest = manifest.replace('Missions:\n\tra|missions.yaml', 'Missions:')
    manifest = manifest.replace('SupportsMapsFrom: ra', 'SupportsMapsFrom: omarchy')
    # Stock strings for omitted UI are allowed in the shared upstream packages.
    manifest = manifest.replace('AllowUnusedFluentMessagesInExternalPackages: false',
                                'AllowUnusedFluentMessagesInExternalPackages: true')
    (mod / 'mod.yaml.in').write_text(manifest)
    # A build-local manifest is usable directly by OpenRA Utility.
    (mod / 'mod.yaml').write_text(manifest.replace('@OMARCHY_DLL@', str((mod / dll.name).resolve())))
    shutil.copyfile(dll, mod / dll.name)
    for path in (ROOT / 'mod/ui').iterdir():
        shutil.copyfile(path, mod / path.name)
    # Reuse the stock content downloader, but return to Omarchy when it finishes.
    content_manifest = (engine / 'mods/ra-content/mod.yaml').read_text()
    content_manifest = content_manifest.replace('{DEV_VERSION}', 'release-20250330').replace('\tMod: ra\n', '\tMod: omarchy\n')
    (content / 'mod.yaml').write_text(content_manifest)
    shutil.copyfile(engine / 'COPYING', mod / 'COPYING.OpenRA')
    (mod / 'SOURCE.txt').write_text('OpenRA manifest/content configuration: https://github.com/OpenRA/OpenRA/tree/release-20250330 (GPL-3.0-or-later).\nCustom menu source: https://github.com/tcballard/command-and-conquer-omarchy/tree/codex/omarchy-skirmish/mod (GPL-3.0-or-later).\n')
    # Make the custom roster the mod defaults, not optional per-map overrides.
    art = mod / 'roster'
    art.mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT / 'build/omarchy-skirmish.oramap') as src:
        for name in src.namelist():
            if name not in ('map.yaml', 'map.bin', 'map.png'):
                (art / name).write_bytes(src.read(name))
    # Map-local Fluent permits unused attributes; mod-global Fluent does not.
    # Shared production descriptions deliberately use stock role text.
    used = set(re.findall(r'(?:omarchy|garden)-[\w-]+\.(?:name|description)', (art / 'rules.yaml').read_text()))
    messages = []
    for block in (art / 'omarchy.ftl').read_text().split('\n\n'):
        lines = block.splitlines()
        if not lines or ' = ' in lines[0] or not lines[0].endswith(' ='):
            continue
        key = lines[0][:-2].strip()
        attributes = [line for line in lines[1:] if key + '.' + line.strip().split(' =')[0].lstrip('.') in used]
        if attributes:
            messages.append('\n'.join([lines[0], *attributes]))
    (art / 'omarchy.ftl').write_text('\n\n'.join(messages) + '\n')
    (mod / 'roster-check.tsv').write_text(''.join(
        f'{actor}\t{faction}\t{side}-{actor}\n'
        for side, faction in [('omarchy', 'allies'), ('garden', 'soviet')]
        for actor, *_ in roster.SIDES[side]))
    maps = mod / 'maps'
    maps.mkdir(exist_ok=True)
    battle = maps / 'package-conflict.oramap'
    with zipfile.ZipFile(ROOT / 'build/omarchy-skirmish.oramap') as src, zipfile.ZipFile(battle, 'w', zipfile.ZIP_DEFLATED) as dst:
        for name in src.namelist():
            if name not in ('map.yaml', 'map.bin', 'map.png'):
                continue
            data = src.read(name)
            if name == 'map.yaml':
                data = data.replace(b'RequiresMod: ra', b'RequiresMod: omarchy')
                data = data.replace(b'Rules: rules.yaml\nSequences: sequences.yaml\nFluentMessages: omarchy.ftl\n', b'')
            item = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(item, data)
        terrain = src.read('map.bin')
    # A quiet backdrop made from our own map terrain. Never offered as a match.
    shell_yaml = '''MapFormat: 12
RequiresMod: omarchy
Title: Omarchy Backdrop
Author: Omarchy Edition
Tileset: TEMPERAT
MapSize: 96,96
Bounds: 2,2,92,92
Visibility: Shellmap
Categories: Shellmap
Players:
\tPlayerReference@Neutral:
\t\tName: Neutral
\t\tOwnsWorld: True
\t\tNonCombatant: True
\t\tFaction: allies
\tPlayerReference@Creeps:
\t\tName: Creeps
\t\tNonCombatant: True
\t\tFaction: allies
Actors:
'''
    with zipfile.ZipFile(maps / 'backdrop.oramap', 'w', zipfile.ZIP_DEFLATED) as dst:
        for name, data in [('map.yaml', shell_yaml.encode()), ('map.bin', terrain)]:
            item = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(item, data)
    return mod


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('engine', type=Path)
    p.add_argument('dll', type=Path)
    p.add_argument('--output', type=Path, default=ROOT / 'build/mods')
    a = p.parse_args()
    print(build(a.engine, a.dll, a.output))
