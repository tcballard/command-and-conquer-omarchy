#!/usr/bin/env python3
"""Real-client deterministic bridge smoke. Run under Xvfb; retain evidence on failure."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import zipfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument('bundle', type=Path)
    p.add_argument('--content', type=Path, required=True)
    p.add_argument('--evidence', type=Path, default=Path('build/agent-evidence'))
    p.add_argument('--seconds', type=int, default=480)
    a = p.parse_args()
    bundle, out = a.bundle.resolve(), a.evidence.resolve()
    out.mkdir(parents=True, exist_ok=True)
    support = out / 'support'
    with zipfile.ZipFile(a.content) as z:
        z.extractall(support / 'Content/ra/v2')
    env = dict(os.environ, OMARCHY_AGENT_TEST='1', OMARCHY_AGENT_SELFTEST='1', SDL_VIDEODRIVER='x11',
               SDL_AUDIODRIVER='dummy', ALSOFT_DRIVERS='null', LIBGL_ALWAYS_SOFTWARE='1')
    command = [str(bundle / 'OpenRA'), 'Game.Mod=omarchy', f'Engine.SupportDir={support}',
               'Graphics.Mode=Windowed', 'Graphics.WindowedSize=1280,800', 'Graphics.UIScale=1',
               'Game.FetchNews=false', 'Debug.CheckVersion=false']
    video = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'x11grab', '-video_size', '1280x800',
                              '-framerate', '8', '-i', os.environ['DISPLAY'], '-c:v', 'libx264', '-preset', 'ultrafast',
                              '-crf', '30', str(out / 'gameplay.mp4')])
    with (out / 'client.log').open('w') as log:
        game = subprocess.Popen(command, cwd=bundle, env=env, stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + a.seconds
        stalled = resumed = False
        rows = []
        try:
            while time.monotonic() < deadline:
                if game.poll() is not None:
                    raise RuntimeError(f'Client exited unexpectedly: {game.returncode}')
                files = list((support / 'AgentPlayer').glob('*.jsonl'))
                if files:
                    rows = []
                    for line in files[0].read_text().splitlines():
                        try: rows.append(json.loads(line))
                        except json.JSONDecodeError: pass
                states = [r for r in rows if r['type'] == 'state']
                if states and states[-1]['own'].get('proc', 0) and not stalled:
                    # Stop the actual supervised child; the game must time out without blocking rendering.
                    children = subprocess.check_output(['pgrep', '-P', str(game.pid)], text=True).split()
                    for child in children:
                        os.kill(int(child), signal.SIGSTOP)
                    stalled = True
                if any(r['type'] == 'disconnect' for r in rows) and not resumed:
                    subprocess.run(['xdotool', 'mousemove', '90', '148', 'click', '1'], check=True)
                    resumed = True
                if any(r['type'] == 'summary' for r in rows):
                    break
                time.sleep(1)
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'x11grab', '-video_size', '1280x800',
                            '-i', os.environ['DISPLAY'], '-frames:v', '1', str(out / 'gameplay.png')], check=True)
            subprocess.run(['xdotool', 'mousemove', '245', '148', 'click', '1'], check=True)
            game.wait(timeout=15)
        finally:
            if game.poll() is None: game.terminate(); game.wait(timeout=15)
            video.send_signal(signal.SIGINT)
            video.wait(timeout=15)
    files = list((support / 'AgentPlayer').glob('*.jsonl'))
    rows = [json.loads(s) for s in files[0].read_text().splitlines()] if files else []
    states = [r for r in rows if r['type'] == 'state']
    actions = [r for r in rows if r['type'] == 'action']
    checks = {r['name'] for r in rows if r['type'] == 'check' and r['passed']}
    assert rows and sorted(rows[0]['slots'], key=lambda s: s['slot']) == [
        {'slot': 'Multi0', 'bot': 'omarchy-agent-test', 'spawn': 1, 'faction': 'allies'},
        {'slot': 'Multi1', 'bot': 'normal', 'spawn': 2, 'faction': 'soviet'},
        {'slot': 'Multi2', 'bot': 'normal', 'spawn': 3, 'faction': 'russia'}], rows[:1]
    assert any(s['own'].get('powr') and s['own'].get('proc') and s['own'].get('e1') for s in states), 'No actual base and infantry'
    assert {'attack', 'defend'} <= {r['kind'] for r in actions}, 'Missing combat orders'
    assert {'stale-id', 'invalid-target', 'hidden-target', 'foreign-unit', 'fog-observation', 'blocked-placement'} <= checks, checks
    assert stalled and resumed and any(r['type'] == 'resume' for r in rows), 'Disconnect recovery failed'
    assert any(r['type'] == 'summary' for r in rows), 'No stopped/result summary'
    assert not list((support / 'Logs').glob('exception*.log')), 'Engine exception'
    print('Real client: correct factions, construction, troops, combat, safety checks and timeout/resume verified.')


if __name__ == '__main__':
    main()
