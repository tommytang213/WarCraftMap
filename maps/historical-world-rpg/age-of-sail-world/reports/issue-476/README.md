# Issue #476: active quest map guidance

Separate registered Show on Map and Track actions now resolve authoritative active
objectives and authored return destinations into scoped regional focus and exact
local markers. The implementation and player commands are documented in
[QUEST_MAP_GUIDANCE.md](../../docs/QUEST_MAP_GUIDANCE.md).

The controller does not mutate visit knowledge, physical positions, military
orders or command rights. Invalid and unavailable actions reject before map focus
or modal ownership changes. Existing exact settlement knowledge may upgrade broad
guidance; unmet clue gates still reject. Approximate guidance without earned exact
knowledge remains unavailable until bounded search areas are implemented.

Tracking retains its existing save encoding. Markers and focus are disposable
projections. Successful loads and physical transitions reconstruct guidance;
staged or failed loads preserve existing markers, tracking and pause ownership.
No save schema migration or incremental player QA is required.

`validation.json` records final checks and transcript hashes. The scoped report
verifies current source identity, the pinned compiler, every executed test, all
configured production-entry journeys, nine live/headless differential vectors,
actual compiled quest/guidance definitions, and original/mutated framework builds.
The packaged diagnostic W3X contains the same source identity as execution.
Generated map binaries remain under ignored `_build/` storage.

Reproduce from the campaign directory with a local offline Grill wrapper:

```sh
python3 reports/issue-476/validate.py --grill <local-offline-grill> --group navigation --build-dir _build/issue476-navigation --package
python3 reports/issue-476/validate.py --grill <local-offline-grill> --group remaining --build-dir _build/issue476-remaining
python3 reports/issue-476/validate.py --grill <local-offline-grill> --group rpg --build-dir _build/issue476-rpg
PATH=<local-offline-grill-directory>:$PATH python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign
python3 tooling/requirement_traceability_audit.py --write --check
```

The wrapper uses the repository-pinned compiler and bundled Java copied from a
stopped cached container, plus a cached standard library. No container ran or
mounted this worktree, and no global tooling or services changed. The compiler and
standard-library identities are retained in `validation.json`.

Exploratory full runs exposed the help pagination change and exceeded the pinned
20-second per-test limit in existing large treasure fixtures. Final execution uses
three disjoint groups in fresh interpreters. Only `@test` selection changes in
private assemblies; every source function is typechecked and every test remains
in the union. `report.py` verifies each original transcript, its precise input
transformation and source hash, complete test membership, and production journeys
within individual passing tests. It does not synthesize a combined compiler run
or relax timeouts. The repository worker still performs its authoritative gate.

The retained Python transcripts cover quest generation/journal/events, headless
map parity, discovery, interactions, supported saves and migrations, persistence,
autosaves, framework boundaries, traceability and release-report freshness. The
source-only release audit remains failed with its existing publication blockers;
refreshing its input hash does not relax any gate.

REQ-0284 breadcrumbs, production clue acquisition, bounded search-area rendering,
non-settlement earned point knowledge, custom frame presentation (#440), native
Warcraft launch (#438) and broader release obligations remain downstream. Scoped
completion is not a claim that all of ROAD-0064 or REQ-0281–REQ-0295 is complete.
