// SPDX-License-Identifier: GPL-3.0-or-later
using OpenRA.Graphics;
using OpenRA.Mods.Common.LoadScreens;
using OpenRA.Primitives;

namespace OpenRA.Mods.Omarchy
{
    // Keep the complete poster visible at every window size, with black letterboxing.
    public sealed class OmarchyCoverLoadScreen : SheetLoadScreen
    {
        Sprite cover;
        Sheet previousSheet;

        public override void DisplayInner(Renderer renderer, Sheet sheet, int density)
        {
            if (sheet != previousSheet)
            {
                previousSheet = sheet;
                cover = sheet == null ? null : CreateSprite(sheet, density, new Rectangle(304, 107, 1440, 810));
            }

            if (cover == null)
                return;

            var resolution = renderer.Resolution;
            var scale = System.Math.Min(resolution.Width / 1440f, resolution.Height / 810f);
            var width = 1440f * scale;
            var height = 810f * scale;
            renderer.RgbaSpriteRenderer.DrawSprite(cover,
                new float3((resolution.Width - width) / 2, (resolution.Height - height) / 2, 0),
                new float3(scale, scale, 1));
        }
    }
}
