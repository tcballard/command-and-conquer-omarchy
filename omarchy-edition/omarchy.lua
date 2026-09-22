--[[
   Red Alert: Omarchy Edition -- mission script.
   The Omarchians (Allied tech, bottom-left) versus the Commies (Soviet, top-right).
   Every API call below is listed in the release-20250330 Lua docs
   (utility --lua-docs) or copied from the shipped allies-01/allies-02 scripts.
   campaign.lua provides InitObjectives; utils.lua provides IdleHunt,
   AddPrimaryObjective and AddSecondaryObjective.
]]

PlanMinutes = 30

HoundTypes = { "dog", "dog", "dog", "dog" }
Wave1Types = { "e1.commie", "e1.commie", "e1.commie", "e1.commie", "e1.commie", "e1.commie", "3tnk", "3tnk" }
Wave2ChokeTypes = { "3tnk", "3tnk", "3tnk", "e1.commie", "e1.commie", "e1.commie", "e2", "e2", "e3.commie", "v2rl" }
Wave2BridgeTypes = { "3tnk", "3tnk", "e1.commie", "e1.commie", "e1.commie", "e1.commie" }
GnomeEscortTypes = { "3tnk", "3tnk", "shok", "shok" }
Wave3ChokeTypes = { "3tnk", "3tnk", "3tnk", "ttnk", "v2rl", "v2rl", "e1.commie", "e1.commie", "e2", "e2", "e4", "e4" }
Wave3BridgeTypes = { "3tnk", "3tnk", "ftrk", "e1.commie", "e1.commie", "e3.commie", "e3.commie" }
TankReinforcements = { "1tnk", "1tnk", "1tnk" }
HeroReinforcements = { "e7" }

ChokePath = { SovietSpawn.Location, ChokePoint.Location }
BridgePath = { SovietSpawn.Location, BridgeNorth.Location, BridgeSouth.Location }
WestPath = { WestEntry.Location, WestRally.Location }

InfantryLossLines = { "omarchy-msg-infantry-lost-1", "omarchy-msg-infantry-lost-2", "omarchy-msg-infantry-lost-3" }
VehicleLossLines = { "omarchy-msg-vehicle-lost-1", "omarchy-msg-vehicle-lost-2" }
InfantryLosses = 0
VehicleLosses = 0
AgentLaunched = false

Say = function(text, prefixKey)
	Media.DisplayMessage(text, UserInterface.GetFluentMessage(prefixKey))
end

-- Reinforce a Commie group along `path`; once each unit reaches the end of the
-- path it attack-moves on the ISO and then hunts whatever is left.
SendCommieWave = function(types, path, interval)
	if Compositor.IsDead then
		return
	end

	Reinforcements.Reinforce(Commies, types, path, interval, function(unit)
		if not ISO.IsDead then
			unit.AttackMove(ISO.Location)
		end
		IdleHunt(unit)
	end)
end

-- t = 2:00. Four Systemd Hounds go for the truck.
-- Stock dogs cannot bite vehicles (DogJaw only targets infantry), so they
-- sprint to the truck's position and maul whoever is guarding it.
SendHounds = function()
	if Compositor.IsDead then
		return
	end

	Say(UserInterface.GetFluentMessage("omarchy-msg-hounds"), "omarchy-prefix-cpc")
	Media.PlaySpeechNotification(Omarchy, "EnemyUnitsApproaching")

	local trucks = Omarchy.GetActorsByType("harv")
	Reinforcements.Reinforce(Commies, HoundTypes, ChokePath, 10, function(hound)
		if #trucks > 0 and not trucks[1].IsDead then
			hound.AttackMove(trucks[1].Location)
		elseif not ISO.IsDead then
			hound.AttackMove(ISO.Location)
		end
		IdleHunt(hound)
	end)
end

-- t = 5:00. First wave through the ford.
SendFirstWave = function()
	if Compositor.IsDead then
		return
	end

	Say(UserInterface.GetFluentMessage("omarchy-msg-wave1"), "omarchy-prefix-omarchy")
	Media.PlaySpeechNotification(Omarchy, "SovietForcesApproaching")
	SendCommieWave(Wave1Types, ChokePath, DateTime.Seconds(1))
