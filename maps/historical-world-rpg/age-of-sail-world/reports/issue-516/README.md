# Issue #516 focused development evidence

The four typed naval research consumers use `NavalServices` and
`NavalCampaignRuntime`, generated from the approved design and existing roster.
The design dependency is merged as `9db8952` (#511). This implementation starts
from `1c5ae80`; `focused-validation.json` identifies the uncommitted worktree's
exact source contents. No predecessor branch or CI artifact was used.

Production checks compare paid 115/100 hull repairs, close cannon hits of
110/100, and voyage weather loss of 368/400. Recruitment research grants no ship;
its 1540-currency/700-crew roster purchase takes 180 days after paid infrastructure
and the separate naval-board choice. Negative, duplicate-source, capture,
active/inactive, save/migration and late rollback cases are in the same test file.
The installed weapon callback test uses recording native boundaries with the
production event router. The long-campaign fixture checks 50 years of bounded
weekly exposure/repair and exact fractional conservation; it is not evidence of
historical national outcomes or native-client performance.

The focused compiler run uses the repository's immutable Wurst image
`frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`.
The worktree is mounted read-only and the compile tree is copied to container
private `/tmp`. Production source is unchanged; only unrelated `@test`
annotations are removed from that disposable test copy. The retained selection
contains all naval, navigation and science tests, the four Cast Cannon tests,
and the compatibility compile fixture. Naval production probes use the
repository's `integration_evidence.instrument_tree`; the integrated passing test
must hit all seven naval probes. Compressed logs and source hashes accompany the
machine summary.

Python checks cover naval catalogue mutation/sensitivity, research generation,
combat bindings and science compilation. Current-source generation and
`verify_generated` check packaging inputs/provenance; the framework boundary
audit checks the shared/content separation. These are focused development checks,
not a packaged campaign or authoritative complete-suite execution report.

Reproduce the Python selections with `python3 -m unittest discover -s tests -p
'PATTERN'`, using `test_naval_services.py`, `test_research_generation.py`,
`test_combat_effects.py` and `test_science_exploration.py` from the scenario root.
The controller runs the complete pinned repository command after integration;
`python3 ../_shared/tooling/run_wurst_tests.py package.json` is the ordinary
complete Wurst gate, with no test selection or synthetic compiler.

The exact four issue #516 research-unbound release findings remain pending the
controller's fresh integrated current-main execution/runtime/traceability audit.
This directory is not an allowlist or a substitute for that audit. Native campaign
launch #438 remains separately blocked. No release findings, CI evidence, campaign
archives, GitHub state, commits or global tooling are changed here.

Fresh merge integration evidence is in `merge-integration-validation.json` and
its two compressed logs. It records both merge parents and exact generated and
compiled input hashes. The pinned compiler typechecked the integrated production
source and passed 124 focused tests, including land/naval consumers, campaign
registration, save/load rollback, and the version 14 regression that preserves
both legacy `h` record shapes and migrates either version 13 branch. The 49
Python checks include 12 packaging regressions using the repository synthetic
compiler fixture; those packaging fixtures are not real compiled-map evidence.
Fresh campaign/conformance generation, provenance and framework boundary checks
also passed. Full repository and release/runtime/traceability validation remains
with the controller, and this focused report closes no release findings.

Validation repair after integration updates the runtime source-evidence marker
from military snapshot version 13 to the implemented version 14 and regenerates
the runtime, release-blocker and traceability source reports. Fresh focused Python
validation passes 118 tests: naval services (4), research generation (9), release
save compatibility (6), runtime acceptance (24), requirement traceability (53),
release-blocker audit (10) and packaging (12). Packaging uses the repository's
synthetic compiler fixture. No Wurst production or test source changed in this
repair; pinned execution and authoritative complete repository validation remain
with the controller. The source reports retain all execution/artifact blockers
and do not close the four naval research findings.

PR #539 CI repair: the campaign packaging job failed in
`productionCampaignContentContract` at the interpreter's unchanged 20-second
deadline; its separate Wurst workflow passed. The shared conformance fixture now
finalizes migration defaults after bounding its registered authority, releases
discarded civic definitions, and bounds agricultural sites to the retained
settlements. All original gameplay, save/load and travel assertions remain.
A separate shared test verifies full-world production migration defaults in both
campaigns. Production registration and the execution gate are unchanged.

`ci-repair-validation.json` and its compressed transcripts record 117 passing
pinned Wurst tests: the complete current third 100-test execution batch plus all
naval/navigation tests. The integrated naval trace exercises all seven required
production probes. Both shared conformance tests also pass in the reusable
campaign and its renamed-content/price mutation (four executions). All container
inputs were mounted read-only and builds ran as the image's default non-root user
in container-private `/tmp`. Generation/provenance, framework boundary, map source
and traceability freshness checks pass. Refreshed source audit reports preserve
all existing release blockers. These are focused development results; the outer
worker still owns complete repository validation and release evidence.

The repair also passes 38 focused Python tests: naval catalogue/research
generation (13), shared framework packaging/evidence (3), and execution-gate
failure handling (22). Their transcript is `ci-repair-python.log.gz`. Python
compiler fixtures exercise orchestration and fail-closed packaging, separately
from the real pinned interpreter executions above. Broad local Python discovery
was stopped in favor of these selections; it is not claimed as a complete pass.
