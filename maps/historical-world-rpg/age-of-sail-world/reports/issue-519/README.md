# Issue #519 focused development evidence

The resumed validation repair is recorded in `clock-repair-verification.json`
and the `clock-repair-*` inputs and transcripts. The reported capture failure
was an inlined dereference of the uninstalled native-map campaign-clock
singleton. Military capture, garrison events, default force transfers and
capture project deadlines now prefer the owning campaign's transactionally
restored clock. Detached runtimes retain their legacy clock fallback. No save
schema or logistics balance changes are needed.

Fresh pinned typechecking and all **131 selected Wurst tests pass**, including
every logistics, finance, land-army, industry, startup, campaign-load, military
settlement and remote-region authority case. The previously failing capture
case passes. A new regression covers capture and transfer without the native
singleton, then capture and garrison losses with an unrelated global clock.
The complete logistics production probes are present in the interpreter log.

All **185 distinct selected Python tests pass** after refreshing source reports:
176 gameplay/generation/save/audit/packaging/execution cases and nine reusable
framework cases. The initial run's two stale runtime/release report assertions
are retained in its transcript; all 35 tests in those suites pass in the final
rerun. Synthetic packaging fixtures deliberately print passing and failed
compiler totals; those are protocol tests, not real Wurst execution evidence.
Generation/provenance verification, canonical map source, framework boundary,
report freshness and whitespace checks pass. Source reports retain the exact
two logistics release findings until the outer worker supplies complete
same-revision validation. Native campaign launch #438 remains separate.

The fresh assembly and cached standard library were mounted read-only into the
pinned compiler container with networking disabled. All compilation ran in
container-private `/tmp`; the worktree was not mounted. The compressed prepare
and run scripts, selected discovery, exact source hashes and transcripts allow
review of the focused result. No commits, GitHub writes, tooling installation,
container ownership changes or player QA were performed.

PR #542 CI repair is recorded in `ci-repair-verification.json` and the
`ci-repair-*` inputs and transcripts. The failed job is linked in `ci-failure.txt`:
its single seven-schema military migration test exceeded the pinned interpreter's
20-second per-test deadline. Each schema now has an independent test calling the
same complete migration journey. All original load, XP, order, consumed-loss,
save round-trip, replay and invalid-input assertions remain. A discovery test
requires all seven schema cases; the compiler deadline is unchanged.

Fresh pinned typechecking and all **45 selected Wurst tests pass**, including the
seven migration schemas, all seven logistics cases, finance, land-army and
industry tests. The food/freight comparisons emit their real production probes.
All **163 Python tests pass**: logistics (9), finance (7), compiler execution and
release gating (23), related gameplay/save/audit regressions (115), and reusable
framework conformance (9). The Python packaging tests use synthetic compiler
fixtures; their printed 664-test totals are not real Wurst execution evidence.
Current-source generation/provenance verification, canonical map-source and
framework-boundary checks pass. Runtime, release and traceability source reports
are refreshed with the same outstanding blockers. This focused repair evidence
does not replace the outer worker's complete repository, packaging and
same-revision release validation. Both exact logistics findings and native launch
#438 remain blocking pending their required evidence.

The merge integration repair is recorded separately in
`integration-verification.json` and the `integration-*` transcripts. It preserves
both #519 logistics and main's #518 industry consumers. Military snapshot v17
requires the combined industry, finance and daily freight state, accepts both
independent v16 layouts, and initializes absent legacy domains unfunded. The
runtime manifest and source reports describe the combined revision. All six
conflicted paths are resolved and staged; no commit was created.

Fresh pinned execution passes all 76 selected Wurst tests, including all logistics
and industry cases, capture, travel, save rollback, both v16 migrations and missing
v17 ledger rejection. Both consumers' production probes are present. The initial
Python run imported the old v16 runtime assertion; after correcting the manifest,
all 35 runtime/release audit regressions were rerun on stable final sources.
The original failed transcript is retained alongside the passing repair run.
Source report freshness and framework boundary checks pass. These are focused
development results; full repository validation and authoritative release evidence
remain the controller's responsibility. Both exact logistics release findings and
native launch #438 remain blocking.

The evidence below documents the original implementation before this merge repair.

Both approved logistics consumers are implemented on the merged #511 design.
The work starts at `c1b78cd` and uses no unmerged predecessor code or CI artifacts.
`validation.json` identifies the exact uncommitted source tree and compiler inputs.

Passing checks:

- **69 pinned Wurst tests**, including all seven army-food/canal-freight cases,
  the finance and land supply suites, populated campaign-load rollback, and the
  existing regressions changed by military snapshot v16. The compiler also
  typechecks all assembled production and test source. The integrated logistics
  test hits all five logistics/construction production probes.
- **145 Python tests**: logistics compiler/geometry/evidence (9), research
  generation and all generated depot approaches (10), finance (7), land army (5),
  release save compatibility (6), runtime acceptance (24), release-blocker audit
  (10), requirement traceability (53), packaging (12) and reusable framework (9).
  Packaging/framework tests use synthetic compiler fixtures for their archive
  and validation protocols; their printed interpreter totals are **not** real
  compiled-map execution evidence.
- Current-source generation/provenance verification, framework boundary audit,
  and whitespace validation pass. Runtime/release/traceability source reports
  are refreshed while preserving the existing execution/artifact blockers.

Production comparisons deliver **77 versus 75** army supply from exactly 100
real grain, and move **110 versus 100** stock units per canal day after paid
construction. Tests exercise research and registered actions; missing resources,
control, title, gear, era and infrastructure; disconnected land; source dedup and
layer repair; repeated loads; capture; active/inactive travel; migration from v15;
late campaign-load rollback; and 50 years of stock, supply and treasury conservation.

Generation binds **423** depot approaches to materialized physical market
locations and packaged land components. Four warehouses (Hohhot, Karakorum,
Pskov, Thessaloniki) have no traversable approach within the scenario's 512-unit
service radius and remain ineligible. Canal freight follows only the authored
Yangzhou–Zhenjiang waterway and its completed paid quay; both directions and all
commodities share durable daily usage.

The pinned compiler is
`frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`;
its JAR hash is recorded and verified in the transcript. All inputs are mounted
read-only. Compilation runs in container-private `/tmp`; the worktree is never
mounted writable or subjected to container ownership/permission changes. The
cached standard-library source is a dependency, not predecessor execution evidence.
Only unrelated `@test` annotations are removed in the disposable focused copy;
production is instrumented using the repository's `integration_evidence` probes.
The expected selection, exact compiler input hashes, generated provenance and
compressed transcripts are retained alongside the machine summary.

Reproduce Python selections from the scenario directory with
`python3 -m unittest discover -s tests -p PATTERN`, using the ten corresponding
`test_*.py` files named above. The normal complete interpreter command remains
`python3 ../_shared/tooling/run_wurst_tests.py package.json`.

Complete repository validation and fresh integrated current-main execution,
runtime/traceability and release evidence belong to the controller. These focused
results do not clear either exact research-unbound release finding. Native
campaign launch #438 remains separately owned. No commits, GitHub writes, global
tooling changes, service installations or player QA were performed.
