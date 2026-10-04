# Issue 363: Wurst execution repairs and release gate

Base revision: `7ba80ff629279e1ab2f9b7fcec21e57931f20e3b`. The implementation
is an uncommitted worktree change. The retained execution JSON hashes every
compiled Wurst source, generated scenario, compiler options, core JASS and
installed Wurst dependency source. Its input-set digest identifies the tested
worktree contents independently of the base revision. Every current authored
Wurst file was compared with that manifest after execution.

The baseline independently reproduced **64/73 passing, nine failing**. The
implementation executes **78/78 passing** with no unresolved assertions,
interpreter errors, timeouts or missing results. All original tests remain;
five additional tests cover restoration, trade rollback and minimal/generated
RPG records. Both runs used read-only worktree mounts and container-private
source/build copies. No player testing or World Editor work was required.

## Retained evidence

- [Baseline per-test results](issue-363/baseline.json) and
  [raw transcript](issue-363/baseline.log). These are archived historical
  failures, not a current release validation result.
- [Implementation per-test results](issue-363/execution.json) and
  [raw transcript](issue-363/execution.log), produced by the same execution gate
  used in the artifact path. Input-set SHA-256:
  `3499ab09197cbef167153d7014dd8bf109865a74e9500d273396d4bbb4cf1244`.
