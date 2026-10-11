# Issue #471 validation

This scope covers persistent region/visited-settlement knowledge, authorized
world/regional listings and `/map focus <settlement-id>`. It retains quest
guidance, clue/search-area presentation, #440 and native-launch blockers.

Final validation:

- Pinned Wurst typecheck and **258/258** execution tests across 19 selected suites
  passed. These include production interaction/command adapters, questless and
  rejected visits, save migration, failed storage, rollback, physical travel,
  remote command/return, pause ownership and treasure preservation.
- **66** focused Python tests and **72** traceability/release-evidence tests
  passed. The discovery cases compare the live catalogue and command policy
  with `engine/map_discovery.py`.
- The compiled diagnostic map contains **7 regions and 827 settlements** with
  definitions matching the generated catalogue and the knowledge/map-command
  implementation present in Lua.
- Original and content-mutated framework campaigns each passed **2/2** Wurst
  tests and campaign packaging with unchanged shared framework sources.
- World validation, framework boundary audit, traceability consistency and
  `git diff --check` passed.

The final source tree hash is
`1a88cb2b90549a39d50b802b0bf79afd307f2b29dcc81376d7d37b6b606b6166`.
Execution and packaged definitions record the same hash. Legacy research and
recruitment fixtures were updated for schema 10 before this final run. This is
scoped execution evidence, not a new full-suite or native-client validation.
The broader release audit retains its unresolved campaign/publication blockers.

`validate.sh` uses the pinned Wurst compiler with the worktree and cached
dependencies mounted read-only. It copies sources into container-private `/tmp`
before compiling. `VISITS_TARGETED=1 VISITS_PACKAGE=1` selects the relevant
execution suites and builds a diagnostic map, then validates the original and
content-mutated framework campaigns. Test selection changes only the private
copy; all source functions are still typechecked. No player QA is involved.
`PACKAGE_ONLY=1` skips the main execution suite when packaging and framework
checks run independently alongside an execution container with the same source.

`report.py` verifies compressed execution transcripts, current source hashes,
packaged catalogue equality, compiled command/knowledge code and framework
evidence before regenerating `scoped-traceability.json`. The source tree hash
binds the uncommitted implementation to its recorded base revision. The scoped
result does not promote downstream guidance or native-client work to complete.
