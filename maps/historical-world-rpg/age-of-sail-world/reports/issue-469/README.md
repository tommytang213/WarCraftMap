# Issue #469: military-tradition combat effects

The implementation and its original validation are recorded in `validation.json`.
`repair-validation.json` records the earlier release-report freshness repair.
The current PR #477 CI repair is recorded in `ci-repair-validation.json` and the
`ci-repair-*` transcripts alongside it.

Both [the world build](https://github.com/tommytang213/WarCraftMap/actions/runs/38217239265/job/114704727368)
and [the campaign build](https://github.com/tommytang213/WarCraftMap/actions/runs/38217239245/job/114704727401)
passed 530 of 531 Wurst tests, then timed out in
`generatedTreasuresRoundTripWithHeroQuestAndEquipmentProgress`. That fixture
restored every generated treasure twice in one test, exceeding the pinned
interpreter's 20-second limit during snapshot validation.

The generated-record fixture now partitions treasures into four deterministic
intervals, using the existing hero/quest batching approach. Full production
registration and treasure resolution still execute. Every generated treasure is
restored in a batch, and the first discovered treasure remains in each batch
alongside the progressed hero, equipment, research, quest reward and guidance.
Every batch retains both restore/reconcile passes and complete snapshot equality
assertions. Production code, authored content, save formats, the compiler timeout
and official release gates are unchanged by this repair.

Fresh execution passes all **534/534** Wurst tests, including all **41** military
combat callback tests and the four treasure batches. The execution verifier finds
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

The real-client crash tracked by **#438 remains unresolved**. Headless and
compiler checks do not establish native launch success. Unbound discipline and
maneuver consumers, and starting forces lacking authored weapon identities,
remain explicit blockers; no recipients or weapon assignments were invented.
No player QA was requested.
