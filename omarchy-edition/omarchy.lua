--[[
   Red Alert: Omarchy Edition -- mission script.
   The Omarchians (Allied tech, bottom-left) versus the Commies (Soviet, top-right).
   Every API call below is listed in the release-20250330 Lua docs
   (utility --lua-docs) or copied from the shipped allies-01/allies-02 scripts.
   campaign.lua provides InitObjectives; utils.lua provides IdleHunt,
   AddPrimaryObjective and AddSecondaryObjective.
]]

HoundTypes = { "dog", "dog", "dog", "dog" }
Wave1Types = { "e1.cadre", "e1.cadre", "e1.cadre", "e1.cadre", "e1.cadre", "e1.cadre", "3tnk", "3tnk" }
Wave2ChokeTypes = { "3tnk", "3tnk", "3tnk", "e1.cadre", "e1.cadre", "e1.cadre", "e1.cadre", "e1.cadre", "e1.cadre", "v2rl" }
Wave2BridgeTypes = { "3tnk", "3tnk", "e1.cadre", "e1.cadre", "e1.cadre", "e1.cadre" }
GnomeEscortTypes = { "3tnk", "3tnk", "e1.cadre", "e1.cadre" }
AlacrittyTypes = { "1tnk", "1tnk", "1tnk" }

ChokePath = { SovietSpawn.Location, ChokePoint.Location }
BridgePath = { SovietSpawn.Location, BridgeNorth.Location, BridgeSouth.Location }
WestPath = { WestEntry.Location, WestRally.Location }

-- Reinforce a Soviet group along `path`; once each unit reaches the end of the
-- path it attack-moves on the ISO and then hunts whatever is left.
SendSovietWave = function(types, path, interval)
	if Compositor.IsDead then
		return
	end

	Reinforcements.Reinforce(USSR, types, path, interval, function(unit)
		if not ISO.IsDead then
			unit.AttackMove(ISO.Location)
		end
		IdleHunt(unit)
	end)
end

