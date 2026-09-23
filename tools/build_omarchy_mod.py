#!/usr/bin/env python3
"""Build an isolated Omarchy mod using the pinned OpenRA manifest and our map."""
import argparse
from pathlib import Path
import shutil
import re
import struct
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
    manifest = manifest.replace('\tra|chrome.yaml', '\tra|chrome.yaml\n\tomarchy|chrome.yaml\n\tomarchy|panels.yaml')
    manifest = manifest.replace('\tra|chrome/ingame-player.yaml', '\tomarchy|ingame-player.yaml')
    manifest = manifest.replace('\tra|chrome/gamesave-loading.yaml', '\tomarchy|gamesave-loading.yaml')
    manifest = manifest.replace('\tcommon|chrome/ingame-menu.yaml', '\tomarchy|ingame-menu.yaml')
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
    # Keep lobby widget identities/logic while giving the two-faction match room.
    for filename in ('lobby.yaml', 'lobby-players.yaml'):
        manifest = (mod / 'mod.yaml.in').read_text()
        manifest = manifest.replace(f'common|chrome/{filename}', f'omarchy|{filename}')
        (mod / 'mod.yaml.in').write_text(manifest)
        (mod / 'mod.yaml').write_text(manifest.replace('@OMARCHY_DLL@', str((mod / dll.name).resolve())))
    lobby = (engine / 'mods/common/chrome/lobby.yaml').read_text()
    lobby = lobby.replace('Width: 900', 'Width: 1040').replace('Height: 600', 'Height: 560')
    lobby = lobby.replace('Width: 675', 'Width: 755').replace('X: 695 - WIDTH', 'X: 775 - WIDTH')
    lobby = lobby.replace('Y: 67', 'Y: 90').replace('Height: 219', 'Height: 175')
    lobby = lobby.replace('Y: 285', 'Y: 270').replace('Y: 291', 'Y: 276')
    lobby = lobby.replace('Height: 259', 'Height: 210')
    lobby = lobby.replace('Button@START_GAME_BUTTON:', 'Button@START_GAME_BUTTON:\n\t\t\tBackground: omarchy-primary')
    lobby = lobby.replace('Label@SERVER_NAME:', 'Label@SERVER_NAME:\n\t\t\tVisible: False')
    lobby = lobby.replace('\tChildren:\n', '\tChildren:\n'
        '\t\tLabel@OMARCHY_TITLE:\n\t\t\tX: 24\n\t\t\tY: 16\n'
        '\t\t\tWidth: 700\n\t\t\tHeight: 30\n\t\t\tFont: BigBold\n'
        '\t\t\tTextColor: 9ECE6A\n\t\t\tText: omarchy-lobby-title\n'
        '\t\tLabel@OMARCHY_SUBTITLE:\n\t\t\tX: 24\n\t\t\tY: 46\n'
        '\t\t\tWidth: 700\n\t\t\tHeight: 20\n\t\t\tTextColor: A9B1A7\n'
        '\t\t\tText: omarchy-lobby-subtitle\n', 1)
    (mod / 'lobby.yaml').write_text(lobby)
    players = (engine / 'mods/common/chrome/lobby-players.yaml').read_text()
    players = re.sub(r'X: (410|420|478|560|617|619)\b', lambda m: f'X: {int(m[1]) + 70}', players)
    players = players.replace('Width: 140', 'Width: 210')
    players = players.replace('Container@FACTION:\n\t\t\t\t\t\t\tX: 270\n\t\t\t\t\t\t\tWidth: 160',
                              'Container@FACTION:\n\t\t\t\t\t\t\tX: 270\n\t\t\t\t\t\t\tWidth: 230')
    players = re.sub(r'(Label@FACTIONNAME:[\s\S]*?Width:) 70', r'\1 160', players)
    (mod / 'lobby-players.yaml').write_text(players)
    # Keep the pinned upstream widget layouts, changing only branded artwork references.
    player = (engine / 'mods/ra/chrome/ingame-player.yaml').read_text()
    player = player.replace('Logic: AddFactionSuffixLogic, IngameRadarDisplayLogic', 'Logic: IngameRadarDisplayLogic')
    player = player.replace('ImageCollection: sidebar\n\t\t\t\t\tImageName: radar',
                            'ImageCollection: omarchy-radar\n\t\t\t\t\tImageName: radar')
    (mod / 'ingame-player.yaml').write_text(player)
    save = (engine / 'mods/ra/chrome/gamesave-loading.yaml').read_text()
    save = save.replace('Background: loadscreen-stripe', 'Background: panel-bg')
    save = save.replace('ImageCollection: logos', 'ImageCollection: omarchy-brand')
    (mod / 'gamesave-loading.yaml').write_text(save)
    menu = (engine / 'mods/common/chrome/ingame-menu.yaml').read_text()
    menu = menu.replace('ImageCollection: logos', 'ImageCollection: omarchy-brand')
    (mod / 'ingame-menu.yaml').write_text(menu)
    # OpenRA's texture backend requires power-of-two sheet dimensions.
    cover = (mod / 'cover.png').read_bytes()
    if not cover.startswith(b'\x89PNG\r\n\x1a\n') or struct.unpack_from('>II', cover, 16) != (2048, 1024):
        raise RuntimeError('Loading screen must be a 2048x1024 PNG sheet')
    for filename, size in (('omarchy-icon.png', (256, 256)), ('omarchy-faction.png', (32, 16)), ('omarchy-panels.png', (256, 64)), ('installer.png', (1024, 512))):
        pixels = (mod / filename).read_bytes()
        if not pixels.startswith(b'\x89PNG\r\n\x1a\n') or struct.unpack_from('>II', pixels, 16) != size:
            raise RuntimeError(f'{filename} must be a {size[0]}x{size[1]} PNG sheet')
    # Reuse the stock content downloader, but return to Omarchy when it finishes.
    content_manifest = (engine / 'mods/ra-content/mod.yaml').read_text()
    content_manifest = content_manifest.replace('{DEV_VERSION}', 'release-20250330').replace('\tMod: ra\n', '\tMod: omarchy\n')
    content_manifest = content_manifest.replace('\t\t$ra-content: racontent', '\t\t$ra-content: racontent\n\t\t$omarchy-content: omarchycontent')
    content_manifest = content_manifest.replace('Chrome:\n\tcontent|chrome.yaml', 'Chrome:\n\tcontent|chrome.yaml\n\tomarchycontent|chrome.yaml')
    content_manifest = content_manifest.replace('ChromeLayout:\n\tcontent|content.yaml', 'ChromeLayout:\n\tomarchycontent|content.yaml')
    content_manifest = content_manifest.replace('Image: ^EngineDir|mods/common-content/chrome.png\n\tImage2x: ^EngineDir|mods/common-content/chrome-2x.png\n\tImage3x: ^EngineDir|mods/common-content/chrome-3x.png',
                                                'Image: ^EngineDir|mods/omarchy-content/installer.png')
    (content / 'mod.yaml').write_text(content_manifest)
    shutil.copyfile(mod / 'installer.png', content / 'installer.png')
    shutil.copyfile(ROOT / 'mod/ui/content-chrome.yaml', content / 'chrome.yaml')
    content_layout = (engine / 'mods/common-content/content.yaml').read_text()
    content_layout = content_layout.replace('Background: background\n', 'Background: omarchy-installer-background\n', 1)
    # Keep the poster title visible on the right while content setup is open.
    for panel in ('CONTENT_PANEL', 'PACKAGE_DOWNLOAD_PANEL', 'SOURCE_INSTALL_PANEL', 'CONTENT_PROMPT_PANEL'):
        needle = f'@{panel}:\n'
        start = content_layout.index(needle)
        x = content_layout.index('\tX: (WINDOW_WIDTH - WIDTH) / 2', start)
        content_layout = content_layout[:x] + '\tX: 8' + content_layout[x + len('\tX: (WINDOW_WIDTH - WIDTH) / 2'):]
    (content / 'content.yaml').write_text(content_layout)
    shutil.copyfile(engine / 'COPYING', mod / 'COPYING.OpenRA')
    (mod / 'SOURCE.txt').write_text('OpenRA manifest/content configuration: https://github.com/OpenRA/OpenRA/tree/release-20250330 (GPL-3.0-or-later).\nCustom menu source: https://github.com/tcballard/command-and-conquer-omarchy/tree/codex/omarchy-skirmish/mod (GPL-3.0-or-later).\nOmarchy emblem: https://omarchy.org/brand/omarchy-logo.svg (official brand artwork).\n')
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
