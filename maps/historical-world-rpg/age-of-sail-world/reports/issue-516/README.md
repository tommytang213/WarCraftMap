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
