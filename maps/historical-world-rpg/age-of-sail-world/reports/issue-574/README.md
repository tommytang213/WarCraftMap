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
