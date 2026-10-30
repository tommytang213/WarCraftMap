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
preflight. Existing release audit outputs have not been rewritten. Neither this
focused report nor a later merged PR establishes release-blocker closure. No
player QA was requested.
