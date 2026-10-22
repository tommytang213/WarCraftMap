# PR #536 startup continuation evidence

This report retains validation of clean source `d6697380d979f96b2f3543593c6383402ba26e5b`, after integration of main `58d1b88d0fb4b852b639d2d82a5a24dee92ed92c`, starting from published `99524f6e4c356e02acc6ea7fa2f3b9a73fb62d13`. The source identity is `d08445f912a604b5fdb43beed2ec9573904075beb2e1ed6c40771df75852be37`. The source checkout is required to verify authored tests and production probe bindings.

## Source changes and required checks

The continuation rejects an empty public `session_start` or `major_milestone` encoding before writing that checkpoint or acknowledging the pending startup request. The failed attempt rolls back in-memory state and preserves the pending request for a valid retry. A milestone failure retains the valid session checkpoint already written, matching the existing non-atomic write order. The integer digit fast path returns ASCII digits directly and retains the existing fallback semantics for other input. Integration retains main's schema 17 migrations and all eight date-bound checks.

The unchanged full Wurst gate completed 698/698 tests with observed passing tests in all 28 required systems and all 84 production probes observed. The separate source/Python prefix completed with unittest counts [1137, 198]; Wurst was explicitly skipped in that prefix and synthetic fixture Wurst lines are not counted as actual Wurst execution. The focused-attempt1 original receipt remains failed because the strict transcript gate rejected the read-only setup.log diagnostic even though its 66 selected assertions passed. The negative-guard-attempt1 original receipt also remains failed. Its separate review confirms exactly the two intended guard assertions failed (0/2), while preserving the temporary harness's rejection of the compiler's normal failed-test wrapper.

The first evidence-pack attempt also **failed**, before creating an output directory: the strict path reader rejected the project's tracked `Agriculture.wurst` shared-source link. Its original reviewed helpers, review, raw rejection log, checkpoint, tracked link inventory and validation-input identities remain preserved under `evidence-review/packing-attempt1-preserved/`. The corrected source-only reader accepts only the exact 51 shared Wurst links recorded in the local `d6697380d979f96b2f3543593c6383402ba26e5b` Git tree, including the bootstrap link, and verifies their same-name canonical regular target blobs. Parent directories, evidence inputs, historical references and package traversal keep their no-link checks. No source, gate, test, model or build was changed or rerun for this packaging correction.

The second evidence-pack attempt passed that source-link check, then **failed** because its lowercase-only filename guard rejected the literal uppercase `X` in six recorded slice-model IDs. Its exact helpers, review, raw log and inventory of the incomplete 156-file staging directory are preserved under `evidence-review/packing-attempt2-preserved/`; that directory had no manifest and is not reused. The corrected guard allows only the eight exact IDs defined by the unchanged, hash-bound differential runner. All model contents, results, traversal checks and hash checks remain unchanged.

## Compiled and modeled evidence

Both compiled arms use integrated schema 17 source. The counterfactual baseline reverses only the two public empty-encode guards and the trade integer digit fast path; it is not published 99524f6 or historical schema 15 save data. Their typecheck/build logs, actual archived Lua and known extracted member bytes are retained. W3X archives remain workspace-only: two-reader known-member archive checks were performed during the original build and are not rerun by this integrity verifier.

The integer differential covers 703 cases under eight explicit slice models. The same integrated-source startup arms produce these measured values under the retained explicit native models:

| Measurement | Counterfactual baseline | Revised source |
| --- | ---: | ---: |
| Startup `SubString` calls | 10,060,261 | 9,298,589 |
| Startup `StringLength` calls | 2,042,487 | 1,527,363 |
| Sampled startup instructions | 875,150,000 | 834,300,000 |
| Modeled callbacks through 1.001 synthetic seconds | 37 | 37 |
| Sampled callback instructions | 14,710,000 | 14,710,000 |

All other startup native-call counts match, and each callback's native-call map and sampled instruction count match. The scoped review resolves one shifted compiled callback line to the identical bridge function. This is model-only work evidence; it is not a native elapsed-time measurement or a claim of Warcraft timing or behavioral parity.

All four ordered saved payloads are byte-identical between these schema 17 arms (3,203,778 uncompressed bytes per arm). The original gzip bytes for all eight payload files are retained separately. This comparison does not claim equality with historical schema 15 save bytes.

The original startup comparison **failed** its historical exact expectation of 8,422 markets. Its failed receipt, runner, outer log and all completed raw outputs remain unchanged. The separate source-derived `catalogue-cardinality.json` proves 8,422 base market pairs plus four absent industry pairs (`iron_goods` in Milan, Nuremberg, Stockholm and Vienna), giving 8,426 markets and last index 8,425. The store count stays 829. An independently reviewed, read-only derivation applies that exact current-source expectation to the already completed startup outputs; no startup model was rerun.

The original full-scale stage was never run. Its first execution used a separate, reviewed case and runner with only the exact market count/index literals and source/path bindings adapted. Native stubs, all other assertions and both 2-billion-instruction phase budgets remain unchanged. The passing full-scale revised model covers all 8,426 markets, 829 stores and 829 populated provenance lots, including mutation, reconstruction, selection and catalogue-order restoration, and exact saved/restored capture equality. All model results are supplemental developer evidence.

## Native acceptance remains open

**Native status remains `not_run`; Continue freeze resolution is not established.** The latest retained owner report, received at 2026-10-20 16:52:49 UTC, described Austria → Victory → Continue becoming unresponsive after delivery of the a1b4396 candidate. The run time was not independently verified, and the installed-file hash was not recollected. Destination terrain or a controllable unit was not observed. Keep PR #536 draft/unmerged and issue #438 open until the existing real-client acceptance and review requirements are satisfied. These artifacts are not a player release candidate.

Run the read-only verifier with the exact source checkout:

```sh
python3 -B verify-evidence.py --root /path/to/startup-main-continuation --project /path/to/WarCraftMap/maps/historical-world-rpg/age-of-sail-world --require-manifest
```

The pinned source is available at https://github.com/tommytang213/WarCraftMap/tree/d6697380d979f96b2f3543593c6383402ba26e5b. The checkout must contain that local Git tree; a source archive without its Git objects is insufficient. A later report-only commit is accepted only if the source identity remains unchanged. The source-link check uses read-only `git ls-tree` with network access and fetching disabled. The verifier does not weaken source checks for future main, execute tests or native models, rebuild maps, or contact any service.

`manifest.json` binds the exact retained file set, original and compressed hashes, logical aliases, original absolute-path aliases, and existing historical references. Identical generated/source bytes are stored once; original saved-payload gzip files are preserved separately and unchanged. Recorded absolute paths are provenance, never destinations followed by the verifier. Historical inputs already in the repository are referenced rather than duplicated in full.