end

-- t = 8:00. Three light tanks roll in from the western map edge.
SendTanks = function()
	Media.PlaySpeechNotification(Omarchy, "ReinforcementsArrived")
	Say(UserInterface.GetFluentMessage("omarchy-msg-reinforce"), "omarchy-prefix-omarchy")
	local tanks = Reinforcements.Reinforce(Omarchy, TankReinforcements, WestPath, DateTime.Seconds(1))
	Utils.Do(tanks, WatchOmarchianUnit)
end

-- t = 10:00. DHH arrives. One per distribution.
SendHero = function()
	Say(UserInterface.GetFluentMessage("omarchy-msg-dhh"), "omarchy-prefix-omarchy")
	local heroes = Reinforcements.Reinforce(Omarchy, HeroReinforcements, WestPath, DateTime.Seconds(1))
	Utils.Do(heroes, function(hero)
		Trigger.OnKilled(hero, function()
			Say(UserInterface.GetFluentMessage("omarchy-msg-dhh-dead"), "omarchy-prefix-omarchy")
		end)
	end)
end

-- t = 12:00. Progress report, reveal the Compositor, and a two-pronged wave
-- (ford and pontoon bridge).
FiveYearPlanUpdate = function()
	if Compositor.IsDead then
		return
	end

	Say(UserInterface.GetFluentMessage("omarchy-msg-plan60"), "omarchy-prefix-cpc")
	Actor.Create("camera", true, { Owner = Omarchy, Location = Compositor.Location })
	SendCommieWave(Wave2ChokeTypes, ChokePath, DateTime.Seconds(1))
	SendCommieWave(Wave2BridgeTypes, BridgePath, DateTime.Seconds(1))
end

-- t = 18:00. The Five-Year Plan makes a GNOME Shell (Mammoth) invulnerable and
-- sends it at the ISO. If the Iron Curtain was already destroyed it arrives
-- without the shield.
ReleaseGnomeShell = function()
	if Compositor.IsDead then
		return
	end

	local gnome = Actor.Create("4tnk", true, { Owner = Commies, Location = SovietSpawn.Location })
	if not FiveYearPlan.IsDead then
		gnome.GrantCondition("invulnerability", DateTime.Seconds(45))
		Media.PlaySound("ironcur9.aud")
		Media.PlaySpeechNotification(Omarchy, "IronCurtainReady")
		Say(UserInterface.GetFluentMessage("omarchy-msg-gnome"), "omarchy-prefix-cpc")
	else
		Say(UserInterface.GetFluentMessage("omarchy-msg-gnome-cancelled"), "omarchy-prefix-omarchy")
	end

	gnome.AttackMove(ChokePoint.Location)
	if not ISO.IsDead then
		gnome.AttackMove(ISO.Location)
	end
	IdleHunt(gnome)

	SendCommieWave(GnomeEscortTypes, ChokePath, DateTime.Seconds(1))
end

-- t = 24:00. Everything the Committee has left.
SendFinalWave = function()
	if Compositor.IsDead then
		return
	end

	Say(UserInterface.GetFluentMessage("omarchy-msg-wave3"), "omarchy-prefix-cpc")
	Media.PlaySpeechNotification(Omarchy, "SovietForcesApproaching")
	SendCommieWave(Wave3ChokeTypes, ChokePath, DateTime.Seconds(1))
	SendCommieWave(Wave3BridgeTypes, BridgePath, DateTime.Seconds(1))
end

-- The Five-Year Plan clock. Destroying the Iron Curtain stops it.
PlanCompleted = function()
	if Compositor.IsDead or FiveYearPlan.IsDead then
		return
	end

	Say(UserInterface.GetFluentMessage("omarchy-msg-plan-done"), "omarchy-prefix-cpc")
	Omarchy.MarkFailedObjective(DestroyCompositorObjective)
end

PlanCancelled = function()
	DateTime.TimeLimit = 0
	UserInterface.SetMissionText("")
	Say(UserInterface.GetFluentMessage("omarchy-msg-plan-cancelled"), "omarchy-prefix-omarchy")
	Omarchy.MarkCompletedObjective(CancelPlanObjective)
