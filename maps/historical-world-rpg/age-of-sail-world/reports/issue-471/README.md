# Issue #471 validation

This scope covers persistent region/visited-settlement knowledge, authorized
world/regional listings and `/map focus <settlement-id>`. It retains quest
guidance, clue/search-area presentation, #440 and native-launch blockers.

Final validation after integration repair:

- Pinned Wurst typecheck and **258/258** execution tests across 19 selected suites
  passed. These include production interaction/command adapters, questless and
  rejected visits, save migration, failed storage, rollback, physical travel,
  remote command/return, pause ownership and treasure preservation.
- **59** focused Python tests and **72** traceability/release-evidence tests
  passed. The discovery cases compare the live catalogue and command policy
  with `engine/map_discovery.py`.
- **47** campaign-packaging/runtime-acceptance Python tests passed, including
  both reproduced validation failures. Their synthetic compiler fixtures test
  packaging orchestration and binary structure, not Wurst execution.
- The compiled diagnostic map contains **7 regions and 827 settlements** with
  definitions matching the generated catalogue and the knowledge/map-command
  implementation present in Lua.
- Original and content-mutated framework campaigns each passed **2/2** Wurst
  tests and campaign packaging with unchanged shared framework sources.
- World validation, framework boundary audit, traceability consistency and
  `git diff --check` passed.

The final source tree hash is
`7c4699d6e36551b985346c4924edc063313cb0d95ec54cb6abcd737a97387b78`.
Execution and packaged definitions record the same hash at base revision
`d800afc7c80a51428716cd8d12d5b0fe6acd5b2c`. This is scoped execution evidence,
not a new full-suite or native-client validation. The broader release audit
retains its 241 unresolved campaign/publication blockers.

The repair preserves the issue implementation. The bootstrap dependency fixture
now includes `DiscoveryKnowledge` and its `PhysicalInteraction` visit-listener
contract, imported through generated `ScenarioSettings`. The runtime artifact
fixture uses the supported schema list from the compatibility matrix, so it
reaches its intended acceptance/checksum checks with schema 10. No production
gate was relaxed.

`validate.sh` uses the pinned Wurst compiler with the worktree and cached
dependencies mounted read-only. The repair run used a non-root, offline
container. It copies sources into container-private `/tmp`
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
