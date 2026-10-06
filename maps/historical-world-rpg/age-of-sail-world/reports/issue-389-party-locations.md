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

After integration with current main, all **228 pinned Wurst tests** passed in one
interpreter run through the unchanged `./tooling/package_release.sh` gate. Its
dependency installation, typecheck, canonical Lua compilation, map assembly and
archive inspection also passed. All **217 Python tests** passed: 97 targeted
persistence/navigation/compatibility checks, 53 packaging/release checks and 67
automation checks. Results, commands, transcript hashes and 60 verified current
Wurst source hashes are in
[integration-validation.json](issue-389/integration-validation.json).

The import conflicts in startup and load-transaction tests retain both the party
location and management-screen regressions. Startup fixtures now destroy discarded
generated catalogue records before reducing their counts. Previously, each fixture
retained an entire world: a diagnostic full-suite run filled nearly all of the
interpreter's 4 GB heap and recorded 11 timeouts before being stopped. The cleanup
retains full production registration, the same authority slices and assertions,
every test annotation, and the pinned 20-second per-test limit. No production
persistence or management behavior changed during this integration repair.

Interpreter tests replace native movement/projection and storage boundaries while
running production save/load, startup, migration, navigation and transaction code.
Python campaign packaging uses its recording compiler and inspects materialized
MPQ/pathing payloads for all 17 maps; actual pinned compilation and packaging cover
the canonical folder map. World, geography, map-source, recovery-documentation and
diff checks also passed. Container validation mounted the worktree read-only and
built as `wurstuser` from copies under private `/tmp`.

The earlier [validation.json](issue-389/validation.json) and
[batched validation script](issue-389/validate.sh) are retained as historical
development evidence. The complete integration run supersedes those batches for
repository readiness; the outer worker performs the authoritative repository check.

Revalidation from checkpoint `b0a44d0` again passed all **228 pinned Wurst tests**
in one complete interpreter run, followed by canonical Lua compilation and map
packaging. All 60 checked-in Wurst inputs match the passing execution evidence.
All **220 Python checks** also passed: 97 targeted, 53 packaging/release and 70
automation tests, including the three new failure-log regressions.
The outer worker's reported execution failure did not recur, so this retry
preserves the production implementation and existing tests. See
[revalidation.json](issue-389/revalidation.json) for the current evidence.

The repository runner now prints the container's Wurst execution transcript on
failure before `--rm` removes it. The previous error referenced a log inside the
deleted container and did not expose the failing test or interpreter exception.
Automated shell regressions verify transcript forwarding, failures without a log,
quiet successful execution, and preservation of the original exit status. The
pinned compiler, complete-suite gate, timeout and read-only source mount remain
unchanged.

Release status remains **blocked_pending_real_forsaken_kingdom_launch_smoke**.
No real-client launch/gameplay validation or player QA was performed. No commit,
push, issue/PR modification, service installation or global tooling change was made.