end

-- Reactive lines for our own losses. Capped so the chat does not drown.
WatchOmarchianUnit = function(unit)
	if unit.Owner ~= Omarchy or not unit.HasProperty("Health") then
		return
	end

	Trigger.OnKilled(unit, function()
		if unit.Type == "harv" then
			Say(UserInterface.GetFluentMessage("omarchy-msg-truck-lost"), "omarchy-prefix-omarchy")
		elseif unit.Type == "heli" then
			Say(UserInterface.GetFluentMessage("omarchy-msg-agent-lost"), "omarchy-prefix-omarchy")
		elseif unit.Type == "e7" then
			return -- handled in SendHero
		elseif unit.HasProperty("Move") and (unit.Type == "e1" or unit.Type == "e3" or unit.Type == "e6" or unit.Type == "medi" or unit.Type == "mech" or unit.Type == "spy" or unit.Type == "thf") then
			InfantryLosses = InfantryLosses + 1
			if InfantryLosses <= #InfantryLossLines then
				Say(UserInterface.GetFluentMessage(InfantryLossLines[InfantryLosses]), "omarchy-prefix-omarchy")
			end
		elseif unit.HasProperty("Move") then
			VehicleLosses = VehicleLosses + 1
			if VehicleLosses <= #VehicleLossLines then
				Say(UserInterface.GetFluentMessage(VehicleLossLines[VehicleLosses]), "omarchy-prefix-omarchy")
			end
		end
	end)
end

-- Lines for named buildings on both sides.
WatchBuilding = function(building, key, prefixKey, extra)
	if not building or building.IsDead then
		return
	end

	Trigger.OnKilled(building, function()
		Say(UserInterface.GetFluentMessage(key), prefixKey)
		if extra then
			extra()
		end
	end)
end

-- The pontoon bridge is spawned by the engine from the tile templates, so its
-- pieces are only discoverable once the world is loaded.
WatchBridge = function()
	local pieces = Utils.Where(Map.ActorsInWorld, function(a)
		return a.Type == "br1" or a.Type == "br2" or a.Type == "br3"
	end)

	if #pieces > 0 then
		Trigger.OnAnyKilled(pieces, function()
			Say(UserInterface.GetFluentMessage("omarchy-msg-bridge"), "omarchy-prefix-omarchy")
		end)
	end
end

Tick = function()
	if Omarchy.HasNoRequiredUnits() then
		Commies.MarkCompletedObjective(CommiesObjective)
	end
end

