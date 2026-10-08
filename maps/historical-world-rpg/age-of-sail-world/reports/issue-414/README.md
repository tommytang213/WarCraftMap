# Issue #414 validation

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
