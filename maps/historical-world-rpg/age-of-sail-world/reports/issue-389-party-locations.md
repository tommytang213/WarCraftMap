# Issue 389: preserve current local party positions

Campaign schema 7 adds stable-ID `partyLocations` records with physical map,
coordinates, land component and last verified safe coordinates. Manual saves,
autosaves and recovery checkpoints sample the production party observation port.
Missing representations retain their last committed records; nonlocal roster
assignments stay abstract. Reconstruction validates the records and projects each
member at its own coordinates through the existing load transaction.

Transfer checkpoints explicitly identify the traveling party and pending arrival.
Each traveler must belong to the source map's field party before its assignment
can be rebound. Missing traveler IDs and records that enroll remote companions
reject transactionally; the latter regression reproduced an accepted malformed
transfer before the additional validation was applied.
The generated boundary correspondence is consumed once. Subsequent ordinary saves
restore current coordinates even if the old arrival corridor is unavailable.
Initial origin placement remains authored and independent of settlement objects.

The shared navigation generator and Wurst resolver use the packaged terrain's land
components and playable bounds. Native blocking permits a nearby connected recovery
within 512 world units, then a verified last-safe point. There is no implicit distant
settlement fallback for current records. Invalid maps, coordinates, identities,
components, empty parties and duplicate records reject without replacing prior
locations, authority or stored saves. Partial projection failures roll back retained
representations through the existing checkpoint boundary.

Schemas 1–6 without coordinates migrate to an explicit legacy fallback: saved
boundary, selected origin, or exact recorded local settlement. Their former field
projection determines legacy membership up to capacity, including clearing stale
authored home regions on those field members. Other assignments remain abstract.
Discarded ordinary movement cannot be recovered; explicit carried position records
are preserved and validated. The compatibility manifest, generic envelope, release
inspection and English documentation now advertise schemas 1–7.

All **203 pinned Wurst tests**, **150 Python tests**, and the real canonical
folder-map compilation passed. Validation results and 60 source hashes are recorded in
[validation.json](issue-389/validation.json). Interpreter tests replace native
movement/projection and storage boundaries while running production save/load,
startup, migration, navigation and transaction code. Python campaign packaging uses
its recording compiler and inspects actual materialized MPQ/pathing payloads for all
17 maps. A separate pinned compiler builds the canonical folder map.

The full Wurst test set is executed in two fresh interpreter processes: startup,
then all remaining tests. Earlier monolithic attempts exceeded the pinned
interpreter's 20-second per-test limit in catalogue registration late in the run.
Only test annotations outside each batch are removed in container-private copies;
production code and scenario data are unchanged. Both batches together must cover
every discovered test exactly once. The worktree is mounted read-only, builds run
as the image's `wurstuser`, and source/build writes stay under private `/tmp`.
The input copy is prepared using the shared map packager's `generate` and `_assemble`
functions with `package.json`, the same assembly path used by `run_wurst_tests.py`.
The [validation script](issue-389/validate.sh) records the exact batching/build steps.
It takes the assembled compile directory as its first argument; the final run used
`_build/issue-389-review/final/compile` through the read-only `/source` mount.
The current Python run covers persistence, autosaving, navigation, boundary
arrival, origin generation, compatibility, execution-evidence checks, runtime
acceptance, map/campaign packaging, release blockers, upload inspection and
recovery documentation. Suite commands and logs are listed in `validation.json`.

Release status remains **blocked_pending_real_forsaken_kingdom_launch_smoke**.
No real-client launch/gameplay validation or player QA was performed. No commit,
push, issue/PR modification, service installation or global tooling change was made.
