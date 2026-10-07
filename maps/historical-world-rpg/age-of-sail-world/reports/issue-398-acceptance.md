# Issue 398: execution-bound release acceptance

Runtime acceptance and the release blocker now keep four distinct evidence
levels: source readiness, headless production integration, built-artifact
verification, and real-client execution. The checked-in source-only reports
intentionally fail and cannot authorize a player candidate.

The pinned interpreter traces configured production registration and adapter
entries inside individual passing tests. Acceptance checks the transcript,
compiler identity, current test discovery, instrumented production input hashes,
source revision and source-content digest. Declaring test names or coverage does
not supply execution. Instrumentation exists only in the disposable assembly
and is restored before map compilation. Grill's normalized `wurst.build` has its
own recorded interpreter-input hash; the authored configuration remains covered
by the source identity.

Every packaged map carries that source identity. The artifact verifier opens the
exact W3N and nested W3X payloads, checks campaign metadata and map contents, and
records their exact hashes. Candidate packaging and the copied-ZIP upload gate
recompute acceptance from the transcript and extracted campaign. Missing,
unexecuted, stale, malformed or failing evidence, including a required false
`releaseValidated` flag, blocks publication.

Aggregation also rejects omitted, exempted or duplicate required systems and
missing evidence digests. Artifact inspection cannot pass without an explicit
source revision and source-content digest. Malformed source and publication
metadata produces gate diagnostics instead of object-type exceptions.
Source-system flags must be booleans. Malformed real-client configuration,
built-map metadata, and candidate configuration are rejected explicitly,
including scalar JSON values that previously reached dictionary `.get` calls.

## Initial implementation verification

- `WARCRAFTMAP_WURST_CHECK=skip bash automation/run_checks.sh` passed the world,
  geography and map-source validators, all 842 scenario/tooling tests and all 70
  automation tests. Wurst validation ran separately in the pinned container below.
- The final pinned compiler run passed typechecking, all 271 Wurst tests and the
  standalone map build. Revalidation against this worktree passed. The built map
  retained the matching source identity and contained no instrumentation markers.
- Source revision: `b079918788f8e1045486e9c5cadd6faa7ace2190`.
- Source-content SHA-256:
  `a9221a46aaa0a49ed26b8eb19c739372293dd8d12327d15d64a64fc727151cba`.
- The 12-test integration-evidence regression suite passed, including
  source-only, missing, stale, unexecuted, malformed and declared-only evidence,
  invalid validation flags, transcript boundaries and compiler normalization.
- All 23 runtime/artifact, 9 release-blocker, 13 upload and 15 execution-protocol
  regressions passed against the final source, including three additional
  malformed-metadata regressions added after the complete suite started.
  The fresh retained transcript also produced a blocked runtime acceptance and
  release-blocker result, as expected. The prior attempt's real transcript was
  rejected as stale despite sharing the same Git revision.

Logs and retained evidence are generated under
`_build/issue-398-validation/`, including `resume-results.json`,
`resume-execution.log`, `resume-runtime-acceptance.json` and
`resume-release-blocker.json`. The complete repository log is
`resume-repository-checks.log`; compiler/build output is `resume-pinned-wurst.log`.
`resume-validation.json` records the final verification summary.
Container validation mounted this worktree
read-only and performed all build writes in container-private temporary storage.

## Initial remaining release evidence

The executed suite supplies complete configured entry coverage for 12 of 20
required systems. Administration, army/fleet control, city capture, country
diplomacy, garrisons, government rewards, origin selection and save/autosave/load
still lack complete coverage within a passing production-path test. They remain
blockers even though the general Wurst suite passes.

No full built campaign was supplied to this run's acceptance report. W3N/W3X
verification has automated binary-fixture regression coverage, but that does not
constitute verification of a releasable campaign. Warcraft III, native saves and
the declared client journeys were not executed. Their status remains explicit;
no player candidate was published.

## PR 405 CI repair

The failed campaign build ran all 278 Wurst tests successfully, then correctly
rejected the candidate because eight systems lacked complete production-entry
coverage in a passing test. The acceptance gate remains fail closed.

The added command integration tests exercise origin selection through its durable
handoff and regional startup, manual save/load through registered commands, and
the timed autosave adapter. Country and reward commands now verify discovery,
standing, resource debit, duplicate rejection and restored grant history using
the production authority. Military tests dispatch the registered management
commands and assert the state they display after orders, garrison expenditure,
appointments, and capture through the production combat-event adapter.

The coverage contract additionally requires command dispatch for origin,
military and save integration, and the autosave scheduler for save integration.
Source-only checked-in acceptance reports remain blocked; executable evidence
and exact same-source campaign artifacts must still be supplied for a candidate.

The repaired pinned run passed typechecking, all 273 tests in this isolated
worktree, and the standalone map build. Rechecking the retained transcript
against the current worktree confirms production coverage for all 20 required
systems. The generated map embeds the matching source identity and contains no
instrumentation probes. The save-command fixture supplies the native game-start
timer that Blizzard initializes in the client but the interpreter leaves unset.

`WARCRAFTMAP_WURST_CHECK=skip bash automation/run_checks.sh` also passed the world,
geography and map-source validators, all 845 scenario/tooling tests (including
the fail-closed acceptance/publication regressions), and all 70 automation tests.
The skip flag separates that repository run from the completed pinned Wurst
typecheck/execution/build above; it does not waive Wurst validation. Its log is
`_build/issue-398-validation/repository-checks.log`.

This execution used source revision
`ec5a9cdc29f464df90520d21201127d733ef0272` plus source-content SHA-256
`e078e537affd693e9223a171e35214b36cc8ad3bed8a0cf48e010391227ef691`, binding the
uncommitted repair as well as the base revision. Retained evidence is under
`_build/issue-398-validation/pinned-evidence/`; `validation-summary.json` records
the revalidation against this worktree. The container mounted source read-only,
copied it as the build user to private temporary storage, and was removed after
its results were retained.

No full W3N/ZIP was rebuilt in this repair, and Warcraft III was not executed.
Acceptance and the release blocker both correctly remain blocked when the new
passing transcript is supplied without a matching campaign artifact. Full
campaign packaging and upload verification remain CI checks, and the real-client
journeys and native saves remain a separate unexecuted evidence level.
