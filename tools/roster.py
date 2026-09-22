"""
The single source of truth for every name in Red Alert: Omarchy Edition.

tools/build_map.py turns this into omarchy.ftl (strings), rules.yaml
(Tooltip/Buildable overrides and side-specific variants), sequences.yaml and
the generated sidebar icons. Change a name here, rebuild, done.

Each entry: (actor id, display name, description or None, role label for the
icon or None). Descriptions quote real Omarchy hotkeys/commands from the
Omarchy manual (basecamp/omarchy, manual/*.md) -- nothing invented.

OPEN DECISIONS (marked below): light tank / ranger naming, ore truck naming.
"""

# --------------------------------------------------------------------------
# Omarchians (Allied tech tree). Every buildable here gets a generated icon.
# --------------------------------------------------------------------------
OMARCHY = [
    # structures
    ("mcv",  "Boot USB",            "Deploys into the ISO. Don't lose it.", "mcv"),
    ("fact", "The ISO",             "Everything is built from here. Do not rm -rf.", "conyard"),
    ("powr", "Hyprland",            "The compositor. Tiling only.", "power"),
    ("apwr", "Hyprland (NVIDIA)",   "Twice the power. Check the driver. Check it again.", "power"),
    ("proc", "Package Mirror",      "Refines packages into credits. Rolling release.", "refinery"),
    ("silo", "Package Cache",       "/var/cache/pacman/pkg. Never cleaned.", "silo"),
    ("tent", "Omarchy Menu",        "Super + Space. Everything comes out of here.", "barracks"),
    ("weap", "Docker",              "Ships armour in containers. Super + Shift + D for Lazydocker.", "factory"),
    ("dome", "Omarchy Bar",         "Always on screen. The right and middle buttons are where the good stuff hides.", "radar"),
    ("fix",  "omarchy reinstall",   "Reinstalls the defaults and downgrades whatever is too new.", "repair"),
    ("atek", "Neovim",              "(btw). Unlocks everything, once you learn the keys.", "tech"),
    ("pdox", "Edge Channel",        "Chronoshifts units to tomorrow's packages. They come back when the snapshot restores.", "chrono"),
    ("gap",  "Lock Screen",         "Super + Ctrl + L. Nobody sees what's behind it. Fingerprint optional.", "gap gen"),
    ("pbox", "ufw",                 "Default deny. Docker gets special treatment.", "pillbox"),
    ("hbox", "Fido2 Key",           "Small. Easy to miss. Denies sudo to strangers.", "camo pillbox"),
    ("gun",  "sudo",                "Asks for your password. Then shoots.", "turret"),
    ("agun", "Silence Notifications", "Super + Ctrl + , . Shoots down anything that pops up.", "AA gun"),
    ("sbag", "Pane Divider",        "Ctrl + Space, then split. Cheap. Infantry walk around it.", "wall"),
    ("fenc", "Window Gaps",         "Super + Shift + Backspace toggles them.", "wall"),
    ("brik", "Window Border",       "2 px. Theme-coloured. Impassable.", "wall"),
    ("hpad", "Agent Terminal",      "Super + Shift + Ctrl + A. Launches your default agent.", "helipad"),
    ("mslo", "rm -rf /",            "--no-preserve-root. You were warned.", "silo"),
    # infantry
    ("e1",   "Keybinder",           "Everything happens via the keyboard. EVERYTHING.", "infantry"),
    ("e3",   "ripgrep",             "rg. Finds anything at range and hits it.", "rocket"),
    ("e6",   "chown -R",            "Takes ownership of any building. Recursively.", "engineer"),
    ("medi", "Night Light",         "Super + Ctrl + N. Heals the eyes of nearby operatives.", "medic"),
    ("mech", "Lazydocker",          "Repairs containers. Press ? for help.", "mechanic"),
    ("spy",  "Private Window",      "Disguises as anything. Leaves no history.", "spy"),
    ("thf",  "yt-dlp",              "Steals the whole thing. Lands in ~/Videos.", "thief"),
    ("e7",   "DHH",                 "One per distribution. Do not let him near the config.", "hero"),
    # vehicles  -- OPEN DECISION 1: jeep/1tnk names. Proposal: jeep=Alacritty, 1tnk=Foot.
    ("jeep", "Alacritty",           "Fast. Minimal. GPU-accelerated.", "ranger"),
    ("1tnk", "Foot",                "The default. Fast, lightweight, runs on old hardware. No tabs.", "light tank"),
    ("2tnk", "Ghostty",             "Optional. Heavier. Has tabs.", "medium tank"),
    ("arty", "LocalSend",           "Lobs files across the network. Super + Ctrl + S.", "artillery"),
    ("apc",  "Workspace",           "Carries five windows. Super + Shift + 2 moves them.", "APC"),
    ("mnly", "Reminders",           "Lays timed messages. They go off later. Super + Ctrl + R.", "minelayer"),
    ("ctnk", "zoxide",              "Remembers everywhere it's been. Jumps there.", "chrono tank"),
    ("mgg",  "Screensaver",         "ASCII art on wheels. Hides everything behind it.", "mobile gap"),
    # OPEN DECISION 2: truck name. Proposal: omarchy update.
    ("harv", "omarchy update",      "Harvests packages the right way. Takes a snapshot first. Alias: mup.", "harvester"),
    # aircraft
    ("heli", "Coding Agent",        "Auto-approving mode. Rockets included. What could go wrong.", "helicopter"),
    ("tran", "Tmux",                "Carries five panes anywhere. Ctrl + Space is the prefix.", "transport"),
    ("mh60", "Herdr",               "Like Tmux, newer. Detach, come back later, it is still running.", "transport"),
    ("mrj",  "Hide Bar",            "Super + Shift + Space. Their radar goes blank.", "radar jammer"),
]

