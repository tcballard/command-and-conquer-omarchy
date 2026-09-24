// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Linq;
using OpenRA.Network;
using OpenRA.Widgets;
namespace OpenRA.Mods.Omarchy
{
    public sealed class AgentLobbyLogic : ChromeLogic
    {
        readonly OrderManager orderManager;
        int agentSetupStep;
        [ObjectCreator.UseCtor]
        public AgentLobbyLogic(OrderManager orderManager)
        {
            this.orderManager = orderManager;
            if (Environment.GetEnvironmentVariable("OMARCHY_AGENT_TEST") == "1")
            {
                Game.LobbyInfoChanged += ConfigureAgentMatch;
                ConfigureAgentMatch();
            }
        }
        void ConfigureAgentMatch()
        {
            var om = orderManager;
            var local = om.LocalClient;
            if (local == null) return;
            if (agentSetupStep == 0)
            {
                agentSetupStep = 1;
                om.IssueOrder(Order.Command("spectate"));
                return;
            }
            if (!local.IsObserver) return;
            var slots = new[] { "Multi0", "Multi1", "Multi2" };
            var bots = new[] { "omarchy-agent-test", "normal", "normal" };
            if (agentSetupStep <= 3)
            {
                var i = agentSetupStep - 1;
                if (i > 0 && om.LobbyInfo.ClientInSlot(slots[i - 1])?.Bot != bots[i - 1]) return;
                agentSetupStep++;
                om.IssueOrder(Order.Command($"slot_bot {slots[i]} {local.Index} {bots[i]}"));
                return;
            }
            if (slots.Where((slot, i) => om.LobbyInfo.ClientInSlot(slot)?.Bot != bots[i]).Any()) return;
            Game.LobbyInfoChanged -= ConfigureAgentMatch;
            om.IssueOrder(Order.Command("startgame"));
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing) Game.LobbyInfoChanged -= ConfigureAgentMatch;
            base.Dispose(disposing);
        }
    }
}
