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

## Executed verification

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

## Remaining release evidence

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
