// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Linq;
using OpenRA;

namespace OpenRA.Mods.Omarchy
{
    public sealed class CheckOmarchy : IUtilityCommand
    {
        string IUtilityCommand.Name => "--check-omarchy";
        bool IUtilityCommand.ValidateArguments(string[] args) => args.Length == 1;

        [Desc("Validate the Omarchy-only map catalog and menu assembly.")]
        void IUtilityCommand.Run(Utility utility, string[] args)
        {
            var mod = Game.ModData = utility.ModData;
            mod.MapCache.LoadPreviewImages = false;
            mod.MapCache.LoadMaps();
            var available = mod.MapCache.Where(m => m.Status == MapStatus.Available).ToArray();
            if (available.Length != 2 || available.Count(m => m.Visibility.HasFlag(MapVisibility.Lobby)) != 1 ||
                available.Count(m => m.Visibility.HasFlag(MapVisibility.Shellmap)) != 1 ||
                mod.Manifest.Missions.Length != 0 || mod.Manifest.MapFolders.Count != 1 ||
                mod.ObjectCreator.FindType("OmarchyMenuLogic") != typeof(OmarchyMenuLogic))
                throw new InvalidOperationException("Omarchy must expose exactly one skirmish, one backdrop, and no missions.");
            Console.WriteLine("Omarchy catalog verified: one playable skirmish, one backdrop, no campaign; custom menu resolves.");
        }
    }
}
