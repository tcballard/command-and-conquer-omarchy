# Agent Player: Codex adapter (experimental)

This developer branch connects the validated game bridge to **Codex CLI**, using
its existing authentication and an explicitly chosen model. The separate
deterministic test bot remains available. No production menu option or release
is added. The target-XPS full-match gate is still outstanding.

## Setup and launch

Use the model-adapter branch's bundled build, not the v0.1.0 release. Python 3 and
Codex CLI **0.156.1** are required for the reviewed command contract. Sign in with
`codex login` on the same user account if you have not already done so. The runner
never reads, copies or exports Codex tokens. Your account's model availability
and usage limits apply; this is not an unlimited or offline Codex mode.

Choose the exact model ID available to your Codex account. The adapter will not
silently substitute another model. From the repository:

```sh
python3 agent-player/model_runner.py --init codex --model YOUR_CODEX_MODEL_ID
python3 agent-player/model_runner.py --check
tools/run_agent_model.sh /absolute/path/to/build/bundle
```

Replace `YOUR_CODEX_MODEL_ID` with your chosen ID. `--init` creates, and never
overwrites, `$XDG_CONFIG_HOME/command-and-conquer-omarchy/agent.json` (default
`~/.config/command-and-conquer-omarchy/agent.json`), mode 0600:

```json
{"provider":"codex","model":"YOUR_CODEX_MODEL_ID","max_decisions":1200}
```

`OMARCHY_AGENT_CONFIG` can select another config file. Do not put credentials in
it. To change providers or models, edit this configuration and start a new match.
The running match checks that its selected model has not changed on reconnect.

`--check` makes one real inference request to verify a structured wait action.
Launch repeats that check before opening the game. It requires a working account
and consumes normal provider usage. Failure leaves the game unopened.

The panel identifies `codex / <model>`, shows the last accepted decision and
supports Pause, Resume and Stop. Manual takeover is still deferred. A completed
match records OpenRA's real result; Stop records an unfinished match.

## Boundaries and timing

Codex is invoked directly, never through a model-generated shell command. Each
request uses a private empty working directory, `--ignore-user-config`,
`--ephemeral`, read-only sandbox and no approvals. Shell/exec, apps, plugins,
hooks, browser/computer use, image viewing, web search, memory and subagents are
disabled for these invocations. Existing exec-policy rules and managed restrictions
are not bypassed. Conflicting restrictions must fail setup. Personal Codex config
is not modified; the runner supplies its own narrow invocation options while
Codex retains control of authentication. File-edit requests remain denied by the
read-only sandbox. The CI contract test exercises unsolicited command/edit calls.

Only compact Omarchy-visible state goes to the selected provider. The session
pipe token is stripped before inference. The model returns a single JSON action,
which must pass runner shape checks and the existing authoritative game checks.
No free-form model text or reasoning is shown as narration or written to logs.
For Codex, this game state is sent to the configured OpenAI service; ephemeral
CLI mode prevents local rollout persistence, not provider-side retention.

Observations are compacted to at most 96 owned actors and 32 visible enemies,
with omitted counts, owned totals, recent attacks, available production,
static building prerequisite tokens, legal placement candidates and explored
terrain runs. Context has a 24,000-byte ceiling; overflow pauses rather than
silently truncating a JSON prompt. Static prerequisites are informational;
`production.available` and the game resolver determine legal builds.

The game allows one in-flight decision, at least 25 ticks and two wall-clock
seconds between requests. The CLI/provider has a 25-second deadline; the game
has a 30-second/750-tick ceiling. These are initial bounded settings, not yet
XPS-tuned values. No automatic retry or fallback occurs. A timeout, malformed
response, disconnected runner or request-budget exhaustion pauses the controller.
Resume creates a fresh session and a new per-runner decision budget; it does not
retry an old action. Existing unit activities and production continue during a
pause. Stop terminates the runner and its descendants.

The audit records provider/model, action results, fixed failure codes, context
byte counts, decision latency, disconnects and the actual outcome. It does not
record tokens, prompts, model output or Codex diagnostic text.

## Optional Ollama adapter

For an already installed local model that supports structured output and
`think:false`, initialize with `--init ollama --model YOUR_LOCAL_MODEL` instead.
Only loopback HTTP is accepted, redirects/proxies are not followed, and model
metadata identifying cloud forwarding is rejected. No downloads, credentials or
remote Ollama endpoints are configured by this runner. Disable cloud features in
the Ollama service for a wholly local deployment. This option is supplementary;
Codex is the requested path for the first on-device model match.

## What is and is not validated

Automated checks cover bounded context, token exclusion, action shape, duplicate
requests, timeouts, fixed error codes, request budgets and child cleanup. The
Codex contract workflow runs the actual pinned CLI against a fake Responses API;
that is CLI/protocol evidence, **not real inference or a model-backed match**.
The existing deterministic real-client workflow remains the game regression gate.

Still required on the Omarchy XPS: run setup with the chosen Codex model, complete
a match, inspect the summary/replay, exercise Pause/Resume/Stop and tune latency
and context from measured behaviour. No claim of a full model match, a win,
provider competitiveness, or release readiness is made here.

Sources checked 24 September 2026:

- https://learn.chatgpt.com/docs/non-interactive-mode
- https://learn.chatgpt.com/docs/config-file/config-reference
- https://github.com/openai/codex/tree/rust-v0.156.1
- https://docs.ollama.com/api/chat
- https://docs.ollama.com/faq
