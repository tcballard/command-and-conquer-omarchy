// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading.Tasks;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Omarchy
{
    [TraitLocation(SystemActors.Player)]
    public sealed class AgentPlayerInfo : TraitInfo, IBotInfo
    {
        public string Type => "omarchy-agent-test";
        [FluentReference]
        public readonly string Name = "omarchy-agent-test-name";
        string IBotInfo.Name => Name;
        public override object Create(ActorInitializer init) => new AgentPlayer(this, init.World);
    }

    public sealed partial class AgentPlayer : IBot, ITick, IResolveOrder, INotifyActorDisposing
    {
        readonly AgentPlayerInfo info;
        Player player;
        World world;
        Process runner;
        Task<string> pending;
        string token;
        int request, epoch, resolvedEpoch, lastResolved, nextTick, decisionTick;
        readonly Stopwatch decisionClock = new();
        readonly Stopwatch duration = new();
        bool enabled, paused, ended;
        int accepted, rejected, disconnects;
        string auditPath;
        object result = new { accepted = true, reason = "No action yet" };
        public string Status { get; private set; } = "Not connected";
        public string LastDecision { get; private set; } = "Deterministic test bot (no model)";
        public bool Paused => paused;
        IBotInfo IBot.Info => info;
        Player IBot.Player => player;
        public AgentPlayer(AgentPlayerInfo info, World world) { this.info = info; this.world = world; }
        void IBot.QueueOrder(Order order) { throw new InvalidOperationException("Use the validated action contract"); }

        void IBot.Activate(Player p)
        {
            if (p.World.IsReplay) return;
            player = p;
            world = p.World;
            // The experimental controller is not available to network matches.
            var clients = world.LobbyInfo.Clients.Where(c => c.Bot == null).ToArray();
            if (Environment.GetEnvironmentVariable("OMARCHY_AGENT_TEST") != "1" || p.InternalName != "Multi0" ||
                clients.Length != 1 || !clients[0].IsObserver || !Game.IsHost)
            {
                Status = "Unavailable: use the local test launcher";
                return;
            }
            enabled = true;
            duration.Start();
            var directory = Path.Combine(Platform.SupportDir, "AgentPlayer");
            try { Directory.CreateDirectory(directory); }
            catch (Exception e) when (e is IOException || e is UnauthorizedAccessException)
            { Status = "Paused: cannot create match evidence"; paused = true; return; }
            auditPath = Path.Combine(directory, DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N") + ".jsonl");
            Audit(new { type = "start", slots = world.LobbyInfo.Clients.Where(c => c.Bot != null).Select(c => new { slot = c.Slot, bot = c.Bot, spawn = c.SpawnPoint, faction = c.Faction }).ToArray(), controller = "deterministic-test", provider = "none", fallback = false });
            if (!paused) StartRunner();
        }

        void Audit(object entry)
        {
            if (auditPath == null) return;
            try { File.AppendAllText(auditPath, JsonSerializer.Serialize(entry) + "\n"); }
            catch (Exception e) when (e is IOException || e is UnauthorizedAccessException) { Status = "Paused: cannot write match evidence"; paused = true; KillRunner(); }
        }

        void StartRunner()
        {
            epoch++;
            world.IssueOrder(new Order("OmarchyAgentEpoch", player.PlayerActor, false) { ExtraData = (uint)epoch });
            token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
            var script = Path.Combine(Platform.EngineDir, "agent-player", "test_adapter.py");
            if (!File.Exists(script)) { Status = "Paused: test adapter missing"; paused = true; return; }
            try
            {
                var start = new ProcessStartInfo("python3")
                {
                    UseShellExecute = false, RedirectStandardInput = true,
                    RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true
                };
                start.ArgumentList.Add("-u");
                start.ArgumentList.Add(script);
                start.Environment["OMARCHY_AGENT_TOKEN"] = token;
                runner = Process.Start(start);
                // Never record untrusted runner stderr or secrets; drain to avoid pipe backpressure.
                _ = DrainErrors(runner.StandardError);
                Status = "Agent connected — TEST BOT";
                nextTick = world.WorldTick + 25;
            }
            catch (Exception e) when (e is IOException || e is System.ComponentModel.Win32Exception)
            { Disconnect(); }
        }

        static async Task DrainErrors(StreamReader r)
        {
            try { var buffer = new char[1024]; while (await r.ReadAsync(buffer, 0, buffer.Length) > 0) { } }
            catch (Exception e) when (e is IOException || e is ObjectDisposedException) { }
        }

        void KillRunner()
        {
            epoch++;
            if (pending != null)
                _ = pending.ContinueWith(t => { var ignored = t.Exception; }, TaskContinuationOptions.OnlyOnFaulted);
            pending = null;
            if (runner == null) return;
            try { if (!runner.HasExited) runner.Kill(true); }
            catch (InvalidOperationException) { }
            runner.Dispose(); runner = null;
        }

        void Disconnect()
        {
            disconnects++;
            paused = true;
            KillRunner();
            world.IssueOrder(new Order("OmarchyAgentEpoch", player.PlayerActor, false) { ExtraData = (uint)epoch });
            Status = "Reconnecting — paused; press Resume";
            Audit(new { type = "disconnect", tick = world.WorldTick });
        }

        public void TogglePause()
        {
            if (!enabled || ended) return;
            paused = !paused;
            if (paused) { KillRunner(); world.IssueOrder(new Order("OmarchyAgentEpoch", player.PlayerActor, false) { ExtraData = (uint)epoch }); Status = "Paused — orders stopped"; }
            else StartRunner();
            Audit(new { type = paused ? "pause" : "resume", tick = world.WorldTick });
        }

        public void End(string reason)
        {
            if (!enabled || ended) return;
            ended = true;
            KillRunner();
            Status = "Stopped — " + reason;
            Audit(new { type = "summary", reason, duration_seconds = duration.Elapsed.TotalSeconds,
                tick = world.WorldTick, result = player.WinState.ToString(),
                winners = world.Players.Where(p => p.WinState == WinState.Won).Select(p => p.InternalName).ToArray(),
                controller = "deterministic-test", provider = "none", accepted, rejected, disconnects, fallback = false });
        }

        void INotifyActorDisposing.Disposing(Actor self) => End("match closed");

        void ITick.Tick(Actor self)
        {
            if (!enabled || ended) return;
            if (world.IsGameOver || player.WinState != WinState.Undefined) { End("game result"); return; }
            if (Environment.GetEnvironmentVariable("OMARCHY_AGENT_SELFTEST") == "1") RunChecks();
            if (paused) return;
            if (pending != null)
            {
                if (decisionClock.Elapsed.TotalSeconds > 5 || world.WorldTick - decisionTick > 150) { Disconnect(); return; }
                if (!pending.IsCompleted) return;
                try
                {
                    var reply = AgentProtocol.Parse(pending.GetAwaiter().GetResult(), token, request);
                    pending = null;
                    var envelope = new AgentEnvelope { request = request, epoch = epoch,
                        deadline = world.WorldTick + 25, action = reply.action };
                    world.IssueOrder(new Order("OmarchyAgentAction", self, false) { TargetString = JsonSerializer.Serialize(envelope) });
                    Status = "Acting — TEST BOT";
                    nextTick = world.WorldTick + 25;
                }
                catch (Exception e) when (e is IOException || e is JsonException || e is InvalidOperationException || e is ObjectDisposedException)
                { Disconnect(); }
                return;
            }
            if (world.WorldTick < nextTick) return;
            request++;
            decisionTick = world.WorldTick;
            decisionClock.Restart();
            Status = "Deciding — TEST BOT";
            // Both pipe write and read run off the game thread. Only immutable JSON crosses threads.
            var json = JsonSerializer.Serialize(Observe());
            var process = runner;
            pending = Task.Run(async () =>
            {
                await process.StandardInput.WriteLineAsync(json);
                await process.StandardInput.FlushAsync();
                return await AgentProtocol.ReadLine(process.StandardOutput);
            });
        }

        Actor[] Owned() => world.Actors.Where(a => a.Owner == player && a.IsInWorld && !a.IsDead).OrderBy(a => a.ActorID).ToArray();
        ProductionQueue[] Queues() => Owned().SelectMany(a => a.TraitsImplementing<ProductionQueue>()).Where(q => q.Enabled && q.IsValidFaction).ToArray();
        static int[] Cell(CPos c) => new[] { c.X, c.Y };
        object Unit(Actor a) => new { id = a.ActorID, actor = a.Info.Name, cell = Cell(a.Location),
            mobile = a.TraitOrDefault<Mobile>() != null, combat = a.TraitsImplementing<AttackBase>().Any(),
            idle = a.IsIdle };

        bool Placement(ActorInfo ai, CPos cell)
        {
            var b = ai.TraitInfoOrDefault<BuildingInfo>();
            return b != null && b.Tiles(cell).All(c => world.Map.Contains(c) && player.Shroud.IsVisible(c)) &&
                b.IsCloseEnoughToBase(world, player, ai, cell) && world.CanPlaceBuilding(cell, ai, b, null);
        }

        object Observe()
        {
            var owned = Owned();
            var queues = Queues();
            var power = player.PlayerActor.Trait<PowerManager>();
            var origin = owned.FirstOrDefault(a => a.Info.Name == "fact")?.Location ?? owned.First().Location;
            var placements = new Dictionary<string, int[][]>();
            foreach (var item in queues.SelectMany(q => q.AllQueued()).Where(i => i.Done).Select(i => i.Item).Distinct())
            {
                var ai = world.Map.Rules.Actors[item];
                var cells = new List<CPos>();
                for (var y = -12; y <= 12; y++)
                    for (var x = -12; x <= 12; x++) cells.Add(origin + new CVec(x, y));
                placements[item] = cells.OrderBy(c => (c - origin).LengthSquared).Where(c => Placement(ai, c)).Take(12).Select(Cell).ToArray();
            }
            return new { version = 1, token, request, tick = world.WorldTick, cash = player.PlayerActor.Trait<PlayerResources>().GetCashAndResources(),
                power = new { provided = power.PowerProvided, used = power.PowerDrained },
                own = owned.Where(a => a.Info.HasTraitInfo<IOccupySpaceInfo>()).Select(Unit).ToArray(),
                enemies = world.Actors.Where(a => a.IsInWorld && !a.IsDead && a.Owner != player &&
                    player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && a.CanBeViewedByPlayer(player) &&
                    a.Info.HasTraitInfo<IOccupySpaceInfo>()).OrderBy(a => a.ActorID).Select(a => new { id = a.ActorID, actor = a.Info.Name, cell = Cell(a.Location) }).ToArray(),
                production = queues.Select(q => new { producer = q.Actor.ActorID, queue = q.Info.Type,
                    available = q.BuildableItems().Select(a => new { actor = a.Name, cost = q.GetProductionCost(a) }).ToArray(),
                    items = q.AllQueued().Select(i => new { actor = i.Item, done = i.Done }).ToArray() }).ToArray(),
                explored = world.Map.AllCells.Where(c => player.Shroud.IsExplored(c)).Select(Cell).ToArray(),
                placements, result };
        }

        void IResolveOrder.ResolveOrder(Actor self, Order order)
        {
            if (order.OrderString == "OmarchyAgentEpoch") { resolvedEpoch = (int)order.ExtraData; return; }
            if (order.OrderString != "OmarchyAgentAction") return;
            if (world.IsReplay) player = self.Owner;
            // Replays resolve recorded envelopes but never launch external code.
            try
            {
                if (order.TargetString == null || order.TargetString.Length > AgentProtocol.MaxReplyBytes) throw new InvalidDataException();
                var e = JsonSerializer.Deserialize<AgentEnvelope>(order.TargetString);
                if (e == null || e.request <= lastResolved || (e.epoch != resolvedEpoch) || world.WorldTick > e.deadline)
                    throw new InvalidDataException("stale action");
                lastResolved = e.request;
                AgentProtocol.Shape(e.action);
                var orders = Translate(e.action);
                foreach (var o in orders)
                    foreach (var resolver in o.Subject.TraitsImplementing<IResolveOrder>()) resolver.ResolveOrder(o.Subject, o);
                if (e.action.kind == "wait") return;
                accepted++;
                LastDecision = $"Accepted {e.action.kind}: {e.action.actor ?? (e.action.group.Length + " owned unit(s)")}";
                result = new { accepted = true, reason = "dispatched", request = e.request, kind = e.action.kind };
                Audit(new { type = "action", tick = world.WorldTick, request = e.request, accepted = true, kind = e.action.kind, actor = e.action.actor });
            }
            catch (Exception ex) when (ex is InvalidDataException || ex is JsonException)
            {
                rejected++;
                result = new { accepted = false, reason = ex is InvalidDataException ? ex.Message : "invalid action" };
                Audit(new { type = "rejected", tick = world.WorldTick, result });
            }
        }

        List<Order> Translate(AgentAction a)
        {
            var orders = new List<Order>();
            if (a.kind == "wait") return orders;
            if (a.kind == "produce" || a.kind == "place")
            {
                if (a.actor == null || !world.Map.Rules.Actors.TryGetValue(a.actor, out var ai)) throw new InvalidDataException("unavailable production");
                var q = Queues().FirstOrDefault(q => q.BuildableItems().Any(i => i.Name == a.actor) && q.CanQueue(ai, out _, out _));
                if (a.kind == "place") q = Queues().FirstOrDefault(q => q.CanBuild(ai) && q.AllQueued().Any(i => i.Item == a.actor && i.Done));
                if (q == null) throw new InvalidDataException("unavailable production");
                if (a.kind == "produce")
                {
                    if (a.count != 1 || q.AllQueued().Any() || (long)q.GetProductionCost(ai) * a.count > player.PlayerActor.Trait<PlayerResources>().GetCashAndResources())
                        throw new InvalidDataException("queue busy or unaffordable");
                    orders.Add(Order.StartProduction(q.Actor, a.actor, a.count));
                }
                else
                {
                    var c = new CPos(a.cell[0], a.cell[1]);
                    if (!q.AllQueued().Any(i => i.Item == a.actor && i.Done) || !Placement(ai, c)) throw new InvalidDataException("placement unavailable");
                    orders.Add(new Order("PlaceBuilding", player.PlayerActor, Target.FromCell(world, c), false)
                    { TargetString = a.actor, ExtraData = q.Actor.ActorID });
                }
                return orders;
            }
            if (a.group.Length == 0 || a.group.Distinct().Count() != a.group.Length) throw new InvalidDataException("invalid owned group");
            var units = a.group.Select(id => world.GetActorById(id)).ToArray();
            if (units.Any(u => u == null || u.IsDead || !u.IsInWorld || u.Owner != player)) throw new InvalidDataException("invalid owned group");
            if (a.kind == "deploy")
            {
                if (units.Length != 1 || units[0].Info.Name != "mcv" || units[0].TraitOrDefault<Transforms>()?.CanDeploy() != true)
                    throw new InvalidDataException("cannot deploy");
                orders.Add(new Order("DeployTransform", units[0], false));
                return orders;
            }
            if (a.kind == "attack")
            {
                var target = world.GetActorById(a.target);
                if (target == null || target.IsDead || !target.IsInWorld || !target.CanBeViewedByPlayer(player) ||
                    player.RelationshipWith(target.Owner) != PlayerRelationship.Enemy) throw new InvalidDataException("target unavailable");
                foreach (var unit in units)
                {
                    Order valid = null;
                    var t = Target.FromActor(target);
                    foreach (var issuer in unit.TraitsImplementing<IIssueOrder>())
                        foreach (var orderTarget in issuer.Orders.Where(o => o.OrderID == "Attack"))
                        {
                            var modifiers = TargetModifiers.None; string cursor = null;
                            if (orderTarget.CanTarget(unit, t, ref modifiers, ref cursor)) valid = issuer.IssueOrder(unit, orderTarget, t, false);
                        }
                    if (valid == null) throw new InvalidDataException("target unavailable");
                    orders.Add(valid);
                }
                return orders;
            }
            foreach (var unit in units)
            {
                if (a.kind == "stop")
                {
                    if (unit.TraitOrDefault<Mobile>() == null) throw new InvalidDataException("stop unsupported");
                    orders.Add(new Order("Stop", unit, false)); continue;
                }
                var c = new CPos(a.cell[0], a.cell[1]);
                if (!world.Map.Contains(c) || !player.Shroud.IsExplored(c)) throw new InvalidDataException("cell unavailable");
                if (a.kind == "set_rally")
                {
                    if (unit.TraitOrDefault<RallyPoint>() == null) throw new InvalidDataException("rally unsupported");
                    orders.Add(new Order("SetRallyPoint", unit, Target.FromCell(world, c), false));
                }
                else
                {
                    var mobile = unit.TraitOrDefault<Mobile>();
                    if (mobile == null || mobile.IsTraitDisabled || mobile.IsTraitPaused ||
                        !mobile.CanEnterCell(c, check: BlockedByActor.None)) throw new InvalidDataException("movement unavailable");
                    if (a.kind == "defend" && !unit.TraitsImplementing<AttackBase>().Any()) throw new InvalidDataException("defend unsupported");
                    orders.Add(new Order(a.kind == "defend" ? "AttackMove" : "Move", unit, Target.FromCell(world, c), false));
                }
            }
            return orders;
        }
    }
}
