#!/usr/bin/env python3
"""Deterministic test bot. No model, network, shell, hidden state or credentials."""
import json
import os
import sys


def choose(o):
    own = o['own']
    by_type = {}
    for u in own:
        by_type.setdefault(u['actor'], []).append(u)
    if 'mcv' in by_type and 'fact' not in by_type:
        return dict(kind='deploy', group=[by_type['mcv'][0]['id']])
    for actor, cells in o['placements'].items():
        if cells:
            return dict(kind='place', actor=actor, cell=cells[0])
    queue = {p['queue']: p for p in o['production']}
    available = {a['actor']: (a['cost'], p) for p in o['production'] for a in p['available']}
    plan = [('powr', 1), ('proc', 1), ('tent', 1), ('powr', 2), ('weap', 1), ('proc', 2), ('powr', 3)]
    for actor, count in plan:
        if len(by_type.get(actor, [])) >= count:
            continue
        if actor in available:
            cost, q = available[actor]
            if not q['items'] and cost <= o['cash']:
                return dict(kind='produce', actor=actor)
        break
    troops = [u for u in own if u['mobile'] and u['combat'] and u['actor'] != 'harv']
    home = by_type.get('fact', [{'cell': [18, 18]}])[0]['cell']
    threats = sorted(o['enemies'], key=lambda e: distance(e['cell'], home))
    if troops and o.get('recent_attacks') and o['request'] % 3 == 1:
        return dict(kind='defend', group=[u['id'] for u in troops[:32]], cell=o['recent_attacks'][-1]['cell'])
    if threats and troops:
        target = threats[0]
        if o['request'] % 3 == 0:
            return dict(kind='attack', group=[u['id'] for u in troops[:32]], target=target['id'])
        if distance(target['cell'], home) < 225 and o['request'] % 3 == 1:
            return dict(kind='defend', group=[u['id'] for u in troops[:32]], cell=target['cell'])
    for actor, cap in [('e1', 16), ('e3', 6), ('1tnk', 6)]:
        if actor in available and len(by_type.get(actor, [])) < cap:
            cost, q = available[actor]
            if not q['items'] and cost <= o['cash'] - 300:
                return dict(kind='produce', actor=actor)
    # Advance only to known terrain. Sight expands the next frontier; no enemy coordinates are assumed.
    if len(troops) >= 6 and o['request'] % 8 == 0:
        scouting = troops[3:]
        goal = [75, 70] if max(u['cell'][0] for u in scouting) >= 44 else [48, 48]
        cells = o['explored']
        if cells:
            cell = min(cells, key=lambda c: distance(c, goal))
            return dict(kind='defend', group=[u['id'] for u in scouting[:32]], cell=cell)
    return dict(kind='wait')


def distance(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def main():
    token = os.environ['OMARCHY_AGENT_TOKEN']
    for line in sys.stdin:
        if len(line) > 2_000_000:
            return 2
        observation = json.loads(line)
        if observation['version'] != 1 or observation['token'] != token:
            return 2
        action = choose(observation)
        print(json.dumps(dict(version=1, token=token, request=observation['request'], action=action)), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
