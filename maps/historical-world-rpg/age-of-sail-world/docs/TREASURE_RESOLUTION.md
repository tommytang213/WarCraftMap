# Campaign treasure resolution

Issue #465 closes resolution and persistence under ROAD-0054, ROAD-0105 and
REQ-0251–REQ-0261. Clue acquisition adapters, authored reward delivery, guard,
hazard and encounter gameplay remain open. A stored variant ID is a selection,
not evidence that its gameplay executed. Existing native launch and downstream
integration blockers remain in force.

`configureGeneratedTreasures` registers every authored candidate, weight,
historical anchor, location family, placement restriction and reward/guard/
hazard/encounter choice. `scenario-runtime.json` contains the global `treasureResolutionCatalog`
and each candidate's materialized physical binding. No new campaign location is
selected by packaging. Physical targets retain #381's terrain/navigation and
reserved-settlement placement, and its observed actor, range, movement and loaded
map checks still authorize `/interact` at commit time.

A new campaign uses its positive, durable origin-request sequence as its decimal
seed. The selector writes this sequence transactionally before loading the first
regional map. Startup binds it before resolution; failed initial checkpoint
writes and fresh-service retries therefore use the same seed. Construction never
seeds or resolves a campaign. Saves and destination reconstruction restore the
seed and results rather than consulting a new origin request or random source.

`TreasureRandom` reproduces the headless SHA-256 contract: UTF-8/ASCII decimal
seed, a NUL byte, and `TREASURE_ID:location`, `:reward`, `:guard`, `:hazard` or
`:encounter`. Selection takes the first eight digest bytes as an unsigned big
endian integer modulo total weight, in authored order. Two unsigned 16-bit halves
avoid backend-dependent integer overflow. Runtime seeds are positive canonical
decimals of at most ten digits; authored namespaces are stable ASCII IDs.

The resolver stages all unresolved records before committing. Historical anchors,
materialized physical-map/navigation bindings, accessibility, clearance,
unavailable candidates and exclusive occupancy are checked before selection.
Only an authored fallback passing the same checks may be used. Previously resolved
records are immutable even when a candidate later becomes unavailable or its map
is inactive. No Warcraft object owns the result.

RPG domain **v7** adds one `s,SEED` record and extends each `t` record with mode,
candidate, reward, guard, hazard and encounter IDs. Registration-only defaults
may be pending, but campaign save validation rejects pending results. Validation
checks the whole snapshot, including duplicate/exclusive placements, before
changing any authority. Load rollback includes seed, resolutions, inventory,
knowledge and collected flags. Read-only decoding never modifies a source slot.

The explicit v1–v6 migration retains the legacy packager's effective candidate
from frozen `legacyCandidateLocationId` metadata for every treasure, including
hidden treasures, so anything previously exposed
cannot move. Migration uses deterministic seed `1` and marks each placement
`legacy`; absent variant history remains empty. Clue counts and collected flags
are copied, and no missing historical reward, encounter or collection is replayed.
An unavailable legacy definition or inconsistent placement rejects restoration.
Current version `seeded` records must contain authored variant identities;
`legacy` records must match the legacy candidate and contain no invented variants.

Knowledge projection reads committed authority. Hidden results reveal neither
region nor destination; partial clue stages reveal only the region in the
existing journal projection. Only an authored exact clue or an already collected
result reveals the committed candidate. Exhausting region-only clues cannot
reveal an exact destination. This change does not claim approximate
search-area rendering or production clue-source integration.

Automated coverage includes all 28 authored treasures at seeds 1, 4 and 42,
Tomar/Almourol physical commands, unavailable and exclusive placement failures,
malformed records, legacy knowledge/collection, failed startup writes, load
rollback and fresh services across outbound travel and return. See the scoped
report in `reports/issue-465/`; no incremental player QA is required.
