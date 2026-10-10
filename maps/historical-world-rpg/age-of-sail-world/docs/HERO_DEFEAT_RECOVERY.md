# Recruited hero defeat and recovery

The installed combat death listener resolves a current recruited field-hero
representation to the existing `RpgHero` authority. A real native death wounds
that character once. Duplicate or obsolete handles, callbacks from earlier
listener generations, and callbacks during reconstruction cannot restart the
recovery period. Projection retirement detaches the handle before native removal;
load commit and rollback keep combat delivery suspended until authority and
representations agree.

`scenario/progression/hero-progression.json` owns `defeatRecovery.recoveryDays`.
The release scenario uses the existing progression contract's 30 campaign days.
The deadline is the authoritative campaign ordinal at defeat plus that duration.
The clock delivers deadline checks after each committed date advancement,
including jumps across days without scheduled events. Manual and management
pauses do not consume recovery time. Loading checks the saved deadline against
the restored clock inside the rollback transaction. Neither reconstruction nor
repeated registration starts another deadline.

Defeat retains identity, recruited ownership, earned progression, starting ranks,
equipment, loyalty, Oathbound and physical location. The character leaves the
field group, their `/unstuck` registration and derived Warcraft representation
are retired, and no rewards or starting grants are issued. At the deadline the
same character becomes ready in reserve and the deadline is cleared, as in
`hero_progression.py`; recovery does not deploy a replacement. `/roster` and
`/inventory HERO` show condition and remaining campaign days.

Party location v1 remains the sole physical-location authority. Its existing
records now retain wounded members and recovered reserves, including the main
character. The native corpse position is sampled before removal, with the last
committed location retained if sampling cannot be validated. Healthy field
members alone are projected and count against field capacity. An all-wounded
party remains saveable and restorable with zero native hero objects; its recovery
clock continues. Reconstructing a wounded or reserve location does not pathing-
nudge it. A later field deployment still requires the existing connected-pathing
validation. Map arrivals carry only explicitly recorded local travelers.

Defeat and recovery add no persisted fields. RPG v5 adds quest-stage history
while retaining the existing hero fields; party location v1 and campaign
envelopes 1–8 are unchanged. Existing RPG v2–v4 wounded flags and deadlines are
retained without starting grants. Coordinate-less legacy campaigns use their
existing origin/boundary migration once, including existing incapacitated heroes;
legacy v2 identity fallback can select an already recruited wounded character
when no field character exists. No character is recruited as a consequence of
defeat or recovery. Rejected restoration restores the previous clock, conditions,
deadlines, location records, objects and equipment bookkeeping atomically.

`HeroDefeatLifecycleTests.wurst` starts through generated production registration
and regional startup, installs the native event callback against recording
boundaries, and advances through the production clock timer. It covers duplicate
and stale deaths, retirement callbacks, repeated installation/reconstruction,
pauses, jumps, mixed and all-wounded parties, fresh-service save/resume,
rejected reconstruction, inspection and equipment replay. The Python progression
oracle and generator checks compare the configured timing and state contract.
These checks do not establish native-client launch or gameplay success.
