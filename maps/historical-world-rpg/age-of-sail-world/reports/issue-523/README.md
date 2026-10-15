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

The preceding integration retry is indexed by `retry-validation.json` and
`retry-wurst.json`, with fresh compressed transcripts. The reported failures
were stale revision identities in the acceptance reports after integration;
all three reports have been regenerated for revision
`688d86690b8bad78c0060af854fface5d9014908`. The gameplay source hash is unchanged.
The retry reruns the failing report-freshness tests, focused voyage and adjacent
system tests, pinned Wurst typechecking and focused production execution.
Its compiler input mount is read-only and all build writes are container-private.
Publication blockers remain unwaived. The controller must regenerate these
reports again after integration onto a new main revision.

The current integration repair is indexed by `current-validation.json` and
`current-wurst.json`, with fresh compressed transcripts. All three acceptance
reports now identify revision `4718d772a20d94d5aa8470a85f7d634460a1e3c3`;
the gameplay source hash is unchanged. The previously failing release-blocker
and requirement-traceability freshness tests pass. This run exercises 169 Python
tests and 96 pinned Wurst tests, including framework conformance, and verifies
generated payloads and compiler input hashes. The compiler runs as its default
`wurstuser`, with a read-only temporary input mount and all build writes in
container-private `/tmp`. No gameplay changes or blocker waivers were needed.
The controller still owns complete repository validation and report regeneration
after integration onto a new main revision.

The final repair is indexed by `integrated-validation.json` and
`integrated-wurst.json`, with fresh compressed transcripts. It retains the
voyage implementation and fixes the recurring report-only checkpoint failure:
the two checked-in-report tests now recompute at each report's recorded revision
and compare all current source hashes and report bytes. A generated-report commit
can no longer invalidate its own revision field. Publication gates still require
the explicitly tested release revision; source changes, changed findings and
remaining blockers receive no exemption. Both tests also pass with a simulated
newer implicit revision, without creating a commit.

This snapshot passes 169 Python tests, those two checkpoint regression checks,
71 selected pinned Wurst tests, Wurst typechecking, framework conformance and
boundary checks, and generated-payload verification. All three audits were
regenerated at `ef605e5a9dcf13e5cb849b4a29ff9da2306256e8` with the repaired
source hash. The Celestial Navigation finding is absent; 238 campaign blockers
remain. Full repository validation remains assigned to the controller. Native
client execution was not run, and no player QA or blocker waiver was used.
