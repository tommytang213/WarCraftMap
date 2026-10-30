# Issue #574 focused developer validation

The implementation adds the Coastal Triangulation source to the existing paid
voyage authority, with an independently commissioned chart/bearing kit and one
shared provision-credit bucket. The design and migration contract is in
[COASTAL_TRIANGULATION.md](../../docs/COASTAL_TRIANGULATION.md).

Local validation passed **44 pinned Wurst tests**, **86 distinct Python tests**,
and current generated catalogue/executable/consumer-metadata/provenance
verification. The Wurst run covers CoastalNavigationTests,
NavigationEfficiencyTests, ScienceExplorationTests and the pinned compatibility
fixture. The complete source assembly was typechecked with zero errors. Existing
compiler warnings remain in the transcript.

Wurst ran offline in the pinned image recorded in `focused-validation.json`.
The worktree and cached standard library were mounted read-only. Source was
copied into container-private `/tmp`; generated assembly and instrumentation were
used only there. Other tests' annotations were disabled in that private copy.
Every required probe was observed inside the isolated registered coastal-only
comparison, including actual commissioning payment, voyage start,
qualification, resolution and source-credit commit. No predecessor CI result or
artifact was used as evidence for this implementation.

Python validation used `python3 -m unittest discover -s
maps/historical-world-rpg/age-of-sail-world/tests -p PATTERN` with:

- `test_*navigation*.py` (48 tests), with final reruns of the eight coastal
  arithmetic/migration tests and 12 navigation/generation tests after their last
  changes. Generated tampering cases cover coastal identity/rate, bearing days
  and consumer metadata even when output hashes are recomputed.
- `test_science_exploration.py` (5 tests).
- `test_research_generation.py` (11 tests).
- `test_coastal_binding_evidence.py` (5 tests).
- `test_barometric_binding_evidence.py` (5 tests).
- `test_botanical_binding_evidence.py` (6 tests).
- `test_calculus_binding_evidence.py` (6 tests).

Synthetic verifier transcripts in the Python tests are protocol regressions,
never release evidence. The archived focused report deliberately uses a separate
format and cannot satisfy the full-suite closure verifier.

Complete repository/framework validation, the complete pinned Wurst suite, and
all three integrated-main audits remain with the controller after integration
preflight. The original focused run did not rewrite release audit outputs. Neither this
focused report nor a later merged PR establishes release-blocker closure. No
player QA was requested.

## Post-merge validation repair

The merged worktree retained schema v21 in the release save manifest and the
runtime integration source marker, while the coastal implementation writes v22.
Both now advertise v22, including all supported military source schemas 1–22.
The release-blocker, runtime-acceptance and requirement-traceability source
snapshots were regenerated for this worktree. Static runtime readiness passes;
the snapshots retain missing execution/artifact blockers, including the coastal
identity, pending complete pinned evidence on integrated main.

Fresh focused Python runs pass navigation (48), coastal evidence (5), science
compilation (5), research generation (11), release save compatibility (6), runtime
acceptance (25), requirement traceability (54), release-blocker audit (10), and
sibling barometric (5), botanical (6) and calculus (6) evidence: 181 tests total.
Framework boundary, both scenario world validators, Europe geography and map
source validation also pass.
The original pinned Wurst transcript above predates this integration repair;
the controller must obtain fresh complete-suite evidence for the final source
digest. No commits, remote changes or player QA were performed.

## Execution-gate timing repair

The controller's complete Python run reached 1,260 tests with one failure: a
host-dependent terrain generation timeout preempted the execution-failure
packaging regression. The execution-gate fixture now supplies a deterministic
clock only to the terrain generator while retaining real generation, validation,
typechecking and the execution gate. Execution timeouts use their normal clock.
Production terrain budgets are unchanged; a new deterministic terrain regression
also verifies that an over-budget generation still fails.

Fresh focused runs pass **99 distinct Python tests**, including all 23 execution
tests and all seven Europe terrain tests. Results and compressed transcripts are
recorded in `execution-gate-repair-validation.json`. The execution-gate tests use
the synthetic compiler protocol; these developer checks are not pinned Wurst
execution or release closure evidence. Complete repository validation, pinned
Wurst execution and all three integrated-main audits remain with the controller.

## Integrated audit freshness repair

The next complete validation passed 1,259 of 1,261 Python tests; its two failures
identified stale release-blocker and runtime-acceptance source snapshots. All
three audit snapshots now record integrated revision
`06d7032585920fb346e730d7b92fd7de092764db` and source digest
`0e0a5d727f46ada6f50546d636a566c996c996f5f5bb51efd2999461131ecb09`.
Only source identity fields changed. Their existing human reports remain current.

Fresh focused validation passes **162 Python tests**: 73 navigation, coastal
evidence, science, research generation and save-compatibility tests; 79 runtime
acceptance and requirement-traceability tests; and ten release-blocker tests.
Both previously failing freshness checks pass. Commands, compressed transcripts
and hashes are in `audit-freshness-repair-validation.json`.

These are source-only audit snapshots and focused developer checks. Existing
release blockers, including Coastal Triangulation pending complete pinned
evidence, remain explicit. Complete repository/framework and pinned Wurst
validation, followed by integrated-main evidence regeneration, remain with the
controller. No gameplay implementation, gate, or player validation requirement
changed during this repair.

## Civic/voyage legacy-fixture integration repair

The controller's next pinned run failed the combined civic/voyage migration
test. Its synthetic v10 save retained the new v22 `x` source-attribution records;
the production parser correctly rejected that mixed-format input. The fixture
now removes both source records when constructing the legacy save, explicitly
checks rejection and rollback for the mixed-format input, and checks that the
genuine legacy save preserves celestial equipment, elapsed days and reserved
provisions with zero unearned source fractions. Production behavior is unchanged.

Fresh focused validation passes **72 pinned Wurst tests** across civic, coastal,
celestial, science and framework suites, including the previously failing test.
The complete source assembly remains present; other suites' test annotations
were disabled only in the disposable assembly. The pinned compiler ran offline
with read-only inputs and all build writes in container-private `/tmp`.
Generated-output verification and the framework boundary audit also pass.
**173 focused Python tests** pass, including all three audit regressions.

All three source-only audit snapshots were regenerated at integrated revision
`368f4a74999b9a3b21ab6b9777e832b86cfd7917` with source digest
`5cd4bac03a053a73bc3362c4bc35b0b6c50c4a8e98c5a9a99efde071b9b04234`.
They retain existing release blockers. Commands, counts and compressed transcript
hashes are recorded in `civic-migration-repair-validation.json`. These focused
results do not establish release closure; complete repository validation, the
complete pinned suite and integrated-main evidence remain with the controller.
