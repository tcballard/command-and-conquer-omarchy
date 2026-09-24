#!/usr/bin/env python3
"""Model action runner. Codex CLI or optional local Ollama; never logs model text."""
import argparse
import collections
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit

MAX_OBSERVATION = 2_000_000
MAX_RESPONSE = 131072
MAX_PROMPT = 24000
MODEL_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_./:-]{0,95}$')
ERRORS = {'configuration', 'provider_unavailable', 'provider_timeout', 'invalid_model_action',
          'context_limit', 'request_limit'}
ACTION_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['kind'],
    'properties': {
        'kind': {'type': 'string', 'enum': ['wait', 'deploy', 'produce', 'place', 'move', 'attack', 'defend', 'stop', 'set_rally']},
        'actor': {'type': 'string', 'pattern': '^[a-z0-9_.-]+$', 'maxLength': 64},
        'count': {'type': 'integer', 'const': 1},
        'group': {'type': 'array', 'items': {'type': 'integer', 'minimum': 1, 'maximum': 4294967295}, 'maxItems': 32, 'uniqueItems': True},
        'target': {'type': 'integer', 'minimum': 1, 'maximum': 4294967295},
        'cell': {'type': 'array', 'items': {'type': 'integer', 'minimum': -4096, 'maximum': 4096}, 'minItems': 2, 'maxItems': 2},
    },
}
SYSTEM = '''Play as green Omarchy and try to win Package Conflict against two Normal AI rivals.
Return exactly ONE JSON action matching the supplied schema. No prose, reasoning, tools or commands.
The game is authoritative and continues while you decide. Observations may omit actors when large;
only use IDs actually provided. Enemy entries are currently visible; never guess a hidden target.
Use prior result to correct rejected actions. Acceptance means dispatched, not completed.
Rules: deploy(group=[owned mcv]) starts a base. produce(actor,count=1) requires an empty queue,
available tech and enough cash. Never duplicate a queued item after a timeout. place(actor,cell)
uses a completed item and one supplied placement candidate. move(group,cell) uses owned mobile IDs
and explored terrain; attack(group,target) uses owned combat IDs and a visible target. defend(group,cell)
is attack-move, not a permanent defence zone. stop(group) stops mobile units. set_rally(group,cell)
requires a producer with rally support. wait is legal. Groups contain at most 32 IDs.
Build power (powr), refinery (proc), barracks (tent), then a war factory (weap). Keep power supplied,
harvesters safe, and train e1/e3 infantry and 1tnk vehicles when available. Defend recent attacks;
scout with a force and attack visible threats. Expand rather than endlessly waiting.
tech contains static prerequisite tokens, not hidden player state; production.available is the legal
current list. explored_rows are [y,first_x,last_x] inclusive runs; scout_cells are known frontier
candidates, not guaranteed passable destinations. Actor positions are [x,y].'''


class Failure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def config_path():
    return Path(os.environ.get('OMARCHY_AGENT_CONFIG') or
                Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) /
                'command-and-conquer-omarchy' / 'agent.json')


def validate_config(c):
    if not isinstance(c, dict) or set(c) - {'provider', 'model', 'endpoint', 'max_decisions'}:
        raise Failure('configuration')
    if c.get('provider') not in {'codex', 'ollama'} or not isinstance(c.get('model'), str) or not MODEL_NAME.fullmatch(c['model']):
        raise Failure('configuration')
    if c['model'] == 'default':
        raise Failure('configuration')
    limit = c.get('max_decisions', 1200)
    if type(limit) is not int or not 1 <= limit <= 10000:
        raise Failure('configuration')
    if c['provider'] == 'codex':
        if 'endpoint' in c:
            raise Failure('configuration')
        return dict(provider='codex', model=c['model'], max_decisions=limit)
    if 'cloud' in c['model'].lower():
        raise Failure('configuration')
    try:
        u = urlsplit(c.get('endpoint', 'http://127.0.0.1:11434'))
        host = '127.0.0.1' if u.hostname == 'localhost' else u.hostname
        if (u.scheme != 'http' or u.username or u.password or u.query or u.fragment or
                u.path not in ('', '/') or not ipaddress.ip_address(host).is_loopback):
            raise ValueError()
        port = u.port or 11434
        if not 1 <= port <= 65535:
            raise ValueError()
    except (ValueError, TypeError):
        raise Failure('configuration') from None
    limit = c.get('max_decisions', 1200)
    if type(limit) is not int or not 1 <= limit <= 10000:
        raise Failure('configuration')
    return dict(provider='ollama', model=c['model'], host=host, port=port, max_decisions=limit)


def load_config():
    try:
        with config_path().open() as f:
            raw = f.read(8193)
        if len(raw) > 8192:
            raise Failure('configuration')
        return validate_config(json.loads(raw))
    except (OSError, ValueError, TypeError):
        raise Failure('configuration') from None


