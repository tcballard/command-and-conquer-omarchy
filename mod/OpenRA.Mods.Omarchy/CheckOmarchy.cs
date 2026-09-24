// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Linq;
using System.IO;
using OpenRA.Mods.Common.Traits.Render;
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
            using var reader = new StreamReader(mod.DefaultFileSystem.Open("omarchy|roster-check.tsv"));
            var expected = reader.ReadToEnd().Split('\n', StringSplitOptions.RemoveEmptyEntries);
            if (expected.Length != 136 || expected.Distinct().Count() != expected.Length ||
                expected.Count(row => row.Split('\t')[1] == "allies") != 46 ||
                expected.Count(row => row.Split('\t')[1] == "soviet") != 45 ||
                expected.Count(row => row.Split('\t')[1] == "russia") != 45)
                throw new InvalidOperationException("The complete three-faction roster is required.");
            foreach (var preview in available)
            {
                using var map = new Map(mod, preview.Package);
                if (map.InvalidCustomRules)
                    throw new InvalidOperationException("Custom rules failed to load.", map.InvalidCustomRulesException);
                foreach (var row in expected)
                {
                    var entry = row.Split('\t');
                    var actor = map.Rules.Actors[entry[0]];
                    var render = actor.TraitInfo<RenderSpritesInfo>();
                    if (render.GetImage(actor, entry[1]) != entry[2] || render.PlayerPalette != "omarchy-player" ||
                        !map.Sequences.Images.Contains(entry[2]) || !map.Exists(entry[2] + ".shp"))
                        throw new InvalidOperationException($"Custom roster missing: {row} on {map.Title}");
                }
            }
            Console.WriteLine("All 136 faction roster entries resolve to custom images in both maps.");
            Console.WriteLine("Omarchy catalog verified: one playable skirmish, one backdrop, no campaign; custom menu resolves.");
        }
    }
}
