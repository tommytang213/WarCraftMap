# Issue 526 focused verification

Chartered Companies now unlocks independently paid commercial courts and Armed
Indiaman construction. The policy contract is in `docs/COMMERCIAL_COURTS.md`.
Military snapshots advance to v19 with inactive migration from versions 1–18;
other save envelopes retain their versions. The release compatibility manifest
advertises the complete updated range.

The pinned Wurst compiler typechecks the assembled source and runs **61 selected
real interpreter cases**: CharteredCompaniesTests, NavalServicesTests,
BankingOperationsTests, TradeFinanceTests, PlayableTradeTests, MixedCargoTests,
ResearchCostTests and FrameworkConformanceTests. `focused-results.json` lists each
case and its observed production probes; `focused-wurst.log.gz` and
`focused-inputs.json.gz` preserve the transcript and exact assembly hashes.
The compiler JAR SHA-256 is
`1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.

The eight chartered cases exercise registered research, policy and construction
commands; separate permissions; complete resource bills and conservation;
research/date/port/shipyard/manpower/supply/counter gates; denied court activation;
missing stock or funds; stale terms and stock quotes, foreign commits and replay;
real buy/sell counterparty constraints; duplicate trade IDs; construction reload;
capture; malformed/legacy saves; actual paid court/dock state after a late failed
campaign load; source replacement; 25-year active/abstract parity; unfunded upkeep;
and the construction serial limit. No exchange research or battlefleet entitlement
is completed or required by the chartered fixture.

**95 distinct Python cases passed** across a 75-case focused integration run and
a 26-case research/save-contract run (six chartered compiler/evidence cases are
shared). The retained Python logs include synthetic framework compiler results;
those printed batches are orchestration fixtures, not additional real interpreter
execution. The Python suites cover roster, naval, trade, banking, research,
release compatibility, campaign save stress and framework assembly/conformance.

`generated-identities.json` records both exact identities and their generated
runtime contracts. `audits.json` identifies fresh release, runtime and requirement
traceability source audits. They fail closed because focused transcripts and
unbuilt archives cannot establish full release acceptance or blocker closure.
The controller must integrate the reserved staging slot, run complete repository
validation, inspect shipping archives and regenerate official audits on new main.
No unmerged predecessor was merged and no predecessor CI/artifact was reused.

`prepare-focused.py PATH_TO_CACHED_WURST_STDLIB` reproduces the assembly using the
normal generator and packaging assembly, disabling only unselected test
annotations in its disposable copy. `collect-focused.py TRANSCRIPT` records real
results; `regenerate-audits.py` regenerates source-only audit artifacts. Validation
used the cached pinned image with network disabled and a read-only assembly
mount. UID/GID 1001 copied it into container-private `/tmp` before compiler writes.
No container wrote to the worktree. No commit, push, PR/issue mutation, global
installation or player QA was performed.
