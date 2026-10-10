# Live army and fleet orders

Regional startup installs `MilitaryOrderEvents` after campaign activation. The
shared Warcraft compatibility boundary registers immediate, point and unit-target
orders. Current representation IDs resolve to stable force records. Only active
player-controlled armies and fleets on the loaded physical map can submit player
orders; local defenses, cores, garrisons, foreign owners and detached objects
cannot acquire command authority.

Supported commands are stop, hold position, move, patrol, attack-move and attack
on a represented military target. A point smart/right-click order becomes move;
a target smart order is supported only for an eligible hostile military target
and resumes as attack. Point destinations use the existing physical-map movement
rasters, connected components and native terrain pathing. Target eligibility uses
stable identities, current conflict membership and settlement capture protection.
Transport, abilities, item/destructible targets and queued order sequences are
outside this single-current-order contract. Their native IDs are never guessed
into saved army or fleet commands.

Safe saves, load checkpoints and retirement sample represented force coordinates
against the same navigation and location-number contracts used by recovery. A
blocked or unknown observation retains the previous safe coordinates. Recovery
continues to own validated last-safe hints. Sampling the current native order
detects completion or cancellation even when Warcraft emits no new issued-order
event. Orders whose target is missing, dead, nonlocal, no longer hostile or under
capture protection settle to stop. Ownership transfer cancels the old command.
Replaying an order never assigns a new physical map or invents a target.

Reconstruction creates all representations before replaying their orders. Nested
load suspension postpones replay until all domains and target bindings have been
restored. Commit restores the saved player allegiance before checking target
hostility during replay. Callback generations, current handles and an issuance guard reject
stale events and synchronous callbacks caused by native replay. Repeated
installation retains one listener owner. Rejected loads restore the retained
native representations and equivalent orders from the existing campaign
checkpoint; old order subscriptions cannot mutate the restored authority.

The independently versioned military payload advances from v5 to **v6**. Its force
record appends `orderTargetId` and `orderControllerId`; no native handle enters a
save. V1–v5 still load, including both historical v4 settlement layouts and their
recovery hints. Legacy `march` and `sail` destinations migrate to `move`. Old
arbitrary order strings or targetless attacks cancel, because those formats never
recorded a target identity. Malformed v6 argument records reject before authority
replacement. Campaign envelopes 1–8, RPG and party location schemas are unchanged.

`MilitaryOrderEventsTests.wurst` starts an initialized campaign with generated
navigation and ordinary military projections, then delivers installed production
callbacks through recording native ports. It covers moved land/naval saves,
point and target replay, immediate orders, completion, missing targets, ownership,
defenders, invalid arguments, stale and reentrant events, repeated reconstruction,
saved allegiance, legacy migration and late failed-load rollback. No incremental
player QA is needed.

Issue #443 receipts cover only the order-persistence portions of ROAD-0048.01,
REQ-0233.01 and REQ-0234.01. Their full obligations remain blocked in canonical
traceability. Physical remote-command transport (REQ-0300.01 / ROAD-0062.01) and
native-client launch remain separate release blockers. Interpreter execution and
diagnostic compiled registrations do not establish Warcraft client gameplay.
