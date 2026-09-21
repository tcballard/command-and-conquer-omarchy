# NOTES — Red Alert: Omarchy Edition

Everything below was checked against a fresh clone of
https://github.com/OpenRA/OpenRA at tag **release-20250330**
(commit tagged 2025-03-30; the tag list on the remote goes
`release-20250303`, `release-20250330` and nothing newer). Arch Linux ships
exactly that: `extra/openra 20250330-5`, built with
`make version VERSION=release-20250330`.

## Step 0 — what the shipped missions taught me

### Map package layout (`mods/ra/maps/allies-01`, `allies-02`, `agenda.oramap`)

* A map is a folder or a zip (`.oramap`) with the files at the archive root:
  `map.yaml`, `map.bin`, optional `rules.yaml`, `weapons.yaml`, `*.ftl`,
  `*.lua`, optional `map.png`. `unzip -l mods/ra/maps/agenda.oramap` shows
  `map.png map.yaml map.bin` at the root, no subfolder.
* `map.yaml` top-level keys accepted by `Map.cs` (release-20250330, line 162+):
  `MapFormat` (12 current, 11 minimum), `RequiresMod`, `Title`, `Author`,
  `Tileset`, `MapSize`, `Bounds`, `Visibility`, `Categories`, `LockPreview`,
  `Players`, `Actors`, `Rules`, `FluentMessages`, `Sequences`,
  `ModelSequences`, `Weapons`, `Voices`, `Music`, `Notifications`.
* Rules/scripts/strings are referenced from `map.yaml`:

  ```
  Rules: ra|rules/campaign-rules.yaml, ra|rules/campaign-tooltips.yaml, rules.yaml
  FluentMessages: ra|fluent/lua.ftl, ra|fluent/campaign.ftl, omarchy.ftl
  ```

  and the Lua files from `rules.yaml` under the world actor:

  ```
  World:
  	LuaScript:
  		Scripts: campaign.lua, utils.lua, omarchy.lua
  ```

  `campaign.lua` (mods/ra/scripts) gives `InitObjectives`; `utils.lua`
  (mods/common/scripts) gives `IdleHunt`, `AddPrimaryObjective`,
  `AddSecondaryObjective`. Both resolve from the mod file system.
* The mission briefing is `World: MissionData: Briefing:` (plain text with
  `\n`, not a Fluent key — `MissionDataInfo.Briefing` has no
  `[FluentReference]` attribute).
* Starting cash: `Player: PlayerResources: DefaultCash:` (allies-02 uses 5700;
  campaign-rules.yaml sets 0 and hides the dropdown).
* Player references (fields from `OpenRA.Game/Map/PlayerReference.cs`):
  `Name, Bot, AllowBots, Playable, Required, OwnsWorld, NonCombatant,
  LockFaction, Faction, LockColor, Color, LockSpawn, LockTeam, Allies,
  Enemies`. The enemy in every shipped mission is `Bot: campaign`, which is
  `ModularBot@CampaignAI: Type: campaign` from campaign-rules.yaml — a bot
  with no modules, i.e. an idle scripted player. That is what this map uses;
  no skirmish AI is involved, so the waves are exactly what the Lua sends.
* Actor names in `Actors:` become Lua globals (`Lab`, `OilPump`,
  `InsertionEntry` in allies-01). Waypoints are `waypoint` actors owned by
  Neutral.

### Renaming actors: the important engine fact

`OpenRA.Game/FluentProvider.cs` looks up the **mod** bundle first and the map
bundle second, explicitly so maps cannot redefine mod strings. So a map
`.ftl` cannot override `actor-e1.name`. Renames therefore go through
`rules.yaml`: `E1: Tooltip: Name: omarchy-e1.name` pointing at a *new* key
defined in `omarchy.ftl`. `Tooltip.Name`, `Buildable.Description`,
`Faction.Name` are all `[FluentReference]` fields, and the lint verifies the
keys exist.

Consequence: a name is per actor *type*, not per owner. `e1`, `fact`, `powr`,
`weap` exist on both sides, so the Soviet copies are inherited sub-actors
(`E1.CADRE`, `FACT.COMMIE`, `POWR.COMMIE`, `WEAP.COMMIE`) with their own
`Tooltip.Name`, `Buildable: Prerequisites: ~disabled`, and
`RenderSprites: Image: <base>` — the same idiom as `E7.noautotarget`
(`Image: E7`) in campaign-rules.yaml and `TRAN.Extraction` (`Image: tran`) in
allies-01. Everything else (`harv`, `mcv`, `1tnk`, `2tnk`, `e3`, `pdox`,
`tent`, `proc` on the Omarchian side; `3tnk`, `4tnk`, `dog`, `iron` on the
Soviet side) is single-owner in this mission and renamed directly.

