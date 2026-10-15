# Issue #523 verification

The bounded scenario contract is documented in
[CELESTIAL_NAVIGATION.md](../../docs/CELESTIAL_NAVIGATION.md). A fully eligible
station-return circuit consumes 48 provisions against the same-condition
50-provision control. Research never supplies the observation kit or relaxes
full provisioning, route, hull, knowledge or station requirements.

`focused-wurst.json` and its compressed transcript retain **85 passing tests**
from the pinned Wurst compiler. The compiler JAR SHA-256 is checked against the
repository pin. All production Wurst sources and all selected test sources were
also compared with the instrumented input hashes after the run. The suite
includes the new registered voyage/research commands, campaign-day resolution,
active/unloaded parity, interruption, equipment removal, controller transfer,
shared/repeated entitlements, save/resume, migration and late campaign-load
rollback. It also includes research cost/runtime, military order/settlement and
framework contract regressions. Unselected test functions remain available as
fixture dependencies but have their test annotations removed in the temporary
execution assembly. This is focused evidence, not full-suite release evidence.

`validation.json` indexes **166 passing Python tests**, including navigation,
vessel progression, military state, research generation/costs, framework
conformance, generated-payload tampering, and all three audit tool regressions.
Framework orchestration unit tests use synthetic compiler protocol fixtures;
their transcripts do not establish real compiled campaign or native-client
execution. The framework boundary audit also passes.

The pinned image ran as its normal `wurstuser` with read-only input mounts.
Source was copied into container-private `/tmp` before dependency installation,
typechecking or tests. No worktree ownership, global tooling or service changes
were made. Generated output is not authoritative source.

The release-blocker, runtime-acceptance and requirement-traceability reports
were regenerated with the full base revision and a hash of this worktree's
actual source inputs. The Celestial Navigation consumer finding is absent;
**217 other unbound research consumers remain**. Source-only audits still block
publication because full same-revision execution/artifact evidence is absent;
no remaining blocker is waived. Full repository validation and regeneration on
the integrated main revision belong to the controller. No player QA was used.

The integration repair is recorded separately in `repair-validation.json` and
`repair-wurst.json`, with fresh compressed transcripts. It aligns the release
save manifest with the live military v10 codec and its v1–v10 migration support,
and refreshes all three acceptance reports on the integrated revision. These
checks supersede the original verification above for the current worktree;
full repository validation remains assigned to the controller. Grill normalizes
its dependency metadata during installation, so the focused run verifies that
normalized build file and every copied Wurst source across compilation and tests.

The latest integration retry is indexed by `retry-validation.json` and
`retry-wurst.json`, with fresh compressed transcripts. The reported failures
were stale revision identities in the acceptance reports after integration;
all three reports have been regenerated for revision
`688d86690b8bad78c0060af854fface5d9014908`. The gameplay source hash is unchanged.
The retry reruns the failing report-freshness tests, focused voyage and adjacent
system tests, pinned Wurst typechecking and focused production execution.
Its compiler input mount is read-only and all build writes are container-private.
Publication blockers remain unwaived. The controller must regenerate these
reports again after integration onto a new main revision.
