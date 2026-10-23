# Issue #551: Auction Markets evidence and commit authority

## Why the finding persists

`release_blocker_audit._audit_research_bindings` already calls
`trade_finance.verified_bindings`. There is no missing entitlement allowlist.
The verifier first calls `integration_evidence.verify_execution_coverage`, which
requires complete test discovery, completed passing execution, the pinned compiler,
matching revision and source-tree identity, transcript/input hashes and actual
instrumented production calls. It then requires all nine original finance cases
and the original exchange, bank and canal probes. Missing any of those returns
no finance bindings.

The report stored at closure revision
`14efef5af129e63021337761b6cc252a24589ddf` declares
`runtimeIntegration.executionStatus = not_run`, with
`required executable production-path evidence is missing`. Its own recorded source
revision is `b52008951a0e954c909e9b8c122c2c12e7504443`. The retained #517 repair
manifest explicitly describes ten focused finance tests and
`releaseEvidence: false`; it cannot meet full discovery or current-source identity.
The source-only audit invokes the verifier without execution/log/revision inputs,
so it returns an empty set before even selecting the finance tests. That is the
precise recognition failure. The audit's generic “no gameplay consumer” text does
not establish that the consumer implementation is absent. Historical files were
inspected to diagnose this failure, never reused as validation of this change.

## Production path and repairs

Generated RPG registration supplies `auction_markets`, its
`consular_trade_networks` prerequisite and the typed
`modifier:progression_auction_markets` unlock. Registered `/research` dispatch
uses `TechnologyRuntime.unlock` to record controller-specific earned authority
and rebuild the named entitlement layer. Generated finance registration supplies
the approved 500-bp commission effect, its 1580 activity gate, the 5000-bp share
of existing spread and actual formal-exchange sites. `CampaignRegistration` wires
this effect chain and `FinanceCampaignRuntime` into the existing trade controller.

Registered `/trade select` and `/trade store` establish physical selection.
`PlayableTradeRuntime.exchange` rechecks current actor presence, market/store
control and access, and resolves the current research controller. Both controller
`buy` and `sell` call `FinanceCampaignRuntime.amount` at commit. Successful
validation enters the private `settlePurchase` or `settleSale` boundary, which
changes the existing stock, currency, cargo, provenance and processed-transaction
history. New probes observe those successful settlement boundaries; shipping
source contains no probe prints.

Two defects were demonstrated:

* A generated site alone continued to authorize discounted quotes after its live
  warehouse service disappeared. Eligibility now checks the registered current
  market and the existing warehouse's service and settlement binding, as well as
  current lawful control, administration, discovery, access and save lifecycle.
* A restored research snapshot without Auction Markets left the previous cached
  entitlement layer in place until reconciliation. A purchase after that preview
  paid 10780 instead of the correct 10800. Quotes and commits now resolve typed
  entitlements from current earned `TechnologyRuntime` authority, using the same
  era and named-source deduplication calculation, without changing cached layers.
  The test deliberately restores authority without manually repairing the cache.

No pricing formula, commission coefficient, sibling coefficient, starting resource,
startup path, dispatch action, persistent field or save schema changed. The
settlement extraction preserves the existing validation and mutation order.

## Exact outcomes and evidence gates

The Auction-only registered matched control uses a 10000 principal and 800
existing spread: 400 commission plus 400 slippage. Purchase debit changes from
10800 to 10780; sale proceeds change from 9200 to 9220. Stock, cargo and combined
market/store currency are conserved on both commits. No brokerage research is
present. The same-market cycle awards no route standing. AI/abstract execution
uses the same amount and transaction methods.

The existing currency-domain rule remains: allocate commission from the settled
spread, floor its 500-bp saving once for the whole order, retain a positive minimum
on every nonzero cost, and keep the existing buy-ceiling/sell-floor pricing rules.
At base price 50 a single unit still costs 54 and sells for 46; ten units settle
for 539 and 461. Ten independently rounded one-unit rebates would incorrectly
save zero. No principal or slippage discount, new fee, currency minting, stock-price
change or alternate cargo authority is introduced.

`verified_bindings` retains every original finance requirement. Auction recognition
additionally requires the three new Auction tests and all registration, research,
trade command, amount, successful purchase and successful sale calls in the same
matched-control test. Missing these new calls leaves Auction unbound; sibling
finance recognition still requires its original full-suite and per-consumer gates.
Synthetic protocol tests pass through the real identity/hash/transcript verifier,
prove that adding the complete Auction path removes exactly its finding relative
to the original finance evidence, and reject missing, failed, stale, tampered,
focused or disconnected evidence. Synthetic fixtures are never release evidence.

`validation.json`, compressed transcripts and result manifests describe fresh
current-source developer checks. The final Wurst selection includes every finance
case, registered trade, pricing/provenance and research tests. It also covers stale
stock/previews, research removal, missing facilities, wrong control/title/office,
access changes including commit-time invalidation, tiny orders, duplicate requests,
counterparty funds, cargo compatibility/capacity, reconstruction, named-source
replay and late campaign-load rollback. Original and content-mutated standalone
framework scenarios run against current shared source. Python packaging tests use
explicit synthetic compiler fixtures; their printed suite counts are protocol
checks, not gameplay execution.

## Reproduction and integration handoff

From the scenario directory, run `prepare-focused.py PATH_TO_CACHED_WURST_STDLIB`
and `prepare-framework.py PATH_TO_CACHED_WURST_STDLIB` in this directory. These
assemble current source and use only cached upstream library source as a dependency.
Run the prepared assemblies in the pinned image recorded in `validation.json`,
with networking disabled, UID/GID 1001, read-only source mounts and a copy into
container-private `/tmp`. Verify the compiler SHA and `inputs.sha256` before and
after `grill typecheck` and `grill test`. Retain stdout/stderr as `pinned-wurst.log`
and `framework-{original,mutated}.log`. `record-focused.py` verifies identities,
results, input hashes and observed calls before retaining compressed evidence.
It also proves that the existing transcript verifier accepts the selected run
while the full integration verifier rejects its incomplete discovery.

All three official source reports are refreshed for this worktree. They correctly
retain the Auction finding without full integration evidence. The controller owns
complete repository validation, fresh full-suite execution and packaged campaign
verification after integration, followed by regeneration of release-blocker,
runtime-acceptance and requirement-traceability audits on the new main revision.
That run must remove this exact Auction finding using accepted current-source
execution evidence; a merge or issue closure is insufficient. Native launch #438
and release promotion remain blocked. No player QA or GitHub mutation was used.