Faction names: `Faction@allies` / `Faction@soviet` live on `^BaseWorld` in
`mods/ra/rules/world.yaml`; overriding `World: Faction@allies: Name:` merges
into the inherited trait.

`campaign-palettes.yaml` is deliberately **not** included: it swaps
`PlayerColorPalette` for `IndexedPlayerPalette` keyed by player name, which
would ignore `Color: 7AA2F7`. Without it the stock `PlayerColorPalette`
remaps units from the player colour, so the Omarchians really are Tokyo Night
blue.

### map.bin format (`Map.cs` `SaveBinaryData` / `LoadBinaryData`)

```
byte   TileFormat = 2
ushort width, ushort height
uint   tilesOffset = 17
uint   heightsOffset = 0        (RA MapGrid has no MaximumTerrainHeight)
uint   resourcesOffset = 17 + 3*W*H
tiles:     for x in 0..W-1: for y in 0..H-1: ushort templateId, byte index
resources: for x: for y: byte resourceType, byte density
```

Template ids/indices come from `mods/ra/tilesets/temperat.yaml`
(`Template@255` = clear1.tem 1x1 PickAny 16 variants, `Template@2` = w2.tem
2x2 water, 241/238/235/380/381 = pontoon bridge pieces, 17/25/26/46/55 shore
pieces). Ore is `ResourceIndex: 1`, `MaxDensity: 12` (`world.yaml`
`ResourceLayer`). The engine replaces index 255 on load with
`x%4 + (y%4)*4`; the generator writes those indices explicitly. The map UID
is a SHA1 over `*.yaml`, `*.bin`, `*.lua` (and `map.png` if present) in the
package.

### Bridges

No shipped map places a bridge actor in `map.yaml`. `LegacyBridgeLayer`
(`world.yaml`, `Bridges: bridge1, bridge2, ... br1, br2, br3, ...`) scans
the tiles for the bridge templates and spawns the destroyable actors itself.
The pontoon bridge here is a verbatim copy of the **tile ids** of a 20x16
rectangle from the shipped temperate mission `soviet-06a` (cells
x=70..89, y=18..33: shore tiles, a `br2`/`br2x` land end, a chain of six
`br3` segments running north-east, a `br1`/`br1x` end). Only numbers were
copied; the art stays in the engine's tileset. Each `br3` segment becomes its
own actor with 100000 HP and `RequiresForceFire`, so the player (or a stray
V2) can drop the crossing.

### Lua API

