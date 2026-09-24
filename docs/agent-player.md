# Agent Player: experimental deterministic slice

The initial slice adds a **deterministic test bot**. This branch now also has an
experimental [Codex model adapter](agent-model.md); its full on-device match is
still unverified. Normal manual skirmish
still uses the existing menu and needs no Python process or API key. There is no
new production menu option or release version.

Build with the existing pinned OpenRA workflow, then run:

```sh
tools/run_agent_test.sh /absolute/path/to/build/bundle
```

Python 3 is required for this developer mode. The one local spectator watches
Omarchy (green, spawn 1) controlled through the bridge; both rivals use Normal AI.
The panel reports the test controller and last accepted action. Pause kills the
runner and stops new decisions; Resume starts a new private session. Already
accepted unit activities and production continue, as they do when a human stops
issuing orders. Orders already submitted to the engine can resolve before the
synchronized pause epoch. Stop and quit records an unfinished summary and exits.
Live manual takeover and automatic fallback are not implemented.

The baseline v0.1.0 release is unchanged. Do not use this experimental mode for
network play or saves. Model-provider setup and its additional limitations are
documented separately in [agent-model.md](agent-model.md).

## Protocol version 1

The game starts the fixed `agent-player/test_adapter.py` using `python3 -u`, with
anonymous stdin/stdout pipes and a random session token passed in the child
environment. No listener or shell is opened. No model credentials are accepted.
One JSON observation line produces one JSON reply line. Only one request is in
flight, at most once per 25 game ticks. A decision expires after five wall-clock
seconds or 150 ticks. Reply length is bounded to 8192 characters, nesting to eight
levels, groups to 32 unique IDs. Errors pause the controller without automatic
retries. Stderr is drained and discarded, never used as narration.

Replies echo `version`, `token`, `request`, plus an `action` object. Observations
contain tick, cash, power, owned actors, available production with costs, owned
queue contents, explored cells, currently visible enemies, legal visible building
placement candidates, recent damage to owned actors, and the previous action result. An ID is the engine's
match-local ActorID, not a permanent identifier. Hidden target errors use the same
`target unavailable` result as invalid IDs. No rival resources/queues are sent.
The initial contract does not yet include a full static prerequisite graph;
that remains work before a model adapter.

| kind | Fields | Meaning |
| --- | --- | --- |
| `wait` | none | Observe again at the next cadence. |
| `deploy` | `group: [owned MCV id]` | Deploy the starting MCV through Transforms. |
| `produce` | `actor`, `count: 1` | Queue one available item if queue empty and fully affordable. |
| `place` | `actor`, `cell: [x,y]` | Place a completed building on a currently visible legal footprint adjacent to the base. |
| `move` | `group`, `cell` | Move owned mobile units to explored, traversable terrain. |
| `attack` | `group`, `target` | Attack a currently visible enemy accepted by each unit's engine targeter. |
| `defend` | `group`, `cell` | Attack-move combat units to explored terrain. Not a persistent patrol manager. |
| `stop` | `group` | Stop the selected owned mobile units. |
| `set_rally` | `group`, `cell` | Set rally points on owned producers that support them. |

Accepted means **validated and dispatched**, not completed: combat, destruction,
and normal production delays still apply. The next observation reflects outcomes.
An action envelope records request, session epoch and tick deadline, but never the
pipe token. The resolver deduplicates request IDs and rejects expired/old epochs.
Never blindly retry production: reconnect, inspect the live owned queue, and make
a new decision. One item per empty queue makes retries conservative. There is no
arbitrary engine order name, engine method, shell command or state mutation API.

## Evidence and boundaries

Local summaries are `Engine.SupportDir/AgentPlayer/*.jsonl`: controller, slots,
accepted/rejected action types, lifecycle events and actual final/unfinished
result. They contain no observation dumps, credentials or model reasoning. Test
instrumentation (`OMARCHY_AGENT_SELFTEST=1`) additionally logs own roster counts
and pass/fail checks; hidden IDs remain inside the game-side test harness.

CI builds the pinned source, tests protocol boundaries, validates the mod, keeps
the manual client smoke test, and runs a visible deterministic match under Xvfb.
It retains a screenshot/video, replay, logs and summary in `agent-player-evidence`.
The test stalls the real child and uses the panel to resume and stop. Its game-side
checks cover hidden targets, foreign actors, stale IDs and blocked placement.
This does not establish a complete model match, human-quality tactics, live
Wayland behaviour, or target-XPS compatibility. Those are later acceptance gates.

## Validation status for this handoff

Verified on the pinned engine in [CI run 36048863039](https://github.com/tcballard/command-and-conquer-omarchy/actions/runs/36048863039),
implementation commit `ff48eb9c717d183bf14192e2ed469356a469c8b8`:

- The original manual-client smoke test passed.
- The deterministic real-client test reached tick 3006 (about two simulated minutes).
  Omarchy built two power plants, a refinery, barracks and war factory, and produced
  additional infantry and a light tank. Both rivals ran Normal AI in their locked slots.
- The bridge dispatched 40 accepted actions, including two attacks against visible
  enemies and a defensive order after actual damage to an owned unit. No live
  action was rejected. Six separate game-side safety checks passed: stale ID,
  invalid target, hidden target, foreign unit, fog-filtered observation and blocked placement.
- A forced runner stall caused one disconnect. The client remained usable, resumed
  with a fresh runner, and stopped through the panel. No fallback took over.
- The match was deliberately stopped, with result `Undefined` and no winners.
  This is first-slice integration evidence, not a completed match or a victory.

The `agent-player-evidence` artifact contains the actual video, screenshot, replay
and JSONL audit. Software rendering needed roughly 11 wall-clock minutes for the
run. Local builds and protocol tests also passed. The current CI does not force
an unaffordable game-side action or exercise every replay/epoch race; those remain
additional validation work before provider integration.

A full model-backed match and review on the target Omarchy XPS remain later gates.
An experimental Codex adapter is now implemented (see agent-model.md), but there
is no on-device model-match evidence, production menu option or new release yet.
