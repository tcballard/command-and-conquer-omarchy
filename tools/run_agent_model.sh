#!/bin/sh
# Developer-only model controller; preflight must succeed before the game opens.
set -eu
bundle=$(cd "${1:?Usage: tools/run_agent_model.sh /path/to/bundle}" && pwd)
command -v python3 >/dev/null
[ -f "$bundle/agent-player/model_runner.py" ] || { echo 'Build the model-adapter branch bundle first.' >&2; exit 1; }
exec python3 "$bundle/agent-player/model_runner.py" --launch "$bundle"
