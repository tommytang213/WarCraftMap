# Issue #469: military-tradition combat effects

The implementation and its original validation are recorded in `validation.json`.
`repair-validation.json` records the earlier release-report freshness repair.
The first PR #477 CI repair is recorded in `ci-repair-validation.json` and the
`ci-repair-*` transcripts alongside it. The subsequent timeout repair is recorded
in `ci-followup-validation.json` and the `ci-followup-*` transcripts.

Both [the world build](https://github.com/tommytang213/WarCraftMap/actions/runs/38217239265/job/114704727368)
and [the campaign build](https://github.com/tommytang213/WarCraftMap/actions/runs/38217239245/job/114704727401)
passed 530 of 531 Wurst tests, then timed out in
`generatedTreasuresRoundTripWithHeroQuestAndEquipmentProgress`. That fixture
restored every generated treasure twice in one test, exceeding the pinned
interpreter's 20-second limit during snapshot validation.

That first repair partitioned treasures into four deterministic
intervals, using the existing hero/quest batching approach. Full production
registration and treasure resolution still execute. Every generated treasure is
restored in a batch, and the first discovered treasure remains in each batch
alongside the progressed hero, equipment, research, quest reward and guidance.
Every batch retains both restore/reconcile passes and complete snapshot equality
assertions. Production code, authored content, save formats, the compiler timeout
and official release gates are unchanged by this repair.

Local validation of that repair passed **534/534** Wurst tests, including all
**41** military combat callback tests and the four treasure batches. The execution verifier finds
complete passing production-entry journeys for all **23** configured systems.
The selected Python suites pass **75/75** tests, covering combat effects,
tradition authority and generation, military state, save compatibility, treasure
resolution, roster predicates, release-blocker checks and framework conformance.
The JSON report records the pinned typecheck and standalone original/mutated
framework build results, source identity and transcript hashes.

The pinned compiler and bundled Java were copied from the cached image into
ignored worktree-local build storage using a temporary stopped container with no
worktree mounts. Validation then ran locally. The standard-library revision is
recorded in the JSON report. No global tooling, services, commits, pushes or
GitHub writes were needed.

The next [world build](https://github.com/tommytang213/WarCraftMap/actions/runs/38227319305/job/114737901434)
and [campaign build](https://github.com/tommytang213/WarCraftMap/actions/runs/38227319224/job/114737902004)
still exceeded the same 20-second limit in three and two treasure batches,
respectively. Partitioning happened after `generatedRpgWithProgress()` resolved
all 28 seeded treasures. Every hero, quest and treasure batch therefore paid
for the entire catalogue's SHA-based choices before discarding most records.

The fixture now selects its batch immediately after full production registration,
before populating progress and resolving treasure choices. This reduces seeded
treasure resolutions across the 14 batches from **392 to 41**. All 28 authored
treasures remain covered; their candidate sets are disjoint. Each batch still
registers a fresh destination runtime, retains the progressed first hero, quest
and treasure with equipment and research, and performs both production
restore/reconcile passes with complete snapshot equality checks. The existing
authored treasure vectors and exclusive-candidate tests remain in the full suite.
No production code, authored data, save format, timeout or release gate changes
are part of this follow-up repair. Validation uses the existing worktree-local
pinned compiler and Java; no container or global tooling changes are needed.

Follow-up validation passes **534/534** Wurst tests, including all **41** combat
callback tests and all **14** generated-record batches. Source-bound execution
verification confirms complete journeys for all **23** configured systems.
All **81** selected Python tests, the pinned typecheck and both original/mutated
standalone framework builds also pass. `ci-followup-validation.json` records the suite results, compiler
identity, source hashes and compressed transcripts for this repair.

The real-client crash tracked by **#438 remains unresolved**. Headless and
compiler checks do not establish native launch success. Unbound discipline and
maneuver consumers, and starting forces lacking authored weapon identities,
remain explicit blockers; no recipients or weapon assignments were invented.
No player QA was requested.