class Ollama:
    def __init__(self, config):
        self.config = config

    def request(self, path, payload=None):
        # Direct HTTP avoids environment proxies, DNS and redirects. No auth headers.
        c = http.client.HTTPConnection(self.config['host'], self.config['port'], timeout=25)
        try:
            body = None if payload is None else json.dumps(payload).encode()
            c.request('GET' if payload is None else 'POST', path, body, {'Content-Type': 'application/json'})
            r = c.getresponse()
            if r.status != 200:
                raise Failure('provider_unavailable')
            data = r.read(MAX_RESPONSE + 1)
            if len(data) > MAX_RESPONSE:
                raise Failure('invalid_model_action')
            result = json.loads(data)
            if not isinstance(result, dict) or result.get('error'):
                raise Failure('provider_unavailable')
            return result
        except TimeoutError:
            raise Failure('provider_timeout') from None
        except (OSError, http.client.HTTPException):
            raise Failure('provider_unavailable') from None
        except (ValueError, UnicodeError, RecursionError):
            raise Failure('invalid_model_action') from None
        finally:
            c.close()

    def verify(self):
        data = self.request('/api/show', {'model': self.config['model']})
        if not isinstance(data.get('details'), dict):
            raise Failure('configuration')
        # A loopback Ollama instance can proxy cloud models. Refuse those explicitly.
        if data.get('remote_host') or data.get('remote_model') or data.get('details', {}).get('format') != 'gguf':
            raise Failure('configuration')
        if 'completion' not in data.get('capabilities', []):
            raise Failure('configuration')

    def decide(self, prompt):
        payload = dict(model=self.config['model'], stream=False, think=False, keep_alive='5m',
                       format=ACTION_SCHEMA, options=dict(temperature=0, num_predict=256, num_ctx=16384),
                       messages=[dict(role='system', content=SYSTEM), dict(role='user', content=prompt)])
        data = self.request('/api/chat', payload)
        try:
            if data.get('done') is not True or data.get('done_reason') == 'length':
                raise ValueError()
            content = data['message']['content']
            if not isinstance(content, str) or len(content) > 8192 or data['message'].get('tool_calls'):
                raise ValueError()
            return validate_action(json.loads(content))
        except (KeyError, TypeError, ValueError, RecursionError):
            raise Failure('invalid_model_action') from None


def validate_action(a):
    if not isinstance(a, dict) or set(a) - set(ACTION_SCHEMA['properties']):
        raise ValueError('action fields')
    kind = a.get('kind')
    if kind not in ACTION_SCHEMA['properties']['kind']['enum']:
        raise ValueError('kind')
    if 'actor' in a and (not isinstance(a['actor'], str) or not re.fullmatch(r'[a-z0-9_.-]{1,64}', a['actor'])):
        raise ValueError('actor')
    if 'count' in a and (type(a['count']) is not int or a['count'] != 1):
        raise ValueError('count')
    group = a.get('group', [])
    if (not isinstance(group, list) or len(group) > 32 or
            any(type(i) is not int or not 1 <= i <= 4294967295 for i in group) or len(set(group)) != len(group)):
        raise ValueError('group')
    if 'cell' in a and (not isinstance(a['cell'], list) or len(a['cell']) != 2 or
                        any(type(i) is not int or abs(i) > 4096 for i in a['cell'])):
        raise ValueError('cell')
    if 'target' in a and (type(a['target']) is not int or not 1 <= a['target'] <= 4294967295):
        raise ValueError('target')
    if kind in {'produce', 'place'} and not a.get('actor'):
        raise ValueError('missing actor')
    if kind in {'deploy', 'move', 'attack', 'defend', 'stop', 'set_rally'} and not group:
        raise ValueError('missing group')
    if kind in {'place', 'move', 'defend', 'set_rally'} and 'cell' not in a:
        raise ValueError('missing cell')
    if kind == 'attack' and 'target' not in a:
        raise ValueError('missing target')
    return a


def compact(o):
    """Only select game-supplied fields. Never forward the session token to a model."""
    own = o['own']
    origin = next((u['cell'] for u in own if u['actor'] == 'fact'), own[0]['cell'] if own else [0, 0])
    distance = lambda c: (c[0] - origin[0]) ** 2 + (c[1] - origin[1]) ** 2
    cells = {tuple(c) for c in o['explored']}
    rows = []
    for x, y in sorted(cells, key=lambda c: (c[1], c[0])):
        if rows and rows[-1][0] == y and rows[-1][2] == x - 1:
            rows[-1][2] = x
        else:
            rows.append([y, x, x])
    frontier = sorted((c for c in cells if any((c[0]+dx, c[1]+dy) not in cells
                      for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)))), key=lambda c: (-distance(c), c))
    scouts = []
    for c in frontier:
        if all((c[0]-s[0])**2 + (c[1]-s[1])**2 >= 36 for s in scouts):
            scouts.append(c)
            if len(scouts) == 16:
                break
    snapshot = dict(tick=o['tick'], cash=o['cash'], power=o['power'], result=o['result'],
                    own=own[:96], own_counts=dict(collections.Counter(u['actor'] for u in own)),
                    enemies=sorted(o['enemies'], key=lambda u: (distance(u['cell']), u['id']))[:32],
                    production=o['production'], placements={k: v[:6] for k, v in o['placements'].items()},
                    recent_attacks=o.get('recent_attacks', [])[-8:], tech=o.get('tech', []),
                    explored_rows=rows[:256], scout_cells=scouts,
                    omitted=dict(own=max(0, len(own)-96), enemies=max(0, len(o['enemies'])-32),
                                 explored_runs=max(0, len(rows)-256)))
    prompt = json.dumps(snapshot, separators=(',', ':'))
    if len(prompt.encode()) + len(SYSTEM.encode()) > MAX_PROMPT:
        raise Failure('context_limit')
    return prompt