-- t = 2:00. Four Systemd Hounds go for the pacman -Syu truck.
-- Stock dogs cannot bite vehicles (DogJaw only targets infantry), so they
-- sprint to the truck's position and maul whoever is guarding it.
SendHounds = function()
	if Compositor.IsDead then
		return
	end

	Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-hounds"), UserInterface.GetFluentMessage("omarchy-prefix-cpc"))
	Media.PlaySpeechNotification(Omarchy, "EnemyUnitsApproaching")

	local trucks = Omarchy.GetActorsByType("harv")
	Reinforcements.Reinforce(USSR, HoundTypes, ChokePath, 10, function(hound)
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

	Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-wave1"), UserInterface.GetFluentMessage("omarchy-prefix-omarchy"))
	Media.PlaySpeechNotification(Omarchy, "SovietForcesApproaching")
	SendSovietWave(Wave1Types, ChokePath, DateTime.Seconds(1))
end

-- t = 8:00. Three Alacrittys roll in from the western map edge.
SendAlacrittys = function()
	Media.PlaySpeechNotification(Omarchy, "ReinforcementsArrived")
	Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-reinforce"), UserInterface.GetFluentMessage("omarchy-prefix-omarchy"))
	Reinforcements.Reinforce(Omarchy, AlacrittyTypes, WestPath, DateTime.Seconds(1))
end

-- t = 12:00. Progress report, reveal the Compositor, and a two-pronged wave
-- (ford and pontoon bridge).
FiveYearPlanUpdate = function()
	if Compositor.IsDead then
		return
	end

	Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-plan60"), UserInterface.GetFluentMessage("omarchy-prefix-cpc"))
	Actor.Create("camera", true, { Owner = Omarchy, Location = Compositor.Location })
	SendSovietWave(Wave2ChokeTypes, ChokePath, DateTime.Seconds(1))
	SendSovietWave(Wave2BridgeTypes, BridgePath, DateTime.Seconds(1))
end

-- t = 18:00. The Five-Year Plan makes a GNOME Shell (Mammoth) invulnerable and
-- sends it at the ISO. If the Iron Curtain was already destroyed it arrives
-- without the shield.
ReleaseGnomeShell = function()
	if Compositor.IsDead then
		return
	end

	local gnome = Actor.Create("4tnk", true, { Owner = USSR, Location = SovietSpawn.Location })
	if not FiveYearPlan.IsDead then
		gnome.GrantCondition("invulnerability", DateTime.Seconds(45))
		Media.PlaySound("ironcur9.aud")
		Media.PlaySpeechNotification(Omarchy, "IronCurtainReady")
		Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-gnome"), UserInterface.GetFluentMessage("omarchy-prefix-cpc"))
	else
		Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-gnome-cancelled"), UserInterface.GetFluentMessage("omarchy-prefix-omarchy"))
	end

	gnome.AttackMove(ChokePoint.Location)
	if not ISO.IsDead then
		gnome.AttackMove(ISO.Location)
	end
	IdleHunt(gnome)

	SendSovietWave(GnomeEscortTypes, ChokePath, DateTime.Seconds(1))
end

-- The pontoon bridge is spawned by the engine from the tile templates, so its
-- pieces are only discoverable once the world is loaded.
WatchBridge = function()
	local pieces = Utils.Where(Map.ActorsInWorld, function(a)
		return a.Type == "br1" or a.Type == "br2" or a.Type == "br3"
	end)

	if #pieces > 0 then
		Trigger.OnAnyKilled(pieces, function()
			Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-bridge"), UserInterface.GetFluentMessage("omarchy-prefix-omarchy"))
		end)
	end
end

Tick = function()
	if Omarchy.HasNoRequiredUnits() then
		USSR.MarkCompletedObjective(USSRObjective)
	end
end

WorldLoaded = function()
	Omarchy = Player.GetPlayer("Omarchy")
	USSR = Player.GetPlayer("USSR")

	InitObjectives(Omarchy)

	USSRObjective = AddPrimaryObjective(USSR, "")
	DestroyCompositorObjective = AddPrimaryObjective(Omarchy, "omarchy-objective-compositor")
	KeepISOObjective = AddSecondaryObjective(Omarchy, "omarchy-objective-iso")
	CancelPlanObjective = AddSecondaryObjective(Omarchy, "omarchy-objective-plan")

	Trigger.OnKilledOrCaptured(Compositor, function()
		Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-win"), UserInterface.GetFluentMessage("omarchy-prefix-omarchy"))
		if not ISO.IsDead then
			Omarchy.MarkCompletedObjective(KeepISOObjective)
		end
		Omarchy.MarkCompletedObjective(DestroyCompositorObjective)
	end)

	Trigger.OnKilledOrCaptured(FiveYearPlan, function()
		Omarchy.MarkCompletedObjective(CancelPlanObjective)
	end)

	Trigger.OnKilled(ISO, function()
		Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-lose"), UserInterface.GetFluentMessage("omarchy-prefix-omarchy"))
		Omarchy.MarkFailedObjective(KeepISOObjective)
		Omarchy.MarkFailedObjective(DestroyCompositorObjective)
	end)

	Trigger.AfterDelay(DateTime.Seconds(1), WatchBridge)
	Trigger.AfterDelay(DateTime.Seconds(3), function()
		Media.DisplayMessage(UserInterface.GetFluentMessage("omarchy-msg-decree"), UserInterface.GetFluentMessage("omarchy-prefix-cpc"))
	end)

	Trigger.AfterDelay(DateTime.Minutes(2), SendHounds)
	Trigger.AfterDelay(DateTime.Minutes(5), SendFirstWave)
	Trigger.AfterDelay(DateTime.Minutes(8), SendAlacrittys)
	Trigger.AfterDelay(DateTime.Minutes(12), FiveYearPlanUpdate)
	Trigger.AfterDelay(DateTime.Minutes(18), ReleaseGnomeShell)

	Camera.Position = ISO.CenterPosition
end
