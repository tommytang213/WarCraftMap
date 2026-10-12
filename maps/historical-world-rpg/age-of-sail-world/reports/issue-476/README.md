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
python3 reports/issue-476/validate.py --grill <local-offline-grill> --group all --build-dir _build/issue476-all --package
PATH=<local-offline-grill-directory>:$PATH python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign
python3 tooling/requirement_traceability_audit.py --write --check
```

The wrapper uses the existing worktree-local repository-pinned compiler, bundled
Java and cached standard library. The initial implementation copied these from a
stopped cached container. This repair uses no containers, global tooling changes
or services. Compiler and standard-library identities remain in `validation.json`.

The outer validator reported 541/544 passing tests: three generated treasure
round-trip fixtures timed out during seeded SHA-256 resolution. The repair splits
the four treasure intervals into fourteen, reducing the largest fixture from
eight to three records. All 28 treasures still execute production registration,
seeded resolution, two restore/reconcile passes and complete snapshot equality;
each fixture retains the discovered first treasure and hero/quest/equipment
progress. `retain.py` verifies complete interval coverage against generated data.
Batching alone exposed accumulated fixture allocations: the interpreter eventually
ran out of heap. Discarded definitions and completed standalone fixtures now
release their owned objects, including nested definitions. The generated shared
interaction catalogue remains borrowed and alive. This keeps repeated full
registration from retaining every discarded catalogue for the entire test run.
Production code, scenario content, save formats and the compiler's 20-second limit
are unchanged by the repair.

Final execution uses one complete interpreter run with unchanged test decorators.
`report.py` uses the repository's production evidence verifier to require every
current test and its actual production calls in that transcript. The
`all-results.json.gz`, `all-execution.log.gz` and `all-typecheck.log.gz` files are
the repair evidence; earlier navigation/remaining/rpg group logs are historical
and are not used for current validation. The repository worker still performs its
authoritative gate.

The retained Python transcripts cover quest generation/journal/events, headless
map parity, discovery, interactions, supported saves and migrations, persistence,
autosaves, framework boundaries, traceability and release-report freshness. The
source-only release audit remains failed with its existing publication blockers;
refreshing its input hash does not relax any gate.

REQ-0284 breadcrumbs, production clue acquisition, bounded search-area rendering,
non-settlement earned point knowledge, custom frame presentation (#440), native
Warcraft launch (#438) and broader release obligations remain downstream. Scoped
completion is not a claim that all of ROAD-0064 or REQ-0281–REQ-0295 is complete.