Generated from the pinned build with `./utility.sh ra --lua-docs` (identical
in content to https://docs.openra.net/en/release/lua/ for this release).
Every call in `omarchy.lua` is in that output:
`Trigger.AfterDelay/OnKilled/OnKilledOrCaptured/OnAnyKilled/OnIdle`,
`Reinforcements.Reinforce`, `Actor.Create`, `Media.DisplayMessage/
DisplayMessageToPlayer/PlaySpeechNotification/PlaySound`,
`UserInterface.GetFluentMessage`, `Player.GetPlayer`, `Map.ActorsInWorld`,
`Utils.Where`, `DateTime.Seconds/Minutes`, `Camera.Position`; actor
properties `IsDead, Type, Location, CenterPosition, AttackMove, Hunt,
GrantCondition`; player properties `AddObjective (via utils.lua),
MarkCompletedObjective, MarkFailedObjective, GetActorsByType,
HasNoRequiredUnits`. `GrantCondition("invulnerability", ticks)` works on
`4tnk` because `^Vehicle` carries `ExternalCondition@INVULNERABILITY`, which
is exactly what the Iron Curtain (`GrantExternalConditionPower`,
`Condition: invulnerability`) grants. Speech notification names
(`EnemyUnitsApproaching`, `SovietForcesApproaching`, `ReinforcementsArrived`,
`IronCurtainReady`) are keys in `mods/ra/audio/notifications.yaml`;
`ironcur9.aud` is the sound the Iron Curtain power itself plays
(`OnFireSound` in structures.yaml). These reference game assets by name; no
asset is bundled.

### Where the map must be installed

`mods/ra/mod.yaml`: `~^SupportDir|maps/ra/{DEV_VERSION}: User`. Linux
SupportDir is `$XDG_CONFIG_HOME/openra` (default `~/.config/openra`),
falling back to a legacy `~/.openra` if that directory exists
(`Platform.cs`). Arch's PKGBUILD runs `make version VERSION=release-20250330`,
so the path is `~/.config/openra/maps/ra/release-20250330/`. A map with
`Visibility: MissionSelector` shows under Singleplayer → Missions in a
generated group named "Missions" (`MissionBrowserLogic.cs`, "loose
missions").

## Step 1 — map layout (generated, not hand-edited)

`tools/build_map.py` writes `map.bin` and `map.yaml` deterministically
(fixed RNG seed for the trees) and asserts that no footprint overlaps and
that every building/unit/ore cell is on clear terrain. 64x64 cells,
`Bounds: 2,2,60,60` (the cordon lint requires bounds not to touch the edge),
TEMPERAT.

* A 7-cell-wide diagonal river along y = x separates the south-west
  (Omarchian) triangle from the north-east (Commie) triangle.
* One ford (the choke) at x+y ∈ [25,35] around cell (15,15); `ChokePoint`
  waypoint there.
* The pontoon bridge chunk at (36..55, 36..51) is the second route.
  Waypoints `BridgeNorth` (51,37) and `BridgeSouth` (37,50) sit on clear
  cells at either end.
* Omarchian base bottom-left: ISO (`fact`, named `ISO`), 2x `powr`, `proc`
  (its `FreeActor` spawns the pacman -Syu truck), `tent`, `weap`; 3x `e1`,
  2x `e3`, 2x `1tnk`; ore field (49 cells, density 12) east of the refinery;
  `WestEntry` (2,56) / `WestRally` (8,56) for reinforcements.
* Commie base top-right, brick-walled with a west gate and a south gate:
  `fact.commie` (named `Compositor`), `iron` (named `FiveYearPlan`),
  2x `apwr` + 3x `powr.commie` (700 power vs 540 drain, so the coils stay
  live), `barr`, `weap.commie`, `kenn`, 3x `tsla`, 2x `ftur`, six
  `e1.cadre`, two `3tnk`, two `dog`; `SovietSpawn` waypoint inside.
* No `map.png`: the engine renders the minimap from `map.bin` at runtime.
  No manual map-editor step was needed; nothing was done by hand.

Run `python3 tools/build_map.py` to regenerate and print an ASCII preview;
`tools/package.sh` regenerates and zips.

## Step 2 — theme

All names/tooltips from the brief are in `omarchy.ftl` and wired in
`rules.yaml`. Stat changes are exactly the two requested: `1tnk` speed 113 →
130 (+15 %), `3tnk` speed 64 → 58 (−10 %). Nothing else is touched.

## Step 3 — script beats (`omarchy.lua`)

| t | beat |
|---|---|
| 0 | primary "Destroy the Central Planning Compositor"; secondary "Keep the ISO alive"; bonus secondary "Cancel the Five-Year Plan" (Iron Curtain); 1500 credits |
| 0:03 | decree message |
| 2:00 | "Incoming: Systemd Hounds detected." — 4 dogs run at the truck (see deviations) |
| 5:00 | wave 1 via the ford: 6 cadres + 2 Floating Windows |
| 8:00 | 3 Alacrittys from the west edge, "Ghostty maintainers have sent tanks. Modal drivers included." |
| 12:00 | "The Five-Year Plan is 60% complete.", camera reveal of the Compositor, wave 2 split between ford (3 tanks, 6 cadres, 1 V2) and bridge (2 tanks, 4 cadres) |
| 18:00 | GNOME Shell (`4tnk`) created at the Soviet base, `invulnerability` for 45 s if the Iron Curtain still stands, Iron Curtain sound + speech, escorts follow |
| win | Compositor killed or captured → "Windows are tiled. Order is restored." |
| lose | ISO killed → "The ISO is gone. Reinstall from scratch." |

Waves stop once the Compositor is dead. Losing every unit and building also
loses (`HasNoRequiredUnits` → USSR's dummy objective completes, the
allies-02 idiom).

## Step 4 — what was verified (and how)

Engine built from the release-20250330 tag with .NET SDK 6.0.428
(`dotnet build -c Release -p:TargetPlatform=unix-generic`, 0 errors).

1. **YAML lint, warnings as errors** — both the source folder and the packed
   `.oramap`:

   ```
   $ TREAT_WARNINGS_AS_ERRORS=true ./utility.sh ra --check-yaml /path/omarchy-edition.oramap
   Testing map: Red Alert: Omarchy Edition
   $ echo $?
   0
   ```

   This runs the mod rule checks on the merged ruleset plus every
   `ILintMapPass` (actor references, owners, players, cordon, tiles, Fluent
   references in rules *and* Lua, Lua script existence, tooltips, ...).
2. **The lint bites.** A copy with a bogus trait, a bogus `Tooltip.Name` key
   and a bogus key in the Lua produced four errors and exit 1, so the clean
   run above is meaningful.
3. **Map hash** on the packed file: `89a85491be33cb53abdf7ed0b935daa97b660f1c`
   (`--map-hash`); the utility opened the zip as a map package.
4. **Lua syntax** under Lua 5.1 (the engine embeds Eluant/Lua 5.1):
   `omarchy.lua`, `campaign.lua`, `utils.lua` compile clean (lupa 2.8,
   lua51 runtime).
5. **Stubbed dry run** of the whole script under Lua 5.1: every OpenRA global
   replaced by recording stubs, `WorldLoaded` executed, every `AfterDelay`
   callback fired in order, the win/lose/bridge triggers fired. No runtime
   error, every Fluent key referenced by the script exists, every named actor
   the script uses exists in `map.yaml`. This checks control flow and
   argument shapes, not engine semantics.
6. **Headless dedicated server.** The stock `OpenRA.Server` cannot start in
   this sandbox: it hardcodes an `IPv6Any` listener and the sandbox has no
   IPv6 (`SocketException (97): Address family not supported`). A 40-line
   test harness that calls the engine's own unmodified `Server` class with an
   IPv4 endpoint (nothing in the engine was patched) was run with the map
   installed in a scratch support dir and selected via `Server.Map=<uid>`:

   ```
   [harness] server state: WaitingPlayers
   [harness] map uid: 89a85491be33cb53abdf7ed0b935daa97b660f1c
   [harness] map title: Red Alert: Omarchy Edition
   [harness] map status: Playable, UnsafeCustomRules
   dedicated-server.log:
   [2026-09-21T21:36:59] Failed to set socket option on 0.0.0.0:1234: Protocol not available
   [2026-09-21T21:36:59] Initial mod: ra
   [2026-09-21T21:36:59] Initial map: 89a85491be33cb53abdf7ed0b935daa97b660f1c
   ```

   `UnsafeCustomRules` is set for *any* map with custom rules
   (`MapPreview.DefinesUnsafeCustomRules`); the shipped `allies-02` run through
   the identical harness reports the same `Playable, UnsafeCustomRules`. The
   socket-option line is the IPv6-only option being refused on an IPv4
   socket, unrelated to the map. Note what this does and does not prove: the
   map loads in the server's map cache and its merged ruleset constructs
   without exceptions. The dedicated server never simulates the world, so
   **the Lua was not executed by the engine**.

### What was NOT verified

* No client run with the Red Alert assets and a display: I could not watch
  the mission play. Pathing through the ford/bridge, wave timing feel, the
  look of the raw water/grass shorelines (no beach transition tiles outside
  the copied bridge chunk), and balance are untested. Treat balance as
  "comedy first" as briefed.
* Engine-side semantics of the Lua calls (e.g. whether `Map.ActorsInWorld`
  already contains the bridge pieces one second in; it should, since
  `LegacyBridgeLayer` spawns them in `WorldLoaded`).

## Deviations from the brief, stated plainly

* **Dogs cannot attack the ore truck.** `DogJaw` has
  `ValidTargets: Infantry` (mods/ra/weapons/other.yaml), and the brief
  forbids stat/weapon changes beyond the two speed tweaks. The hounds
  attack-move to the truck's position and then hunt, so they maul the
  infantry around it. Ordering `dog.Attack(harv)` would be rejected by the
  engine.
* **"Keep the ISO alive" is secondary, as briefed, but losing the ISO must
  end the mission.** Secondary objectives never end the game, so the ISO's
  death also fails the primary objective. The message from the brief is
  shown either way.
* **Win also fires on capture** of the Compositor (`OnKilledOrCaptured`):
  an Allied engineer capture is a legitimate "tiling".
* `campaign-palettes.yaml` omitted (see above) so the player colour applies.
* No `map.png` in the package (engine generates the preview).
* Soviet `powr`/`weap` keep their stock names via `powr.commie`/`weap.commie`;
  the brief said Soviet names stay mostly stock.

## Confidence

| Deliverable | Confidence | Why |
|---|---|---|
| `omarchy-edition.oramap` loads and lints on release-20250330 | high | lint clean with warnings as errors; loads in server map cache; UID computed |
| Renames/tooltips/faction names appear as specified | high | every key is a linted `[FluentReference]`; mod-vs-map bundle precedence understood and respected |
| Player colour #7AA2F7 actually shows on units | medium-high | stock `PlayerColorPalette` path; campaign palette override deliberately excluded; not seen on screen |
| Mission script runs without Lua errors in-engine | medium-high | syntax + stubbed execution + lint of every key and named actor; not executed by the engine |
| Terrain is playable (ford + bridge are the only crossings, bases reachable) | medium | generated with asserts; the bridge tile arrangement is byte-identical to a shipped map; not path-tested in-engine |
| Looks good | low-medium | plain water next to plain grass except around the bridge; trees are random scatter |
| Balance | low | untested by design |
| INSTALL.md paths | high | derived from mod.yaml, Platform.cs and the Arch PKGBUILD |
