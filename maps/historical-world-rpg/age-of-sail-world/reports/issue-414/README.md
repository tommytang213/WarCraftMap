# Issue #414 validation

## Merge integration repair

The eight merge conflicts are resolved while retaining live recovery, main's
settlement authority and protection lifecycle, and both parser optimizations.
Recovery geography now joins the earlier physical-map configuration used by
settlement generation, without generating the same geography twice.

Both branches previously emitted military v4 with different settlement layouts.
Military v5 combines policy and recovery hints, with explicit migration for both
v4 layouts and continued v1–v3 support. The new regression preserves saved hints,
resources and offices, fills absent legacy authority from definitions, repairs
known legacy rawcodes, and rejects mixed layouts without mutation. Campaign v8,
RPG v3, trade v3 and party locations v1 remain supported.

[merge-validation.json](merge-validation.json) records the fresh local validation.
All 345 pinned Wurst tests, 931 scenario Python tests and 129 automation tests
pass. Both framework variants pass 2/2 tests and compile; all 17 campaign maps
compile and pass archive inspection. The 12 recovery obligations have 48 passing
production receipts, and all 16 gameplay maps have four recovery grids verified
against packaged WPM. Main's 12 scoped obligations, all 827 settlement/market
authorities and their projection policies also pass.

The `merge-*` receipts refer to the combined source digest and rebuilt campaign;
the older receipts below describe their own source revisions. Validation uses
the existing worktree-local pinned compiler and bundled JRE, with no containers,
global tooling changes, commits, pushes, GitHub writes or player QA.

After rebuilding, reproduce the scoped receipts and navigation inspection with:

```sh
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-414/verify-ci-repair-evidence.py --prefix merge
```

## PR #423 interpreter timeout repair

