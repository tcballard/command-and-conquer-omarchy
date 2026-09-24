"""Codex CLI provider using saved CLI auth; no access-token extraction or API shim."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile

# Pinned command contract; another CLI version requires compatibility review.
SUPPORTED_VERSION = '0.156.1'
DISABLED = ('shell_tool', 'unified_exec', 'shell_snapshot', 'shell_snapshot_v2',
            'apps', 'plugins', 'hooks', 'codex_hooks', 'plugin_hooks', 'js_repl',
            'code_mode', 'code_mode_only', 'code_mode_host', 'deferred_executor',
            'multi_agent', 'multi_agent_v2', 'collab', 'computer_use', 'browser_use',
            'image_generation', 'memories', 'memory_tool', 'tool_suggest',
            'skill_mcp_dependency_install', 'remote_control')


def command(executable, schema, model):
    args = [executable, 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
            '--sandbox', 'read-only', '--output-schema', str(schema),
            '-c', 'approval_policy="never"', '-c', 'web_search="disabled"',
            '-c', 'project_doc_max_bytes=0', '-c', 'skills.include_instructions=false',
            '-c', 'features.skip_host_skill_discovery=true', '-c', 'features.view_image=false',
            '-c', 'notify=[]', '-c', 'model_reasoning_effort="low"']
    for feature in DISABLED:
        args.extend(['-c', f'features.{feature}=false'])
    if model != 'default':
        args.extend(['--model', model])
    # A literal '-' reads the bounded prompt from stdin, never a shell command line.
    return args + ['-']


def clean_environment():
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith('OMARCHY_AGENT_'):
            del env[key]
    return env


class Codex:
    def __init__(self, config):
        self.config = config
        self.executable = shutil.which('codex')

    def verify(self):
        from model_runner import Failure
        if not self.executable:
            raise Failure('configuration')
        try:
            version = subprocess.run([self.executable, '--version'], capture_output=True, timeout=5,
                                     env=clean_environment(), check=True)
            if not re.fullmatch(rb'codex-cli 0\.156\.1\s*', version.stdout):
                raise Failure('configuration')
            subprocess.run([self.executable, 'login', 'status'], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5, env=clean_environment(), check=True)
        except (OSError, subprocess.SubprocessError):
            raise Failure('configuration') from None

    def decide(self, prompt):
        from model_runner import Failure, SYSTEM, validate_action
        # A private empty cwd avoids loading repository instructions or granting a workspace.
        # Existing Codex auth stays in its normal secure store, handled only by Codex.
        with tempfile.TemporaryDirectory(prefix='omarchy-codex-') as directory:
            schema = Path(__file__).with_name('codex-action.schema.json').resolve()
            args = command(self.executable, schema, self.config['model'])
            process = None
            try:
                process = subprocess.Popen(args, cwd=directory, env=clean_environment(),
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=subprocess.DEVNULL, start_new_session=True)
                output, _ = process.communicate((SYSTEM + '\n\n' + prompt).encode(), timeout=25)
                if process.returncode:
                    raise Failure('provider_unavailable')
                if len(output) > 8192:
                    raise Failure('invalid_model_action')
                action = json.loads(output)
                if not isinstance(action, dict):
                    raise ValueError()
                return validate_action({k: v for k, v in action.items() if v is not None})
            except subprocess.TimeoutExpired:
                raise Failure('provider_timeout') from None
            except (OSError, subprocess.SubprocessError):
                raise Failure('provider_unavailable') from None
            except (ValueError, TypeError, RecursionError):
                raise Failure('invalid_model_action') from None
            finally:
                if process is not None:
                    try:
                        # Kill the owned process group, including any remaining CLI children.
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
