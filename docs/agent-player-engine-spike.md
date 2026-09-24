# Agent Player engine spike — 24 September 2026

Inspected Omarchy main `97bfe38bd09801cc618ebf4c29c0187dbd626bfd`
and OpenRA release-20250330 `b4f3d8ae02b6bd6f4a3a5441e6d0daf7c5073787`.
No engine downgrade or source patch is required for the test controller.

| Concern | Verified extension point | Consequence |
| --- | --- | --- |
| Local match | `OmarchyMenuLogic.StartSkirmish`, `Game.CreateLocalServer`, `ConnectionLogic.Connect`, `Game.LobbyInfoChanged` | Keep manual lobby flow. Developer test mode uses the same local server. |
| Locked slots | `LobbyCommands.SlotBot`, `Specate`, `SyncClientToPlayerReference`; `Session.Client.BotControllerClientIndex` | Issue `spectate`, then `slot_bot Multi0 <host index> omarchy-agent-test` and `normal` for Multi1/2; await acknowledged lobby state before `startgame`. Faction/colour/spawn locks remain effective. |
| Controller | `IBotInfo`, `IBot.Activate`, `Player` constructor; reference `ModularBot` | Host activates custom IBot. Do not activate stock modules for Omarchy or invoke them as an alleged agent. Replays must not launch a runner. |
| Orders | `World.IssueOrder`, `IResolveOrder`, `ValidateOrder.OrderValidation` | Use a small replayable action envelope, validate at resolution, then dispatch only fixed ordinary engine orders. Stock ownership validation still guards the envelope. |
| Production | `ProductionQueue.BuildableItems`, `CanQueue`, `GetProductionCost`, `Order.StartProduction` | Check prerequisites, capacity, affordability and queue state inside game. Acceptance means a legal order dispatched, not a promise it completes. |
| Placement | `PlaceBuilding.ResolveOrder`; `BaseBuilderQueueManager.TickQueue`; `World.CanPlaceBuilding`, `BuildingInfo.IsCloseEnoughToBase` | **Resolver does not itself check cell legality.** Bridge must check visible footprint, terrain/occupancy and base adjacency at resolution, not trust runner coordinates. |
| Visibility | `Actor.CanBeViewedByPlayer`, `Player.Shroud.IsVisible/IsExplored` | Filter by explicit Omarchy player, never spectator `RenderPlayer`. Check visibility before testing or describing hidden targets/placement. |
| Targets | `IIssueOrder.Orders`, `IOrderTargeter.CanTarget`, `IIssueOrder.IssueOrder` | Reuse engine targeting for attacks; restrict group IDs to live owned mobile combat units. |
| Spectator view | `World.RenderPlayer`, `LoadWidgetAtGameStart`, `IPostWorldLoaded` | Observer host can render Omarchy fog. The bridge independently filters all observations. |
| Takeover | `World.SetLocalPlayer` is private; `Player.IsBot/BotType` readonly; controller selected in constructor | Do not expose a takeover button. Implement pause/resume/stop; genuine live takeover needs a separate verified design. |
| Lifecycle | `INotifyActorDisposing`, `IGameOver`, `Player.WinState`, `World.WorldTick` | Kill child on disposal and game end; record actual result, including unfinished/stopped. |

First slice is explicitly a **deterministic test bot**, selected by a developer
launcher, with private redirected process pipes. No network socket, model or key.
The process receives only bounded JSON observations. A per-process random token,
request sequence and tick deadline reject unsolicited/stale replies. Each request
has at most one action. Pausing terminates the child and invalidates in-flight
requests. Resuming starts a fresh session; no automatic fallback or retry loop.
Only the one local spectator plus three required bot slots is supported.

The initial extra `deploy` action is necessary to turn the starting MCV into a
construction yard. It is allowlisted to the owned MCV's `Transforms` trait.
`defend` means an attack-move to a cell, not a permanently managed defence zone.
No model adapter, provider compatibility, on-device result or release is claimed.
