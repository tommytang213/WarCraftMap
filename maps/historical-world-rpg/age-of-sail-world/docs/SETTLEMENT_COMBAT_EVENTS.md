# Settlement combat events

After successful regional startup, `Bootstrap` installs `MilitaryCombatEvents`.
The compatibility boundary registers pre-damage and death listeners for every
Warcraft slot. Current representation IDs resolve to stable force records;
local-force records resolve to their settlement. Polities come from those
records. Forces owned by `player` and currently projected field heroes use the
player's current campaign allegiance. Warcraft ownership slots are presentation
only and do not establish political hostility.

Pre-damage events reject unauthorized harm to represented military units and
refresh legal settlement combat through `beginSettlementAttack`. Deaths pass the
same current-representation, active-region, conflict and capture-cooldown checks.
Core deaths invoke the existing capture authority; local garrison deaths record
the represented force's remaining strength as casualties; other military deaths
use `recordLoss`. Capture retains legal title, occupation attribution, office
reconciliation and authored defense reconstruction. Peace uses the existing
shared conflict authority. Scripted or illegal deaths reconstruct the projection
without changing authority. Detached objects and duplicate deaths have no effect.

A single one-shot timer wakes at the earliest deadline, with a one-second
housekeeping ceiling. It reads native elapsed gameplay time, including partial
ticks at combat, save and pause boundaries. It schedules capture expiry exactly
five unpaused seconds after capture. Modal and manual pause stop this timer;
unpausing resumes the remaining deadline. Strategic calendar speed has no effect
on military gameplay seconds. Each wake spends at most one finite reinforcement
wave per settlement. Further attacks refresh combat activity without resetting
the reinforcement deadline; quiet cleanup precedes reinforcement expenditure.

Registration is idempotent. Region reconstruction and campaign load transactions
suspend listeners and timers before native teardown and restart them after
commit or rollback. Listener generations, timer serials and current native
handles reject obsolete delivery. Representation removal detaches handles before
calling `RemoveUnit`, including capture cleanup. Reconstructed cores and defenses
receive whatever capture protection remains in authority.

## Save compatibility

The campaign envelope is schema 8. The independently versioned
`militarySettlements` payload advances to **v3**, adding one `k` record for elapsed
unpaused gameplay seconds. The current military v6 payload retains this clock
contract and adds [live order persistence](LIVE_MILITARY_ORDERS.md). Deadline and interval fields use the campaign clock's
exact binary-real encoding rather than rounded decimal formatting. Saves sample
the partial native tick, so loading on a fresh map neither restarts protection
nor compares saved deadlines to that map's uptime. Timer handles, registration
generations and UI pause ownership remain transient.

Military v1/v2 remain readable, including the v1 conflict migration. Those
formats had no production military clock or deadline callbacks. Migration uses
the latest recorded combat, wave or capture event as the legacy time anchor;
absent events start at zero. They cannot recover elapsed time that was never
recorded. Current saves preserve exact remaining deadlines across repeated loads,
map reconstruction and failed-load rollback. Missing, duplicate and malformed v3
clock records are rejected before replacing live authority.

`MilitaryCombatEventsTests.wurst` executes generated campaign registration and
regional startup, then delivers combat and timer callbacks through recording
native boundaries. It covers legal capture, shared-slot political identities,
peace and allied targets, duplicate deaths, obsolete callbacks, cleanup,
protection expiry, pauses, save/load, casualties and bounded waves. Native client
launch status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
