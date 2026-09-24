// SPDX-License-Identifier: GPL-3.0-or-later
// Explicit opt-in CI instrumentation. Hidden IDs stay inside the game-side test harness.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using OpenRA.Mods.Common.Traits;
using OpenRA.Traits;

namespace OpenRA.Mods.Omarchy
{
    public sealed partial class AgentPlayer
    {
        readonly HashSet<string> checks = new();
        void CheckRejected(string name, AgentAction action)
        {
            if (checks.Contains(name)) return;
            try { Translate(action); }
            catch (InvalidDataException)
            {
                checks.Add(name);
                Audit(new { type = "check", name, passed = true });
                return;
            }
            throw new InvalidOperationException("Agent safety check failed: " + name);
        }

        void RunChecks()
        {
            if (world.WorldTick % 100 != 0 && !Queues().Any(q => q.AllQueued().Any(i => i.Done))) return;
            var owned = Owned();
            var unit = owned.FirstOrDefault(a => a.TraitOrDefault<Mobile>() != null);
            if (unit != null)
            {
                CheckRejected("stale-id", new AgentAction { kind = "stop", group = new[] { uint.MaxValue } });
                CheckRejected("invalid-target", new AgentAction { kind = "attack", group = new[] { unit.ActorID }, target = uint.MaxValue });
                var hidden = world.Actors.FirstOrDefault(a => a.IsInWorld && !a.IsDead &&
                    player.RelationshipWith(a.Owner) == PlayerRelationship.Enemy && !a.CanBeViewedByPlayer(player));
                if (hidden != null)
                {
                    CheckRejected("hidden-target", new AgentAction { kind = "attack", group = new[] { unit.ActorID }, target = hidden.ActorID });
                    CheckRejected("foreign-unit", new AgentAction { kind = "stop", group = new[] { hidden.ActorID } });
                    using var observation = JsonDocument.Parse(JsonSerializer.Serialize(Observe()));
                    if (observation.RootElement.GetProperty("enemies").EnumerateArray().Any(e => e.GetProperty("id").GetUInt32() == hidden.ActorID))
                        throw new InvalidOperationException("Hidden actor leaked into observation");
                    if (checks.Add("fog-observation")) Audit(new { type = "check", name = "fog-observation", passed = true });
                }
            }
            var fact = owned.FirstOrDefault(a => a.Info.Name == "fact");
            if (fact != null)
                foreach (var q in Queues())
                {
                    var ready = q.AllQueued().FirstOrDefault(i => i.Done && world.Map.Rules.Actors[i.Item].HasTraitInfo<BuildingInfo>());
                    if (ready != null)
                        CheckRejected("blocked-placement", new AgentAction { kind = "place", actor = ready.Item, cell = Cell(fact.Location) });
                    if (!q.AllQueued().Any())
                    {
                        var costly = q.BuildableItems().FirstOrDefault(ai => q.GetProductionCost(ai) > player.PlayerActor.Trait<PlayerResources>().GetCashAndResources());
                        if (costly != null) CheckRejected("unaffordable", new AgentAction { kind = "produce", actor = costly.Name });
                    }
                }
            Audit(new { type = "state", tick = world.WorldTick,
                own = owned.GroupBy(a => a.Info.Name).ToDictionary(g => g.Key, g => g.Count()),
                phase = Status, accepted, rejected, disconnects });
        }
    }
}
