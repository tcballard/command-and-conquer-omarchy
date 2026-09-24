#!/bin/sh
# Developer-only deterministic controller. Not a model-backed agent.
set -eu
bundle=$(cd "${1:?Usage: tools/run_agent_test.sh /path/to/bundle}" && pwd)
command -v python3 >/dev/null
[ -f "$bundle/agent-player/test_adapter.py" ] || { echo 'Build a bundle from the agent-player feature branch first.' >&2; exit 1; }
shift
cd "$bundle"
export OMARCHY_AGENT_TEST=1
exec ./OpenRA Game.Mod=omarchy "$@"