WorldLoaded = function()
	Omarchy = Player.GetPlayer("Omarchy")
	Commies = Player.GetPlayer("Commies")

	InitObjectives(Omarchy)

	CommiesObjective = AddPrimaryObjective(Commies, "")
	DestroyCompositorObjective = AddPrimaryObjective(Omarchy, "omarchy-objective-compositor")
	KeepISOObjective = AddSecondaryObjective(Omarchy, "omarchy-objective-iso")
	CancelPlanObjective = AddSecondaryObjective(Omarchy, "omarchy-objective-plan")

	-- Win / lose
	Trigger.OnKilledOrCaptured(Compositor, function()
		Say(UserInterface.GetFluentMessage("omarchy-msg-win"), "omarchy-prefix-omarchy")
		DateTime.TimeLimit = 0
		UserInterface.SetMissionText("")
		if not ISO.IsDead then
			Omarchy.MarkCompletedObjective(KeepISOObjective)
		end
		Omarchy.MarkCompletedObjective(DestroyCompositorObjective)
	end)

	Trigger.OnKilled(ISO, function()
		Say(UserInterface.GetFluentMessage("omarchy-msg-lose"), "omarchy-prefix-omarchy")
		Omarchy.MarkFailedObjective(KeepISOObjective)
		Omarchy.MarkFailedObjective(DestroyCompositorObjective)
	end)

	-- The clock
	DateTime.TimeLimit = DateTime.Minutes(PlanMinutes)
	Trigger.OnTimerExpired(PlanCompleted)
	Trigger.OnKilledOrCaptured(FiveYearPlan, PlanCancelled)

	-- Reactive lines: our buildings
	WatchBuilding(Power1, "omarchy-msg-powr-lost", "omarchy-prefix-omarchy")
	WatchBuilding(Power2, "omarchy-msg-powr-lost", "omarchy-prefix-omarchy")
	WatchBuilding(Mirror, "omarchy-msg-proc-lost", "omarchy-prefix-omarchy")
	WatchBuilding(Menu, "omarchy-msg-tent-lost", "omarchy-prefix-omarchy")
	WatchBuilding(Factory, "omarchy-msg-weap-lost", "omarchy-prefix-omarchy")

	-- Reactive lines: their buildings
	WatchBuilding(Snapd1, "omarchy-msg-cpowr-lost", "omarchy-prefix-cpc")
	WatchBuilding(Snapd2, "omarchy-msg-cpowr-lost", "omarchy-prefix-cpc")
	WatchBuilding(Snapd3, "omarchy-msg-cpowr-lost", "omarchy-prefix-cpc")
	WatchBuilding(Flatpak1, "omarchy-msg-capwr-lost", "omarchy-prefix-cpc")
	WatchBuilding(Flatpak2, "omarchy-msg-capwr-lost", "omarchy-prefix-cpc")
	WatchBuilding(Forum, "omarchy-msg-barr-lost", "omarchy-prefix-cpc")
	WatchBuilding(ElectronFactory, "omarchy-msg-cweap-lost", "omarchy-prefix-cpc")
	WatchBuilding(TelemetryDome, "omarchy-msg-cdome-lost", "omarchy-prefix-cpc")
	WatchBuilding(Kennel, "omarchy-msg-kenn-lost", "omarchy-prefix-cpc")
	WatchBuilding(Committee, "omarchy-msg-stek-lost", "omarchy-prefix-cpc")
	WatchBuilding(Coil1, "omarchy-msg-tsla-lost", "omarchy-prefix-cpc")
	WatchBuilding(Coil2, "omarchy-msg-tsla-lost", "omarchy-prefix-cpc")
	WatchBuilding(Coil3, "omarchy-msg-tsla-lost", "omarchy-prefix-cpc")
	WatchBuilding(FlameWar1, "omarchy-msg-ftur-lost", "omarchy-prefix-cpc")
	WatchBuilding(FlameWar2, "omarchy-msg-ftur-lost", "omarchy-prefix-cpc")
	WatchBuilding(Captcha1, "omarchy-msg-sam-lost", "omarchy-prefix-cpc")
	WatchBuilding(Captcha2, "omarchy-msg-sam-lost", "omarchy-prefix-cpc")

	-- Reactive lines: units, both pre-placed and produced later
	Utils.Do(Omarchy.GetActors(), WatchOmarchianUnit)
	Trigger.OnAnyProduction(function(producer, produced, productionType)
		if produced.Owner ~= Omarchy then
			return
		end
		if produced.Type == "heli" and not AgentLaunched then
			AgentLaunched = true
			Say(UserInterface.GetFluentMessage("omarchy-msg-agent-first"), "omarchy-prefix-omarchy")
		end
		WatchOmarchianUnit(produced)
	end)

	Trigger.AfterDelay(DateTime.Seconds(1), function()
		WatchBridge()
		Utils.Do(Omarchy.GetActorsByType("harv"), WatchOmarchianUnit)
	end)
	Trigger.AfterDelay(DateTime.Seconds(3), function()
		Say(UserInterface.GetFluentMessage("omarchy-msg-decree"), "omarchy-prefix-cpc")
	end)

	Trigger.AfterDelay(DateTime.Minutes(2), SendHounds)
	Trigger.AfterDelay(DateTime.Minutes(5), SendFirstWave)
	Trigger.AfterDelay(DateTime.Minutes(8), SendTanks)
	Trigger.AfterDelay(DateTime.Minutes(10), SendHero)
	Trigger.AfterDelay(DateTime.Minutes(12), FiveYearPlanUpdate)
	Trigger.AfterDelay(DateTime.Minutes(18), ReleaseGnomeShell)
	Trigger.AfterDelay(DateTime.Minutes(24), SendFinalWave)

	Camera.Position = ISO.CenterPosition
end
