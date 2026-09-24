import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent-player'))
import model_runner as runner
import codex_provider as codex


class ModelRunnerTests(unittest.TestCase):
    def observation(self, request=1):
        return dict(version=1, token='private-token', request=request, tick=100, cash=5000,
                    power=dict(provided=100, used=0), result={'accepted': True},
                    own=[dict(id=7, actor='mcv', cell=[18, 73], mobile=True, combat=False)],
                    enemies=[], production=[], placements={}, explored=[[18, 73], [19, 73], [20, 73]],
                    recent_attacks=[], tech=[])

    def test_config_accepts_explicit_codex_and_local_ollama(self):
        self.assertEqual(runner.validate_config(dict(provider='codex', model='my-codex-model'))['provider'], 'codex')
        self.assertEqual(runner.validate_config(dict(provider='ollama', model='my-local-model'))['host'], '127.0.0.1')

    def test_config_rejects_remote_redirect_credentials_and_arbitrary_fields(self):
        for endpoint in ['https://example.org', 'http://evil.local', 'http://127.0.0.1/path',
                         'http://user:secret@127.0.0.1', 'http://127.0.0.1?secret=x', 'http://127.0.0.1:99999']:
            with self.subTest(endpoint=endpoint), self.assertRaises(runner.Failure):
                runner.validate_config(dict(provider='ollama', model='local', endpoint=endpoint))
        for config in [dict(provider='codex', model='x', api_key='secret'),
                       dict(provider='ollama', model='x-cloud'), dict(provider='codex', model='x', max_decisions=True),
                       dict(provider='codex', model='x', endpoint='http://127.0.0.1'),
                       dict(provider='codex', model='$(shell)'), dict(provider='codex', model='default')]:
            with self.subTest(config=config), self.assertRaises(runner.Failure):
                runner.validate_config(config)

    def test_prompt_drops_session_token_and_compresses_known_cells(self):
        o = self.observation()
        o['secret_extra'] = 'not-for-model'
        prompt = runner.compact(o)
        self.assertNotIn('private-token', prompt)
        self.assertNotIn('not-for-model', prompt)
        data = json.loads(prompt)
        self.assertEqual(data['explored_rows'], [[73, 18, 20]])
        self.assertTrue(all(c in o['explored'] for c in data['scout_cells']))

    def test_large_observation_is_explicitly_bounded(self):
        o = self.observation()
        o['own'] *= 200
        compact = json.loads(runner.compact(o))
        self.assertEqual(len(compact['own']), 96)
        self.assertEqual(compact['omitted']['own'], 104)
        o['production'] = ['x' * 25000]
        with self.assertRaisesRegex(runner.Failure, 'context_limit'):
            runner.compact(o)

    def test_model_action_rejects_text_commands_and_wrong_types(self):
        for action in ['narration', {'kind': 'shell'}, {'kind': 'wait', 'reasoning': 'secret'},
                       {'kind': 'produce', 'actor': 'powr', 'count': True},
                       {'kind': 'move', 'group': [1], 'cell': [True, 2]},
                       {'kind': 'attack', 'group': [1, 1], 'target': 5},
                       {'kind': 'attack', 'group': [1], 'target': 0}, {'kind': 'move', 'group': [1]},
                       {'kind': 'produce'}, {'kind': 'stop', 'group': [1] * 33}]:
            with self.subTest(action=action), self.assertRaises(ValueError):
                runner.validate_action(action)

    def run_session(self, provider, observations, limit=4):
        source = io.StringIO(''.join(json.dumps(o) + '\n' for o in observations))
        output = io.StringIO()
        with patch.dict(os.environ, {'OMARCHY_AGENT_TOKEN': 'private-token'}, clear=True):
            status = runner.serve(dict(model='chosen', max_decisions=limit), provider, source, output)
        return status, [json.loads(s) for s in output.getvalue().splitlines()]

    def test_same_protocol_with_real_provider_boundary_and_no_token_forwarding(self):
        provider = Mock()
        provider.decide.return_value = dict(kind='deploy', group=[7])
        code, replies = self.run_session(provider, [self.observation()])
        self.assertEqual(code, 0)
        self.assertEqual(replies[0]['action'], dict(kind='deploy', group=[7]))
        self.assertEqual(replies[0]['token'], 'private-token')
        self.assertNotIn('private-token', provider.decide.call_args.args[0])
        provider.verify.assert_called_once()

    def test_provider_failure_stops_without_retry_or_test_bot(self):
        provider = Mock()
        provider.decide.side_effect = runner.Failure('provider_timeout')
        code, replies = self.run_session(provider, [self.observation(), self.observation(2)])
        self.assertEqual(code, 2)
        self.assertEqual(replies[0]['error'], 'provider_timeout')
        self.assertNotIn('action', replies[0])
        provider.decide.assert_called_once()

    def test_duplicate_request_and_wrong_session_never_reach_provider(self):
        provider = Mock()
        provider.decide.return_value = dict(kind='wait')
        code, replies = self.run_session(provider, [self.observation(), self.observation()])
        self.assertEqual(code, 2)
        self.assertEqual(len(replies), 1)
        provider.decide.assert_called_once()
        o = self.observation(); o['token'] = 'another-session'
        provider.reset_mock()
        self.assertEqual(self.run_session(provider, [o]), (2, []))
        provider.decide.assert_not_called()

    def test_request_budget_stops_instead_of_hiding_quota(self):
        provider = Mock(); provider.decide.return_value = dict(kind='wait')
        _, replies = self.run_session(provider, [self.observation(), self.observation(2)], limit=1)
        self.assertEqual(replies[-1]['error'], 'request_limit')
        provider.decide.assert_called_once()

    def test_ollama_rejects_cloud_proxy_even_on_loopback(self):
        provider = runner.Ollama(dict(model='local'))
        with patch.object(provider, 'request', return_value=dict(remote_host='https://cloud', details={'format': 'gguf'})):
            with self.assertRaisesRegex(runner.Failure, 'configuration'):
                provider.verify()

    def test_ollama_never_accepts_truncated_or_tool_response(self):
        provider = runner.Ollama(dict(model='local'))
        for response in [dict(done=False), dict(done=True, done_reason='length'),
                         dict(done=True, message={'content': '{}', 'tool_calls': ['tool']}),
                         dict(done=True, message={'content': 'not json'})]:
            with patch.object(provider, 'request', return_value=response), self.assertRaises(runner.Failure):
                provider.decide('observation')

    def test_codex_command_uses_stdin_saved_auth_and_restricts_tools(self):
        argv = codex.command('/usr/bin/codex', '/fixed/schema.json', 'chosen-model')
        self.assertIn('--ignore-user-config', argv)
        self.assertIn('--ephemeral', argv)
        self.assertIn('features.shell_tool=false', argv)
        self.assertIn('features.apps=false', argv)
        self.assertIn('features.plugins=false', argv)
        self.assertIn('read-only', argv)
        self.assertEqual(argv[-1], '-')
        self.assertNotIn('--ignore-rules', argv)
        with patch.dict(os.environ, {'OMARCHY_AGENT_TOKEN': 'secret'}):
            self.assertNotIn('OMARCHY_AGENT_TOKEN', codex.clean_environment())

    def test_codex_timeout_kills_owned_process_group(self):
        provider = codex.Codex(dict(model='chosen-model')); provider.executable = '/usr/bin/codex'
        process = Mock(pid=9876)
        process.communicate.side_effect = subprocess.TimeoutExpired('codex', 25)
        with patch.object(subprocess, 'Popen', return_value=process), patch.object(os, 'killpg') as kill:
            with self.assertRaisesRegex(runner.Failure, 'provider_timeout'):
                provider.decide('state')
            kill.assert_called_once_with(9876, 9)
            process.wait.assert_called_once()

    def test_init_does_not_overwrite_existing_config(self):
        script = Path(runner.__file__)
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, OMARCHY_AGENT_CONFIG=str(Path(d)/'agent.json'))
            result = subprocess.run([sys.executable, str(script), '--init', 'codex', '--model', 'chosen'], env=env, capture_output=True)
            self.assertEqual(result.returncode, 0)
            original = Path(env['OMARCHY_AGENT_CONFIG']).read_bytes()
            result = subprocess.run([sys.executable, str(script), '--init', 'codex', '--model', 'other'], env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(Path(env['OMARCHY_AGENT_CONFIG']).read_bytes(), original)

    def test_preflight_accepts_codex_required_empty_fields(self):
        provider = Mock()
        provider.decide.return_value = dict(kind='wait', group=[], count=1)
        with patch.object(runner, 'load_config', return_value=dict(provider='codex', model='chosen')), \
             patch.object(codex, 'Codex', return_value=provider), \
             patch.object(sys, 'argv', ['runner', '--check']), patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(runner.main(), 0)