def serve(config, provider, source=sys.stdin, sink=sys.stdout):
    token = os.environ['OMARCHY_AGENT_TOKEN']
    previous = 0
    decisions = 0
    verified = False
    while True:
        line = source.readline(MAX_OBSERVATION + 1)
        if not line:
            return 0
        if len(line) > MAX_OBSERVATION or not line.endswith('\n'):
            return 2
        try:
            o = json.loads(line)
            if o['version'] != 1 or o['token'] != token or type(o['request']) is not int or o['request'] <= previous:
                return 2
            previous = o['request']
            reply = dict(version=1, token=token, request=previous)
            started = time.monotonic()
            try:
                if (os.environ.get('OMARCHY_AGENT_MODEL', config['model']) != config['model'] or
                        os.environ.get('OMARCHY_AGENT_MODE', config.get('provider')) != config.get('provider')):
                    raise Failure('configuration')
                if decisions >= config['max_decisions']:
                    raise Failure('request_limit')
                if not verified:
                    provider.verify()
                    verified = True
                prompt = compact(o)
                decisions += 1
                reply['action'] = provider.decide(prompt)
                reply['metrics'] = dict(input_bytes=len(prompt.encode()), elapsed_ms=int((time.monotonic()-started)*1000))
            except Failure as error:
                reply['error'] = error.code
            print(json.dumps(reply, separators=(',', ':')), file=sink, flush=True)
            if 'error' in reply:
                return 2
        except (ValueError, KeyError, TypeError, RecursionError):
            return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--init', choices=['codex', 'ollama'], help='Create provider config; never overwrite.')
    parser.add_argument('--model', default='default', help='Explicit model ID, required when creating configuration.')
    mode.add_argument('--check', action='store_true', help='Verify local model and exercise a structured reply before play.')
    mode.add_argument('--launch', type=Path, metavar='BUNDLE', help='Check setup and launch the bundled game.')
    args = parser.parse_args()
    try:
        if args.init:
            c = dict(provider=args.init, model=args.model, max_decisions=1200)
            if args.init == 'ollama':
                if args.model == 'default':
                    raise Failure('configuration')
                c['endpoint'] = 'http://127.0.0.1:11434'
            validate_config(c)
            path = config_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f:
                json.dump(c, f, indent=2)
                f.write('\n')
            print('Created agent configuration. Run --check before launching.')
            return 0
        config = load_config()
        if config['provider'] == 'codex':
            from codex_provider import Codex
            provider = Codex(config)
        else:
            provider = Ollama(config)
        if args.check or args.launch:
            provider.verify()
            if provider.decide('Setup check only. Return exactly {"kind":"wait"}.') != {'kind': 'wait'}:
                raise Failure('invalid_model_action')
            print(f"Ready: {config['provider']} / {config['model']} (experimental)", flush=True)
            if args.launch:
                bundle = args.launch.resolve()
                if not (bundle / 'OpenRA').is_file() or not (bundle / 'agent-player/model_runner.py').is_file():
                    raise Failure('configuration')
                env = dict(os.environ, OMARCHY_AGENT_MODE=config['provider'], OMARCHY_AGENT_MODEL=config['model'],
                           OMARCHY_AGENT_CONFIG=str(config_path().resolve()))
                env.pop('OMARCHY_AGENT_TEST', None)
                env.pop('OMARCHY_AGENT_SELFTEST', None)
                os.chdir(bundle)
                os.execve(str(bundle / 'OpenRA'), [str(bundle / 'OpenRA'), 'Game.Mod=omarchy'], env)
            return 0
        return serve(config, provider)
    except (Failure, OSError) as error:
        code = error.code if isinstance(error, Failure) else 'configuration'
        # Fixed codes only: never print provider response bodies, prompts or credentials.
        print(f'Agent setup failed: {code}. See docs/agent-model.md.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    # Keep shared exception types identical when the provider imports this module.
    sys.modules['model_runner'] = sys.modules[__name__]
    sys.exit(main())
