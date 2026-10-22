# Central Banking and Central Bank operating contract

Issue #524 uses the owner's delegated routine finance/policy design in
`HISTORICAL_BALANCE_AND_RESEARCH_EFFECTS.md`. The values are bounded gameplay
calibration, not estimates of historical returns. The scenario owns identities,
fees, eligible banks and policy expenses in `scenario/progression/central-banking.json`
and `central-banking-effects.json`. The shared banking modules contain no Age of
Sail identities. This consumer works without TradeFinance or its exchange,
remittance and canal consumers (#517).

The real operation is treasury lodgement: withdraw an existing amount of currency
from the controlled bank's warehouse and place exactly that principal in its
controller's government treasury. Currency is measured in integer minor units.
Two separate service bills leave circulation: counting costs **100 bp (1%)** of
principal and reconciliation costs **100 bp (1%)**. Each base bill rounds up,
with a minimum of one minor unit. No operation can create principal, loans,
credit, debt, debt forgiveness or merchant standing. No operation advances time.
At zero activity both research benefits are zero.

The authored banks are **London, Venice, Lisbon and Cairo**. Each must have the
actual banking, market and warehouse services and generated trade stock. Use
requires current control, legal ownership, no occupation conflict or attack,
a current administrator of the same controller, an accessible non-blockaded,
non-hostile stocked market, the existing warehouse and completed Double Entry
Bookkeeping. The generator rejects missing infrastructure. Government actions
may operate on active or unloaded settlements using the same durable authority;
a Warcraft unit instance never owns the policy or money. Player and AI
controllers use the same engine entry points.

Central Bank institution adoption earns only
`policy:progression_central_bank_institution`. It retains its Merchant
Correspondence prerequisite, preferred year **1694**, base research cost **283**,
existing ahead-of-time cost curve, minimum urbanization **19**, required-node and
diffusion/adoption data. It never completes Central Banking research. The policy
is locally available from 1694, but needs an explicit validated
`/banking policy BANK` action. Enactment consumes **100 bp (1%)** of that bank's
normal annual tax capacity plus **50 bp (0.5%)** for the first year's upkeep from
its controller's existing government treasury. Both bills round up separately.
The normal-tax calculation is the same scenario-owned capacity calculation used
by civic administration, including capital, port and trade-center factors.

| Bank | Normal annual tax | Enactment | Annual upkeep | Initial total |
| --- | ---: | ---: | ---: | ---: |
| London, Venice, Lisbon | 3,341 | 34 | 17 | 51 |
| Cairo | 2,673 | 27 | 14 | 41 |

After a **90-day transition**, the funded policy reduces only the reconciliation
service bill by **500 bp (5%)**. Annual upkeep buys 365 operating days beginning
at the end of transition; expiry is exclusive. Each renewal is paid before the
next operating period. An unfunded renewal ends the policy; restoring money does
not reactivate it or replay missed service. Repeal costs nothing and refunds
nothing. Duplicate enactment is rejected. Capture cancels the old controller's
policy without refund, retains the infrastructure and invalidates old quotes.
The new controller must independently qualify, adopt and pay to activate.

Central Banking technology earns only
`modifier:progression_central_banking`. Its Auction Markets and Standing Army
System prerequisites, preferred year **1695**, base cost **292** and historical
cost curve remain unchanged. From 1695 it reduces only the counting bill by
**600 bp (6%)**, and only while the separately unlocked, enacted, transitioned
and funded institution policy operates. Technology alone grants no policy and
reduces no fee. Institution alone never supplies the counting improvement.
Savings round down from each positive base service bill independently; each
final bill remains positive. Duplicate research provenance contributes once per
controller, including after reconstruction or reload. These identities never
modify exchange spreads, remittances, canal financing or other money operations.

For a principal of **10,000**, the counting/reconciliation bills are:

| Entitlements / state | Counting | Reconciliation | Total service cost |
| --- | ---: | ---: | ---: |
| Neither | 100 | 100 | 200 |
| Technology alone | 100 | 100 | 200 |
| Adopted institution, policy inactive or transitioning | 100 | 100 | 200 |
| Institution with operating policy | 100 | 95 | 195 |
| Both with operating policy | 94 | 95 | 189 |

At 10,001 with both, the base bills are 101 each, final bills 95 and 96;
at principal 1 they remain 1 each. Overflow is rejected before either balance
write. Existing warehouse currency must cover principal plus both service bills;
treasury must have room for the complete principal. Policy expenses use treasury,
so enacting a policy cannot spend warehouse currency indirectly.

`/banking inspect BANK` shows eligibility, fee rates, current research reductions,
activation bill, yearly upkeep, transition and funded dates.
`/banking lodge BANK AMOUNT` obtains and commits a production quote. The quote
includes controller, bank, principal, both final bills, day, durable serial and
both currency balances. Commit derives it again from current authoritative state
and rejects stale quotes, unauthorized actors or replays before mutating either
balance. Research changes, repeal, capture, day changes and competing balance
writes are revalidated. Each committed operation advances the durable serial.

Military/settlement snapshots use **v20**, retaining one mandatory
`b` record per configured bank: bank ID, policy controller, ready day, prepaid
through day, last resolved day and transaction serial. Supported versions 1–17
with no banking ledger migrate to inactive policies and zero serials without copying live state,
charging money or activating research. Parsing stages a detached ledger and
rejects unknown/duplicate/missing records, noncanonical integers, contradictory
policy dates, controller mismatches and dates later than the candidate campaign
clock. Existing campaign checkpoints include the banking ledger, treasury,
warehouse balances and research reconstruction, so a late rejected load restores
the complete prior state. Independent v17 banking saves retain policy state and
initialize absent freight counters empty; independent v17 logistics saves retain
freight counters and initialize absent banking policies inactive. Partially
present ledgers reject. V20 requires complete municipal `u` and court `o` records.
V19 saves from either independent branch preserve their paid authority and
migrate the absent domain inactive.
V18 banking saves migrate without activating municipal policies; independent
v18 municipal saves retain their six-field `b` records through arity-based
migration, initializing absent bank policies inactive. Other campaign/RPG
envelopes are unchanged.

`BankingOperationsTests.wurst` exercises registered research and institution
actions, exact comparative outcomes, registered policy/lodgement commands,
quote/commit revalidation, unauthorized actors, missing infrastructure, funding
failure, integer limits, capture, migration, successful reload, late-load rollback
and a 25-year active/abstract conservation test. `test_central_banking.py` checks
scenario compilation, preserved catalogue rules, framework absence and fail-closed
evidence selection. Release binding requires verified current-source full-suite
execution and actual production probes; focused transcripts alone do not close
release blockers. The controller regenerates integration audits on the merged
revision. No player QA is required.
