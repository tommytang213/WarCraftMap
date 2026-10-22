# Issue 524 implementation verification

The implementation is ready for controller integration preflight and repository
validation. No commit, push, issue/PR mutation or player QA was performed.

- Pinned Wurst typecheck and **20/20 real interpreter tests passed**. The compiler
  JAR SHA-256 is `1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.
  The selected packages are BankingOperationsTests, TradeFinanceTests,
  ResearchCostTests and FrameworkConformanceTests. `focused-results.json` records
  exact cases and observed production probes; the raw transcript and input
  hashes are retained in `focused-wurst.log.gz` and `focused-inputs.json.gz`.
- **95 Python cases passed** across integration/research/economy/save (68),
  release-save compatibility (6), and framework/packaging (21). The integration
  run includes multi-century economy invariants and campaign checkpoint stress.
  Framework/packaging tests use synthetic compilers to check assembly, metadata,
  provenance and rejection paths. Their printed 656-test fixture summaries are
  synthetic orchestration data, not additional real Wurst execution evidence.
- `release-audit.json.gz`, `runtime-audit.json.gz` and
  `traceability-audit.json.gz` were freshly regenerated for the source identity
  in `audits.json`. They fail closed because full-suite integration and packaged
  campaign evidence are intentionally left to the controller. They are not
  blocker-closure claims. No predecessor execution artifacts were reused.

The five banking interpreter cases execute registered research/adoption, policy
activation and actual treasury lodgements with neither/either/both entitlements,
rounding, conservation, denied actors, missing infrastructure/bookkeeping,
insufficient funds, quote revalidation, replay after reload, capture, migration,
late failed-load rollback, provenance repair and 25-year active/abstract upkeep.
The fixture registers no exchange/remittance research consumer. The separate
TradeFinance cases verify coexistence with that already-present implementation.

`prepare-focused.py PATH_TO_CACHED_WURST_STDLIB_SOURCE` reproduces the focused
assembly under `_build/issue-524`. It uses the normal generator and assembly,
then removes only unselected test annotations in that disposable copy. Validation
used the pinned image
`frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`
with `--network none` and a read-only bind mount of the assembly to `/source`.
The image's default user (UID/GID 1001) copied `/source` into its private
`/tmp/banking-validation` before all compiler writes. No container wrote into the
worktree or changed its ownership or permissions. Cached upstream standard
library source was used only as a compiler dependency.

After integration/merge, the controller must run complete repository validation
and regenerate the official release-blocker, runtime-acceptance and requirement-
traceability audits on the new main revision. The custom focused-results format
cannot satisfy the full-suite release evidence gate.
