// SPDX-License-Identifier: GPL-3.0-or-later
using System.Linq;
using OpenRA.Graphics;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Primitives;
using OpenRA.Traits;
using OpenRA.Widgets;

namespace OpenRA.Mods.Omarchy
{
    public sealed class AgentPlayerPanelInfo : TraitInfo<AgentPlayerPanel> { }

    public sealed class AgentPlayerPanel : IPostWorldLoaded, IGameOver
    {
        AgentPlayer controller;
        void IPostWorldLoaded.PostWorldLoaded(World world, WorldRenderer wr)
        {
            var player = world.Players.FirstOrDefault(p => p.BotType == "omarchy-agent-test");
            if (player == null || world.IsReplay || System.Environment.GetEnvironmentVariable("OMARCHY_AGENT_TEST") != "1") return;
            controller = player.PlayerActor.Trait<AgentPlayer>();
            world.RenderPlayer = player;
            var mcv = world.Actors.FirstOrDefault(a => a.Owner == player && a.IsInWorld && a.Info.Name == "mcv");
            if (mcv != null) wr.Viewport.Center(mcv.CenterPosition);
            var panel = new BackgroundWidget { Bounds = new WidgetBounds(12, 65, 510, 112), Background = "panel-bg" };
            panel.AddChild(new LabelWidget(Game.ModData) { Bounds = new WidgetBounds(12, 8, 486, 22), GetText = () => controller.Status });
            panel.AddChild(new LabelWidget(Game.ModData) { Bounds = new WidgetBounds(12, 31, 486, 22), GetText = () => controller.LastDecision });
            panel.AddChild(new ButtonWidget(Game.ModData) { Bounds = new WidgetBounds(12, 68, 140, 30),
                GetText = () => controller.Paused ? "Resume test bot" : "Pause orders", OnClick = controller.TogglePause });
            panel.AddChild(new ButtonWidget(Game.ModData) { Bounds = new WidgetBounds(165, 68, 140, 30),
                GetText = () => "Stop and quit", OnClick = () => { controller.End("user stopped"); Game.Exit(); } });
            Ui.Root.AddChild(panel);
        }
        void IGameOver.GameOver(World world) => controller?.End("game result");
    }
}
