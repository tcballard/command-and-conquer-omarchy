"""Skirmish identity, independent of the archived mission's political parody."""
from roster import OMARCHY as ORIGINAL_OMARCHY, OMARCHY_POWERS, SPEED_TWEAKS

OMARCHY = list(ORIGINAL_OMARCHY) + [
    ('truk', 'Local Backup', 'Move credits between bases. Keep another copy.', 'supply truck'),
    ('stnk', 'Incognito', 'A quiet transport. Your passengers remain your business.', 'stealth APC'),
    ('u2', 'Package Index', 'Scans the map for available packages.', 'scout plane'),
]
GARDEN = [
    ('fact','The Walled Garden','Everything starts here. Everything stays here.','construction'),
    ('powr','Background Services','Always running. Nobody remembers installing them.','power'),
    ('apwr','System Requirements','More power. Your old hardware is no longer supported.','power'),
    ('proc','Data Centre','Turns your activity into shareholder value.','refinery'),
    ('silo','Cloud Storage','Your data. Our servers. Monthly payments.','storage'),
    ('barr','Onboarding','Accept the terms before joining the workforce.','barracks'),
    ('weap','Bloatware Factory','Every vehicle ships with a trial subscription.','factory'),
    ('dome','Telemetry','Help us improve your experience. Opt-out unavailable.','radar'),
    ('fix','Warranty Claim','Have you tried turning it off and on again?','repair'),
    ('stek','Product Roadmap','The feature you wanted is coming next quarter.','tech'),
    ('kenn','Endpoint Security','Identifies threats. Occasionally correctly.','kennel'),
    ('iron','Vendor Lock-in','Temporarily prevents all forms of migration.','forcefield'),
    ('ftur','Thermal Throttling','Runs hot. Very hot.','flame tower'),
    ('sam','Gatekeeper','This aircraft is from an unidentified developer.','AA missile'),
    ('tsla','DRM','Unauthorised access will be electrically discouraged.','coil'),
    ('afld','App Store','Every take-off requires platform approval.','airfield'),
    ('mslo','Forced Reboot','Your work was probably saved.','superweapon'),
    ('brik','Paywall','Subscribe to pass.','wall'),
    ('fenc','Terms of Service','By approaching this fence you agree to its terms.','fence'),
    ('e1','Default User','Standard issue. Administrator rights not included.','infantry'),
    ('e2','Popup','Arrives at the worst possible moment. Splash damage.','grenadier'),
    ('e3','Reply All','Reaches everyone, including people who never asked.','rocket'),
    ('e4','Fan Noise','The update is optimising your experience.','flamer'),
    ('shok','Admin Rights','Access denied. Emphatically.','shock trooper'),
    ('e6','Consultant','Takes ownership. Bills hourly.','engineer'),
    ('dog','Antivirus','Scans everything. Bites anything suspicious.','security dog'),
    ('spy','Tracking Pixel','Already knows where you have been.','spy'),
    ('thf','Dark Pattern','That was the subscribe button.','thief'),
    ('3tnk','Bloatware','Heavy. Persistent. Preinstalled.','heavy tank'),
    ('4tnk','System Upgrade','Needs more RAM, more storage and your entire afternoon.','superheavy'),
    ('v2rl','Push Notification','Long-range interruption delivery.','missile truck'),
    ('ftrk','Cookie Banner','Reject all is somewhere in the next menu.','flak truck'),
    ('ttnk','Kernel Panic','An unexpected problem has occurred. Nearby.','shock tank'),
    ('qtnk','Background Indexer','Shakes the ground while indexing your files.','shockwave'),
    ('dtrk','Factory Reset','Deletes everything in the surrounding area.','demolition'),
    ('apc','Walled Bus','All passengers must use the same ecosystem.','APC'),
    ('mnly','Restart Reminder','Remind me later. And later. And later.','minelayer'),
    ('mcv','Setup Wizard','Next. Next. Accept. Deploy.','MCV'),
    ('harv','Data Harvester','Harvests resources and probably your browsing history.','harvester'),
    ('truk','Cloud Sync','Moves credits. Requires an account.','supply truck'),
    ('mig','Forced Update','Arrives uninvited. Reboots what it hits.','strike jet'),
    ('yak','Clippy','It looks like you are trying to defend a base.','attack plane'),
    ('hind','Notification Spam','Turn them off. Another appears.','helicopter'),
    ('badr','Bundle Installer','Drops several things you did not ask for.','cargo plane'),
    ('u2','Diagnostics','Collecting information about this incident.','scout plane'),
]
SIDES = {'omarchy': OMARCHY, 'garden': GARDEN}
FACTIONS = {'allies':'Omarchians', 'soviet':'The Walled Garden'}
SUPPORT = {'badr','u2'}
# Keep country-special units usable with this map's two fixed factions.
PREREQUISITES = {
    'mgg':'atek, ~vehicles.allies, ~techlevel.high',
    'ctnk':'atek, ~vehicles.allies, ~techlevel.high',
    'stnk':'atek, ~vehicles.allies, ~techlevel.high',
    'ttnk':'tsla, stek, ~vehicles.soviet, ~techlevel.high',
    'dtrk':'stek, ~vehicles.soviet, ~techlevel.high',
    'shok':'~barr, stek, tsla, ~infantry.soviet, ~techlevel.high',
}
GARDEN_POWERS = {
    'iron': ('GrantExternalConditionPower@IRONCURTAIN','Vendor Lock-in','Makes units temporarily immune to attempts to leave the ecosystem.'),
}


def ftl():
    lines=['## Generated skirmish names; archived mission names are not loaded.']
    for key,value in FACTIONS.items():
        lines += [f'omarchy-skirmish-faction-{key} =\n    .name = {value}']
    for side,entries in SIDES.items():
        for actor,name,desc,role in entries:
            lines += [f'{side}-{actor} =\n    .name = {name}\n    .description = {desc or role or name}']
    for actor,(_,name,desc) in OMARCHY_POWERS.items():
        lines += [f'omarchy-power-{actor} =\n    .name = {name}\n    .description = {desc}']
    for actor,(_,name,desc) in GARDEN_POWERS.items():
        lines += [f'garden-power-{actor} =\n    .name = {name}\n    .description = {desc}']
    return '\n\n'.join(lines)+'\n'

# Stock weapon traits that render our custom muzzle sequences.
MUZZLE_TRAITS = {'yak': ['Armament'], 'hind': ['Armament'], 'mh60': ['Armament'], 'agun': ['Armament'], 'gun': ['Armament'], 'sam': ['Armament'], '1tnk': ['Armament'], '2tnk': ['Armament'], '3tnk': ['Armament'], '4tnk': ['Armament@PRIMARY', 'Armament@SECONDARY'], 'arty': ['Armament'], 'jeep': ['Armament'], 'apc': ['Armament'], 'ftrk': ['Armament@AA', 'Armament@AG'], 'e1': ['Armament@GARRISONED'], 'e7': ['Armament@GARRISONED']}
