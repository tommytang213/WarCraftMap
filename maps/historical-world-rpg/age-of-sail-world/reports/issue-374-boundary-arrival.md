# Issue 374: saved boundary correspondence drives party placement

Base revision: `075e07deb1aff8f8f39e47cdd0d857fb301a003b`. This report describes
the uncommitted implementation in the isolated issue worktree.

Destination startup resolves the saved boundary ID to the generated destination
edge and segment, then interpolates the already-transformed saved position.
The unique reverse boundary supplies explicit destination geometry. Source
triggers and destination placement use the same physical playable bounds,
including W3I margins and each generated map's dimensions. Reversal, scale and
offset run once in the source coordinator. Selected-origin startup continues
to use the authored settlement placement independently of settlement objects.

The shared navigation generator derives connected components from the terrain
raster used for packaged WPM. Arrival resolution stays within 512 world units
of the corresponding edge point, uses the nearest entry component for the
movement class, and checks local native pathing. Candidate rows lie 192, 320
and 448 units inward; accepted points remain outside every 128-unit edge
trigger strip. No connected candidate means rejection. The current party
projection reconstructs land heroes, so sea-only arrivals are rejected instead
of silently disembarking at a distant settlement. The reusable resolver also
tests naval connectivity and rejects decorative/disconnected water.

Preflight precedes save mutation and commit; loading still follows successful
commit. Destination rejection retains the transfer checkpoint and keeps startup
and autosaves locked until a successful retry. Existing registration and
selector-handoff ordering are retained. Registration checks explicit completion
of boundary configuration, so a supported single-map campaign with no routes
can still start at its authored origin. The implementation adds no persisted
fields: schemas 1–6 and their migration paths remain supported. Boundary
metadata and pathing spans are generated configuration, not campaign authority.

The pinned Wurst interpreter passed **132/132 tests**
([results](issue-374/execution.json), [transcript](issue-374/execution.log.gz)). Production lifecycle
tests record distinct destination coordinates at 0.25, **0.37**, and 0.5 on the
same generated boundary. They also cover reversed and partial segments,
unequal dimensions, scale/offset, outward/return travel, populated campaign
authority, origins without city objects, all supported transfer envelopes,
unavailable arrivals, malformed IDs/coordinates/maps, failed commits, and
incomplete versus empty boundary registration.
Coordinate comparisons allow 0.01 world units for Warcraft float rounding.

All **127 targeted Python tests** passed: 7 boundary-arrival, 26 navigation,
20 runtime-acceptance, 12 map-packaging, 23 campaign-packaging, 6 release-save
compatibility, 9 execution-gate, and 24 campaign-save, cross-map persistence and
native-save regression tests. These include deterministic campaign
build comparisons using the recording compiler, actual MPQ materialization and
pathing inspection for all physical maps, and rejection of tampered packaged
pathing. The complete campaign-packaging suite passed against the final
implementation, including the deterministic build comparison.

The real pinned-toolchain campaign build also passed: all **17 physical maps**
compiled, materialized, and passed archive/pathing inspection. Final campaign
archive inspection passed in the container and after copying the artifact back
to the worktree. The generated 24,470,584-byte campaign is retained under
`_build/issue-374-validation/AgeOfSailWorldCampaign.w3n`, with SHA-256
`0dd775d102400872c996cb95dc5796d1b517b6c8b1732717b9bf43d4ddcb956c`.
[Validation summary](issue-374/validation.json) records the checks and artifact.

All 49 executed project Wurst source hashes, including regenerated ScenarioData
and the new shared resolver, [match the final source snapshot](issue-374/input-comparison.json). Validation uses a
read-only worktree mount and a container-private copy under `/tmp`; builds run
as `wurstuser`. No worktree ownership or permissions were changed in a container.

Actual Warcraft launch/gameplay validation was not performed. Release status
remains **`blocked_pending_real_forsaken_kingdom_launch_smoke`**. No player QA,
commit, push, issue/PR modification, or publication was requested or performed.
