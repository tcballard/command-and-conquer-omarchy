// SPDX-License-Identifier: GPL-3.0-or-later
// Skirmish connection flow adapted from OpenRA MainMenuLogic (release-20250330).
using System;
using System.Linq;
using OpenRA;
using OpenRA.Mods.Common.Widgets;
using OpenRA.Mods.Common.Widgets.Logic;
using OpenRA.Widgets;

namespace OpenRA.Mods.Omarchy
{
    public sealed class OmarchyMenuLogic : ChromeLogic
    {
        readonly Widget menu;
        readonly ModData modData;
        bool disposed;
        bool busy;

        [ObjectCreator.UseCtor]
        public OmarchyMenuLogic(Widget widget, ModData modData)
        {
            menu = widget;
            this.modData = modData;
            widget.Get<ButtonWidget>("SKIRMISH").OnClick = StartSkirmish;
            widget.Get<ButtonWidget>("QUIT").OnClick = Game.Exit;
            widget.Get<ButtonWidget>("SETTINGS").OnClick = () =>
            {
                menu.IsVisible = () => false;
                Game.OpenWindow("SETTINGS_PANEL", new WidgetArgs
                {
                    { "onExit", (Action)(() => menu.IsVisible = () => true) }
                });
            };
            Game.OnShellmapLoaded += StartSkirmish;
        }

        void ShowMenu()
        {
            busy = false;
            menu.IsVisible = () => true;
        }

        void StartSkirmish()
        {
            if (disposed || busy)
                return;
            busy = true;
            menu.IsVisible = () => false;
            // Fail clearly if packaging ever adds another playable map.
            var map = modData.MapCache.Single(m => m.Status == MapStatus.Available &&
                m.Visibility.HasFlag(MapVisibility.Lobby)).Uid;
            ConnectionLogic.Connect(Game.CreateLocalServer(map, isSkirmish: true), "", () =>
            {
                var lobby = Game.OpenWindow("SERVER_LOBBY", new WidgetArgs
                {
                    { "onExit", (Action)(() => { Game.Disconnect(); ShowMenu(); }) },
                    { "onStart", (Action)(() => menu.Parent?.RemoveChild(menu)) },
                    { "skirmishMode", true }
                });
                // LobbyLogic resets these delegates; override them after construction.
                var changeMap = lobby.GetOrNull<ButtonWidget>("CHANGEMAP_BUTTON");
                if (changeMap != null)
                {
                    changeMap.IsVisible = () => false;
                    changeMap.IsDisabled = () => true;
                    changeMap.OnClick = () => { };
                }
            }, () => { Game.CloseServer(); ShowMenu(); });
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                disposed = true;
                Game.OnShellmapLoaded -= StartSkirmish;
            }
            base.Dispose(disposing);
        }
    }
}
