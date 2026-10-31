Issue #586 implements paid mineral-fuel refining and its exact Coke-smelted Iron
consumer. Scenario authority defines separate coal extraction at evidenced Bristol,
100-coal → 50-coke preparation, transportable commodities, and compatible mineral
refineries at the existing iron-producing, market/warehouse-equipped settlements.
No opening fuel, liquidity, facility, research, or raw iron is granted.

The mineral retrofit costs 120 treasury minor units, 10 tools, 20 timber, 10 assigned
workers and 90 days. Batches reserve 200 ore/feedstock iron, 50 coke, two tools and
20 treasury, then pay ten daily treasury/supply bills. Registered isolated research
produces 106 versus 100 iron_goods; independent Blast Furnace Practice gives 107,
and both give 113. Recovery is capped by consumed feedstock. Charcoal and barrel
production retain their own recipes. Industry and research views expose bills,
conditions and yields, including upstream fuel preparation.

Military v24 adds complete stable-ID I records for new facilities, paid setup,
batch work, fractional recovery and consumed geological reserves. Existing i
records remain compatible; v1–v22 and council/navigation v23 initialize new
facilities uncommissioned. Mineral-only v23 preserves its industrial records
and migrates absent councils inactive. Capture
retains completed infrastructure while rechecking successor authority and research.
The headless ledger advances its own schema to v2 with a v1 migration. Trade's
existing stable commodity/cargo codec needs no new schema. The release compatibility
manifest advertises all military source versions through v24.

Focused developer validation passed:

- Pinned Wurst image `frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`:
  all production sources typechecked; 13/13 Industry tests passed. Other test
  annotations were removed only in a temporary assembly. Source was mounted
  read-only and copied into container-private /tmp as wurstuser. The interpreter's
  normal per-test deadline was unchanged.
- Industry/headless/generation tests: 29 passed, including 200 combined batches,
  fractional resume, depletion, resource rejection and opening-stock safeguards.
- Coke binding evidence protocol tests: 6 passed.
- Research generation, design and cost tests: 15 passed.
- Global goods tests: 4 passed.
- Release save compatibility tests: 6 passed.
- Shared framework boundary audit and `git diff --check`: passed.

The compressed logs are focused development results, not full-suite production
closure evidence. The coke verifier requires its own registered comparison and
upstream production probes, complete current-source pinned execution and passing
lifecycle/negative/rollback tests; sibling industry execution cannot close it.

Per the controller handoff, complete repository validation is deferred until
integration preflight. After merge, regenerate release-blocker, runtime-acceptance
and requirement-traceability audits on the new main revision. The release finding
remains accountable until that revision supplies verified production evidence and
the fresh audit omits this exact identity. No player QA was requested. No commits,
GitHub writes, predecessor merges, or predecessor artifacts were used.

Integration repair resolved both reported conflict paths while retaining main's
council/navigation loader and this issue's mineral-industry loader. Both branches
used v23 independently, so the combined writer now emits v24. Council/navigation
v23 preserves council and navigation state and migrates mineral facilities
uncommissioned; mineral-only v23 preserves paid industrial work and migrates
absent councils inactive. Current v24 rejects missing records in either domain.
The Industry save regression executes both migrations and verifies conserved
trade accounts, retained council revenue, retained mineral work and atomic failure.

Fresh integration validation: **95/95 focused pinned Wurst tests passed**, with
all production sources typechecked. The selected suites cover Industry, councils,
civic governance, coastal/celestial navigation, science, framework production
contracts and late revenue rollback. **71 Python tests passed** across industry,
Coke/headless conservation, exact evidence, save compatibility, local revenue,
research generation, goods and coastal navigation. Generation/verification and
the shared boundary audit passed. See `integration-repair.json` and its compressed
logs. These focused results do not replace the controller's complete validation
or fresh main-revision closure audits.

The subsequent validation repair updates the technology runtime manifest's
industrial yield evidence from the old metric-only `rateAt` call to the actual
fuel-compatible `rateFor` call. This removes the spurious static-readiness failure
without changing production or relaxing the executable evidence gate. All three
source-only audits were regenerated at integrated revision
`8a120d5422bbba33c09e0f3613dcdebace6074e2`; their publication blockers remain
explicit pending complete controller execution and artifact validation.