The [subsequent Wurst job](https://github.com/tommytang213/WarCraftMap/actions/runs/37787494713/job/113345907853)
ran 327 tests and timed out in four existing campaign recovery/load journeys.
The six live-unstuck journeys passed; both campaign packaging runs and both
repository validation jobs passed. The raw failed-job transcript is retained in
[ci-timeout-github-failure.log.gz](ci-timeout-github-failure.log.gz).

Military catalogue registration now uses temporary stable-ID indexes with full
key comparisons, including hash collisions. The indexes are destroyed before
gameplay, so reconstruction still reads the authority arrays. Military snapshot
parsing scans each record once, preserving empty optional fields and strict
record counts. Campaign field lookup searches backwards for the final value,
preserving embedded trade-store separators and appended authority semantics.
No save schema, recovery policy, journey steps or compiler timeout changed.

Three added Wurst regressions cover collisions and duplicate registration across
reconstruction, malformed military records and recovery hints, and final-value
campaign lookup. The four formerly failing journeys take 6.2–7.6 seconds locally,
versus 9.5–13.2 seconds with the original sources, under the unchanged 20-second
limit. [ci-timeout-timings.json](ci-timeout-timings.json) records the baseline source
identity and before/after results; local timings do not guarantee CI timing.

Fresh validation is recorded in [ci-timeout-validation.json](ci-timeout-validation.json):
330/330 pinned Wurst tests, 229 targeted scenario Python tests, nine release-audit
regressions and 129 automation tests passed. All 17 physical maps were rebuilt
and pass the RC artifact gate. All twelve scoped obligations pass with 48 distinct
production receipts; all sixteen gameplay maps have four movement rasters and
anchors verified against their packaged WPM. The original and content-mutated
framework campaigns each passed 2/2 Wurst tests and compiled with unchanged
shared sources. Source/world validation, framework boundaries, traceability
freshness and `git diff --check` also passed.

This used the existing worktree-local pinned compiler and bundled JRE. No
containers, global tooling changes, commits, pushes, GitHub writes or player QA
were required. Broader publication blockers remain outside this repair.

Reproduce the fresh scoped receipts and packaged navigation inspection after the
pinned suite and packaging driver:

```sh
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-414/verify-ci-repair-evidence.py --prefix ci-timeout
```

## PR #423 CI repair

[The failed campaign job](https://github.com/tommytang213/WarCraftMap/actions/runs/37765519229/job/113272106402)
passed 327 Wurst tests and both campaign builds, then rejected the compiled
Europe map because `registerOriginSelection` was absent as a call. The pinned
optimizer had inlined that one-line wrapper; the actual `origin` command
registration was present. [The reproduction](ci-repair-regression.json) records
the old and repaired check against the same previously compiled archive bytes.

Artifact acceptance now requires the emitted command registration, generated
origin configuration and physical-map loading calls. It still rejects a missing
registration or operation, an unbound compiler alias, comments, string literals,
and the surviving wrapper stack annotation. The new regression test failed with
the original checker before passing with this repair.

Fresh results are recorded in [ci-repair-validation.json](ci-repair-validation.json).
All 327 pinned Wurst tests, including the six live recovery journeys, passed.
The complete scenario Python suite passed all 926 tests.
All 17 physical maps were typechecked, compiled and inspected; the fresh campaign
also passes the exact RC artifact gate that failed in CI. Both framework fixture
variants passed 2/2 interpreter tests and compiled with unchanged shared sources.
The scoped audit passes all twelve obligations with 48 distinct production
receipts. All sixteen gameplay maps have four movement rasters and anchors
verified against their packaged WPM, with map-local transforms retained in the
compressed navigation evidence.

Reproduce the artifact/receipt checks after running the pinned suite and the
packaging driver from the repository root:

```sh
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-414/verify-ci-repair-evidence.py
```

The `ci-repair-*` receipts bind the current dirty source digest and the exact
campaign bytes. Validation used the already available pinned compiler and bundled
JRE in worktree-local storage. The map builds used a second local toolchain copy
to avoid sharing compiler log files with the concurrent interpreter run; the
packaging driver changed only its Grill executable path. No containers, global
tooling changes, GitHub writes, commits, pushes, or player QA were needed.

The merged baseline uses outer campaign schema v8 from issue #413, with RPG v3,
military v4 and party locations v1. This repair changes no save layout or recovery
policy. Broader publication blockers remain outside this issue's scope; passing
artifact inspection does not claim native-client gameplay validation.

## Original implementation evidence

The earlier receipts below describe the source identity in `validation.json`,
before the issue #413 merge and this CI repair.

Live `/unstuck` recovery now uses ordinary party and military representations,
the loaded physical map's generated movement components, and the existing
party/force position authority. Creation, ownership/context changes, retirement,
save/load and reconstruction maintain the registry and validated safe hints.
See [the implementation contract](../../docs/LIVE_UNSTUCK.md).

Validation completed against the source identity in [validation.json](validation.json):

- 318/318 tests passed with the pinned Wurst compiler, including six production
  recovery journeys and the existing navigation, party-position, military and
  persistence suites.
- All 923 scenario Python tests passed.
- All 17 physical maps typechecked, compiled and passed archive inspection. The
  16 regional maps each contain four recovery movement rasters verified against
  their packaged WPM. [packaged-navigation.json](packaged-navigation.json)
  records map transforms, component counts, source identities and archive hashes.
- Original and content-mutated framework campaigns each passed 2/2 Wurst tests
  and compiled without changes to shared framework sources between builds.
- All twelve obligations, REQ-0191.01 through REQ-0202.01, passed the scoped audit
  against the exact compiled campaign and current execution transcript. There
  are 48 distinct production receipts: success, failure, replay and stale cases
  for each obligation.
- Shared-framework boundaries, both scenario world validators, traceability
  freshness and `git diff --check` passed.

The pinned toolchain was copied from the cached image into ignored worktree
storage and executed locally with its bundled JRE. No source was mounted into a
container. The declared standard library revision and compiler hash are recorded
in `validation.json`. `grill-offline.sh` preserves the wrapper used at
`_build/grill-offline`; it expects the copied toolchain and standard library beside
it in `_build`. It replaces dependency downloads with that local copy and runs
the real pinned typechecker. `packaging-driver.py` preserves the build invocation
used from the repository root; full interpreter execution ran once separately
against the same source identity. Production packaging remains the canonical
build workflow.

The compressed results and transcripts preserve the passing runs. The Python
log includes intentional negative-fixture diagnostics after its unittest `OK`
summary. Re-run `verify-scoped-evidence.py` after rebuilding to check fresh
artifact and execution evidence; its paths can be overridden with `--artifact`,
`--execution` and `--transcript`.

Nested RPG schema v3 persists the main character and migrates v1–v2. Nested
military schema v4 persists optional validated hints and migrates v1–v3. The
outer campaign schema remains v7 and party locations remain v1. Rejected records
retain existing authority and live representations.

Broader campaign publication blockers remain outside this issue's scope. The
release-blocker report only refreshes hashes of changed inputs; its findings are
unchanged. These results establish readiness for repository validation, without
claiming native-client gameplay validation. No player QA was requested, and no
commits, pushes, GitHub changes or global tooling changes were made.