- Compiler image:
  `frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`.
  Grill `1.4.0.0-2c676dd`; Wurst `1.9.0.0-nightly-1-gedd2e5e74`;
  compiler JAR SHA-256
  `1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.
  The runner verifies this compiler digest, including for local Grill usage.

A fresh verification run through `run_wurst_tests.py` reproduced the retained
78/78 results. Its JSON and raw transcript are byte-for-byte identical to the
linked implementation evidence, including the complete compiler-input manifest.
The baseline's authored Wurst hashes also match the base revision above.

## Failure classification and repairs

| Baseline test | Classification and repair |
| --- | --- |
| `pendingOffersAndRewardHistorySurviveReconstruction` | Production defect: conflict restoration required pre-existing registry entries; later offer failures could also partially mutate authority. Parse and validate a disposable candidate, then commit all country state together. Recover the next player offer ID from retained offer history. |
| `remoteAccessDoesNotRevealUnknownOrMovePhysicalRegion` | Interpreter/test boundary: `PauseGame` is unsupported. Inject the existing pause controller into region selection; production defaults still use the Warcraft pause service. The test verifies pause acquisition/release and discovery through the real selector. |
| `playerCanInspectBuyCarryMoveAndSellCargo` | Outdated fixture: commit-time pricing applies the 920-permille sell spread. A buy cost of 100 and sale proceeds of 270 yield profit 170 and standing 340 at difficulty 2000. |
| `staleDisplayRestrictionsAndFailuresRollbackAtomically` | Outdated fixture changed cached UI price instead of authority. Change shortage by 200 permille to obtain an independently calculated commit price of 12. Rejection coverage also exposed price/history mutation before validation; calculate quotes without mutation and update observations only at commit. |
| `bootstrapRegistrationOpeningOverviewAndBenefitExplanation` | Presentation boundary: registration ignored the registry's output. Registered overview, alias and conversion commands now use that output; recording tests dispatch those actual commands. |
| `equipmentRequirementsComparisonUniquenessAndSets` | Production defect: unset optional equipment strings reached `StringLength(null)`. Use explicit empty requirements/set/source defaults. |
| `questTreasureTechnologyAndReconstruction` | Production defect: an unset technology prerequisite rejected otherwise eligible research. Give optional technology strings valid empty defaults. |
| `authoritativeStateRoundTripsAndReconcilesExactlyOnce` | Production defect: the same optional equipment strings prevented snapshot exercises. Restored equipment, sets, guidance and treasure knowledge now reconcile repeatedly. |
| `playerReachableActionsWorldEventsAndRepeatLock` | Production defects: equipment defaults first raised a null-string exception; after that repair, acquiring a second ordinary item made the writer's own save fail duplicate validation. Permit ordinary inventory copies while retaining unique-item and all other authority uniqueness checks. Quest optional locations default to empty and precision to `hidden`, matching generation. |

The new generated-catalogue test exposed a 20-second interpreter timeout in
snapshot validation. A temporary record-key index replaces repeated reparsing
of the entire snapshot for each duplicate check. The full generated catalogue
now executes equipment, research, quest and treasure actions and two complete
save restorations/reconciliations within the interpreter's existing limit.
No timeout limit or exception handling was relaxed.

Expanded trade persistence coverage also exposed summary cargo being copied
into the previously selected store before resolving the saved store ID.
Resolve the saved market/store first. A newly configured warehouse stays empty;
cost basis, transaction history, standing and price modifiers persist, and
repeated reconstruction is stable. Duplicate transactions, restricted markets,
uncosted cargo and same-market standing restrictions remain covered.

Country coverage includes fresh and existing registries, repeated restoration,
reward history, pending responses, continued offer creation, sparse offer IDs,
late-invalid references, duplicate records, invalid integers/statuses/schema,
trailing records and capacity overflow. Rejection preserves live authority and
offer sequencing. Country v1, RPG v2 and campaign save formats are unchanged;
legacy country rows without material stock retain the existing compatibility
behavior. No persisted-format migration is required.

## Required execution gate

`_shared/tooling/run_wurst_tests.py` uses the release generator and assembler.
`wurst_execution.py` independently discovers source tests, requires individual
terminal results plus matching summary/completion, checks the compiler digest,
and writes a transcript and revision/input-linked JSON even on execution failure.
Assertion failures, interpreter exceptions, missing tools, incomplete output,
duplicate/unexpected results and zero discovery fail closed, including when
the command exits zero.

Map packaging executes the suite before archive assembly. Campaign packaging
executes the complete generated scenario before compiling localized physical
maps. Test-only packages are omitted from those later physical-map compilation
copies to preserve the minimal selector's dependency graph; their coverage was
already executed in full. Repository checks and the Wurst workflow call the
same gated map packager. Docker source mounts remain read-only and the mutable
`latest` image/compiler-install path has been removed from repository checks.

Verification exposed a container-user mismatch in the repository-check path:
Grill running as root looked for the compiler under `/root/.wurst` and reported
it absent. The Docker branch now runs compilation as the image's `wurstuser`,
matching CI and using its installed pinned compiler. Ownership changes apply
only to the container-private source copy. Shell regressions exercise the actual
required-check script's Docker arguments, missing tools, and propagation of a
compiler failure after otherwise successful Python checks.

The RC packager retains `Metadata/wurst-execution.json` and
`Metadata/wurst-execution.log` in its ZIP. The copied-artifact verifier rechecks
their revision, compiler, input/log hashes and complete individual results
before upload. Runner, packager and upload regressions exercise assertion,
interpreter, absent-tool, missing-execution, incomplete-output and zero-test
failures even with otherwise successful typechecking or checksummed packaging.

## Automated verification

- World-contract, Europe-geography and canonical map-source validation passed.
- Scenario Python discovery passed **790 tests**; automation discovery passed
  **67 tests**. These include packaging, workflow, save-compatibility, migration
  and runner regressions. This local Python pass used
  `WARCRAFTMAP_WURST_CHECK=skip bash automation/run_checks.sh`; real compiler
  validation ran separately through the repaired pinned Docker branch.
- The copied-artifact failure matrix is part of the **10-test** upload verifier
  module, included in the complete discovery above. It verifies that no upload
  evidence is produced for the required failure modes with otherwise valid packaging.
- The retained full pinned `package_release_candidate.sh --source-revision
  7ba80ff629279e1ab2f9b7fcec21e57931f20e3b` run exited **0**. Both complete
  Wurst executions passed **78/78**. Both campaign builds typechecked, compiled
  and structurally inspected all **17 physical maps**; normalized campaign
  contents matched, and the resulting RC ZIP passed final inspection including
  the packaged execution evidence. This was a local validation artifact in
  container-private storage, not a GitHub upload or native launch.
- The repaired Docker branch from `automation/run_checks.sh` ran separately
  against the current worktree and exited **0**: **78/78 Wurst tests**, typecheck
  and map packaging passed. Its [output](issue-363/repository-validation.log)
  is retained. The three new shell regressions, six workflow checks and eight
  runner/packager regressions also passed individually.
- [Validation summary](issue-363/validation.json) retains command outcomes;
  [release validation output](issue-363/release-validation.log) retains the
  container output (the duplicate inline execution envelope is stored separately
  in the execution JSON/transcript above).
- Changed Python sources parse, shell syntax checks pass, and `git diff --check`
  passes.

## Native-client boundary

The native-save reconstruction oracle passed. Actual native Warcraft execution
reported `runtime_unavailable` because `WC3_NATIVE_SAVE_RUNNER` is unset.
No Warcraft launch, gameplay or native-save success is claimed.

Release status remains **`blocked_pending_real_forsaken_kingdom_launch_smoke`**.
Interpreter execution and automated packaging do not resolve that separate gate.