Fresh Python checks passed: Coke discovery (19 tests, including imported Industry
generation cases), Industry (16), runtime acceptance (25), requirement traceability
(54), release-save compatibility (6), and release-blocker audit (10). The shared
framework boundary audit and `git diff --check` passed. The `retry-*.log.gz` files
record this repair's checks. Production Wurst code is unchanged by this repair;
complete pinned Wurst and repository validation remain controller-owned. No
predecessor artifacts were used to establish evidence for this source tree.

The recovery validation repair reproduces the reported
`liveRecoveryMigratesLegacyHintsAndRejectsMalformedRecords` failure in isolation.
Its synthesized v3 fixture retained the new `I` records, which the production
loader correctly rejects in that schema. The fixture now removes those records
before legacy restoration, verifies atomic rejection while they are present,
and checks that migration grants no retrofit, active work, fractional yield or
extracted fuel. Production code and loader validation are unchanged.

Fresh focused validation passed **32/32 pinned Wurst tests** across Industry,
live recovery and military persistence, with all production sources typechecked.
The isolated original test failed before the repair. Python Coke/evidence,
Industry, release-save and recovery checks passed **43 test executions** (including
Industry generation cases imported into Coke discovery). The shared framework
boundary audit and `git diff --check` passed. See
`recovery-validation-repair.json` and `recovery-repair-*.log.gz`. Source mounts
were read-only; the pinned container built in private `/tmp` as `wurstuser`.
These are focused development results. Complete repository validation and fresh
integrated-main closure audits remain assigned to the controller.

The subsequent report-freshness repair preserves the integrated implementation
and recovery fixture. The controller's complete Python run reported only two
failures: release-blocker and runtime-acceptance snapshots still hashed the sources
before the recovery repair. All three source-only audits have now been regenerated
at `ec4776dd74ced62d7bdce8096fffe58442bfaf73`, with source hash
`218ced8288766d261a27830533b44547bdfca1243775a49afb71bf4d43018409`.
The runtime and release reports change only their recorded identity; traceability
changes only its revision. Human report content and publication findings are
unchanged. In particular, source-only regeneration does not claim Coke closure.
Complete pinned execution, repository validation and post-merge closure audits
remain controller-owned.

Fresh focused validation passed **124 tests** across Coke/evidence (19, including
imported Industry generation cases), Industry (16), runtime acceptance (25),
release-blocker audit (10), and requirement traceability (54). Both reported
freshness regressions also passed in a separate two-test rerun. The framework
boundary audit and `git diff --check` passed. See `audit-freshness-repair.json`
and `audit-freshness-*.log.gz`. This repair changes only audit/report outputs;
production sources, tests and evidence gates remain intact.

The combat validation repair reproduces all four reported failures in isolation
(0/4 passing before repair). Their synthesized v6/v8 snapshots retained mineral
`I` records absent from those schemas. The fixtures now verify atomic rejection
of those mislabeled current records, remove the mineral records, then exercise
the intended combat migration. Each migration also verifies that mineral
equipment, setup completion, active work, fractional recovery and extraction
remain absent. Production behavior and loader validation are unchanged.

Fresh focused validation passed **89/89 pinned Wurst tests** across the complete
combat, Industry, live-recovery and military-persistence test files, with all
production sources typechecked. The standard transcript parser verified every
discovered focused test and the passing summary. **49 Python test executions**
passed across Coke/evidence, Industry, release-save compatibility, live military
tradition and both audit-freshness regressions. Generation/verification, the
framework boundary audit and `git diff --check` passed. All three source-only
audits were refreshed at `e4a72c459d416aff1a079aa7f7636c555fb0c8cd`; their
publication findings remain explicit. See `combat-validation-repair.json` and
`combat-repair-*.log.gz` for this worktree's results. Builds used read-only mounts
and container-private temporary storage as `wurstuser`, without network access.
Complete repository validation and fresh post-merge closure audits remain
controller-owned; these focused results do not establish blocker closure.