# Support powers on Omarchian buildings (trait field overrides, not actors).
OMARCHY_POWERS = {
    # actor: (trait key as in mods/ra/rules/structures.yaml, name, description)
    "pdox": ("ChronoshiftPower@chronoshift", "Edge Channel", "Sends units to the edge channel. The snapshot brings them back."),
    "mslo": ("NukePower", "rm -rf /", "--no-preserve-root. You were warned."),
}

# Omakase: things Omarchy does not have are removed from the build menu.
OMARCHY_REMOVED = ["syrd", "pt", "dd", "ca", "lst", "msub", "ss", "spen", "truk"]

# --------------------------------------------------------------------------
# The Commies (Soviet side). Types shared with the Omarchians get a
# `.commie` variant actor; Soviet-only types are renamed directly.
# --------------------------------------------------------------------------
SHARED_TYPES = {"fact", "powr", "apwr", "weap", "dome", "fix", "e1", "e3", "e6", "brik", "mslo", "mcv", "harv", "spy", "apc", "mnly"}

COMMIE = [
    ("fact", "Central Planning Compositor", "All windows shall float.", None),
    ("powr", "Snap Daemon",           "Provides power. Runs at boot whether you asked or not.", None),
    ("apwr", "Flatpak Runtime",       "Provides power. 3 GB of runtimes included.", None),
    ("barr", "The Forum",             "Trains cadres. Please search before posting.", None),
    ("weap", "Electron Factory",      "Every unit ships with its own browser.", None),
    ("dome", "Telemetry Dome",        "Sees everything you do. The opt-out is buried.", None),
    ("fix",  "Support Ticket",        "Repairs in 3 to 5 business days.", None),
    ("stek", "Design Committee",      "Unlocks features nobody asked for.", None),
    ("kenn", "systemd",               "Breeds Hounds. Also handles logging, networking, time and your init.", None),
    ("iron", "Five-Year Plan",        "All windows will float. It is only a matter of time.", None),
    ("ftur", "Flame War",             "Burns anyone who mentions systemd.", None),
    ("sam",  "CAPTCHA",               "Shoots down anything that looks automated.", None),
    ("afld", "App Store",             "Launches Windows Updates.", None),
    ("mslo", "Forced Reboot",         "Updates are ready. Restart now.", None),
    ("brik", "Paywall",               "Subscribe to pass.", None),
    ("e1",   "Party Cadre",           None, None),
    ("e2",   "Hot Take",              "Lobs opinions. Splash damage.", None),
    ("e3",   "Reply Guy",             "Well, actually. Long range.", None),
    ("e4",   "Flame Warrior",         None, None),
    ("shok", "Moderator",             "Shocks. Bans. Locks the thread.", None),
    ("e6",   "Consultant",            "Captures your buildings. Bills hourly.", None),
    ("dog",  "Systemd Hound",         None, None),
    ("spy",  "Tracking Pixel",        None, None),
    ("3tnk", "Floating Window",       "Slow. Overlaps everything.", None),
    ("4tnk", "GNOME Shell",           "Invulnerable, as usual.", None),
    ("v2rl", "Electron App",          "400 MB. Hits your RAM from across the map.", None),
    ("ftrk", "Cookie Banner",         "Pops up. Blocks everything until you click Accept.", None),
    ("ttnk", "KDE Plasma",            "Every widget. All of them. At once.", None),
    ("apc",  "Floating Dialog",       None, None),
    ("mnly", "Update Notifier",       "Lays reminders you didn't ask for.", None),
    ("mcv",  "Distro Hopper",         "Deploys a new base every weekend.", None),
    ("harv", "Data Harvester",        None, None),
    ("mig",  "Windows Update",        "Arrives uninvited. Reboots what it hits.", None),
    ("yak",  "Clippy",                "It looks like you're trying to defend a base.", None),
    ("hind", "Notification Spam",     None, None),
    ("badr", "Onboarding Wizard",     "Drops Next, Next, Next, Finish.", None),
]

# Kept as stock on purpose: tsla (Tesla Coil).

# --------------------------------------------------------------------------
# Stat tweaks (the only ones): 1tnk +15 % speed, 3tnk -10 % speed.
# --------------------------------------------------------------------------
SPEED_TWEAKS = {"1tnk": 130, "3tnk": 58}   # stock 113 and 64

FACTIONS = {"allies": "Omarchians", "soviet": "The Commies"}
BOT_NAME = "The Commies"


def key(side, actor):
    return f"{side}-{actor}"


def commie_type(actor):
    """Actor type used on the Soviet side for a given base type."""
    return f"{actor}.commie" if actor in SHARED_TYPES else actor
