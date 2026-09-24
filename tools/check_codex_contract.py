#!/usr/bin/env python3
"""Real pinned Codex CLI + fake Responses endpoint. No credentials or real inference."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent-player'))
from codex_provider import command, clean_environment


def main():
    requests = []
    violations = []
    with tempfile.TemporaryDirectory(prefix='omarchy-cli-contract-') as tmp:
        forbidden = Path(tmp) / 'must-not-exist'
        final = dict(kind='wait', actor=None, group=[], cell=None, target=None, count=1)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append(data)
                # Inspect the real model-facing surface, not just command-line strings.
                def names(tools):
                    result = []
                    for t in tools:
                        if t.get('type') == 'namespace':
                            result.extend(names(t.get('tools', [])))
                        else:
                            result.append(t.get('name', t.get('type')))
                    return result
                exposed = names(data.get('tools', []))
                allowed = {'apply_patch', 'update_plan', 'request_user_input', 'get_current_time', 'get_remaining_context'}
                violations.extend(n for n in exposed if n not in allowed)
                if len(requests) == 1:
                    # An unsolicited command must not execute; a file edit must be denied.
                    items = [dict(type='function_call', id='fc1', call_id='exec1', name='exec_command',
                                  arguments=json.dumps({'cmd': 'touch ' + str(forbidden)})),
                             dict(type='custom_tool_call', id='fc2', call_id='patch1', name='apply_patch',
                                  input=f'*** Begin Patch\n*** Add File: {forbidden}\n+forbidden\n*** End Patch')]
                else:
                    items = [dict(type='message', id='msg1', role='assistant',
                                  content=[dict(type='output_text', text=json.dumps(final))])]
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                events = [('response.created', {'response': {'id': 'resp1'}})]
                events += [('response.output_item.done', {'output_index': i, 'item': item}) for i, item in enumerate(items)]
                events.append(('response.completed', {'response': {'id': 'resp1', 'status': 'completed', 'output': items,
                              'usage': {'input_tokens': 10, 'output_tokens': 10, 'total_tokens': 20}}}))
                for name, payload in events:
                    payload['type'] = name
                    self.wfile.write(f'event: {name}\ndata: {json.dumps(payload)}\n\n'.encode())

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            args = command('codex', Path(__file__).resolve().parents[1] / 'agent-player/codex-action.schema.json', 'gpt-5.4')
            # Fake provider override belongs only to this CI fixture, never the shipped launcher.
            args[-1:-1] = ['-c', 'model_provider="fixture"', '-c',
                          'model_providers.fixture=' + '{name="Fixture",base_url="http://127.0.0.1:' + str(server.server_port) + '/v1",wire_api="responses",requires_openai_auth=false}',
                          '-c', 'features.responses_websockets=false', '-c', 'features.responses_websockets_v2=false']
            env = clean_environment()
            for key in ('OPENAI_API_KEY', 'CODEX_API_KEY'):
                env.pop(key, None)
            result = subprocess.run(args, cwd=tmp, input='Return exactly the wait action JSON; use no tools.',
                                    text=True, capture_output=True, timeout=45, env=env)
            if result.returncode:
                # CLI diagnostics are from this credential-free fixture only.
                raise RuntimeError(result.stderr[-4000:])
            assert json.loads(result.stdout) == final, 'Structured output contract failed'
            assert not violations, f'Unexpected tools exposed: {sorted(set(violations))}'
            assert not forbidden.exists(), 'Codex performed an OS mutation'
            assert len(requests) >= 2, 'Injected tool calls were not exercised'
            print('Pinned Codex CLI: structured output, restricted tools and denied OS actions passed (fake provider).')
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    main()
