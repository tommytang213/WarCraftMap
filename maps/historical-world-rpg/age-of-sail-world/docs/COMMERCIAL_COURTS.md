# Chartered Companies: courts and merchant construction

Issue #526 follows the delegated routine policy/finance design in
HISTORICAL_BALANCE_AND_RESEARCH_EFFECTS.md. Scenario data owns every identity,
rate, site and bill. Completing Chartered Companies grants two independently
consumed permissions and never spends treasury, creates a ship, upgrades a hull
or activates a policy. It preserves the catalogue's prerequisites, date and cost.

`/courts inspect MARKET`, `/courts policy MARKET` and `/courts repeal MARKET`
manage local commercial courts at London, Venice, Lisbon and Cairo. Policy use
begins in 1600, the authored preferred year; early research retains its permission
until then. Eligibility
requires current lawful control, matching local administration, bookkeeping,
accessible commerce and an actual warehouse. Enactment costs 1% of annual normal
tax capacity plus the first 0.5% annual administration bill, rounded up separately.
For London/Venice/Lisbon these are 34 + 17 treasury minor units; Cairo 27 + 14.
The 90-day transition precedes 365 prepaid operating days. Renewals consume real
treasury before the next term; failure ends the policy without refund or automatic
reactivation. Capture and entitlement loss cancel policy benefits. No loans,
debt, standing, free principal or market stock are created.

The bounded commercial service is formal **local warehouse purchases and sales**
at those sites, with real generated market and warehouse identities. They pay a
separate 100 bp (1%) processing bill on the actual settled amount, rounded up.
An operating court reduces **only this service bill by 500 bp (5%)**, savings
rounded down, with a positive minimum bill. At 10,000 principal the bill falls
from 100 to 95; at principal 1 it remains 1. Processing bills leave circulation.
The market receives the full purchase principal or pays the full sale principal;
the warehouse pays the purchase bill or receives sale principal less its bill.
No court benefit applies to personal/ship stores, counterfeit stores/markets,
blocked/hostile/unknown commerce, cargo transfers or treasury/exchange/remittance
operations. Existing stock, capacity, counterparty funds, provenance, physical
access and duplicate transaction checks still govern commits. Trade recalculates
bills inside its authoritative commit; it does not cache an entitlement discount.
This consumer needs no exchange research effects or Battlefleet Doctrine.

`/naval build PORT armed_indiaman` quotes and commits construction through the
existing shipyard action system. A real commissioned paid dock is required, with
lawful local control/administration, port/material access and Dockyard Logistics.
The resolved merchant roster supplies: **850 currency, 160 manpower, 55 provisions
and settlement supply, strength 500, and upkeep 42 currency per 30 days plus one
provision/day**. The established hull bill also consumes 40 timber, 20 iron and
180 construction days. All inputs are withdrawn before work begins; no refund is
issued for cancellation. Unlike battlefleet construction, this merchant has no
Permanent Naval Board or separate ordnance entitlement requirement in its roster.
Joint-stock Enterprise, Galleon Design and Public Credit are independently
required, along with exact `unit:armed_indiaman` permission. Historical availability
is 1600–1820, or early access from 1570 with the existing Galleon Design condition;
all other roster research stays mandatory. Quotes bind day, serial, balances,
stock, research and durable authority; commit rechecks eligibility and rejects
stale/foreign/replayed quotes. Research never performs construction itself.

Construction uses the existing single berth. The saved build target identifies
the selected roster blueprint; old empty targets retain the default battlefleet
blueprint. Capture cancels work and naval board without refunds, preserves the
finished dock and existing hulls, and requires the new controller's own permission
for later builds. Completed hull maintenance follows the roster after capture.
Active and abstract simulation use the same ledgers and calendar advance.

Military snapshots advance to **v20**, adding mandatory `o` records per
configured court: site, policy owner, ready day, paid-through day, last day and
serial. Main v19 saves retain municipal `u` records; independent courts v19
saves retain their court ledger and migrate missing municipalities inactive.
Versions 1–19 without court records migrate inactive without importing
live policy or charging money. Partially present ledgers reject. Parsing is
detached and validates canonical fields, controllers, complete site coverage and
candidate clock before replacement; existing campaign checkpoints include courts,
construction, research, treasury and trade state for late failed-load rollback.
RPG, trade and outer campaign save schemas remain unchanged.

CharteredCompaniesTests exercises production registration, research, policy,
trade, quotes and construction, with independent gates, conservation, replay,
capture, migration, failed-load rollback and 25-year active/abstract parity.
Release evidence selection requires a verified current-source full-suite run;
focused test logs do not close blockers. After overlap integration and merge, the
controller must regenerate release, runtime and traceability audits on new main.

## Phase 9 institutional courts and Commercial Statistics (#588)

Commercial Courts institution adoption retains Merchant Correspondence and the
catalogue's 14% urbanization requirement. A currently lawful administered civic
district must meet that threshold. Adoption grants only
`policy:progression_commercial_courts_institution`; it never grants Chartered
Companies or elects either court policy. `/courts institution MARKET` elects the
institutional source separately; `/courts repeal-institution MARKET` repeals it.
`/courts policy MARKET` and `/courts repeal MARKET` retain their corporate meaning.
Both use the existing qualified sites, bookkeeping requirement, 1% annual normal
tax setup bill, 90-day transition and prepaid 0.5% annual upkeep. Each election
pays its own bills and tracks its own owner, readiness, funding and serial.
`/courts inspect MARKET` explains both elected sources on the same service.

Only operating, currently entitled sources reduce the existing processing bill:
400 bp institutional plus 500 bp corporate, summed before the existing floor of
savings. Thus a 1,000-unit bill is 960 with institutional courts, 950 with corporate
courts, or 910 with both. A one-unit bill remains one. Capturing a site clears both
choices without transferring research, and failed renewal ends only that source.
Re-enactment pays again and repeats its transition; it never resumes for free.

Commercial Statistics binds `modifier:progression_commercial_statistics` at its
1740 preferred year. Existing formal exchange execution charges fund price
reporting and market coordination on actual purchases and sales. It reduces only
the execution-slippage component by 500 bp, compatible with Brokerage's 700 bp.
A 1,000-unit slippage component is 950 with Statistics or 880 with both. The processing bill retains its original pre-discount quote base, so reporting
does not reduce another fee bucket. Commission, scarcity and unrelated charges keep their own rules; principal is never a rebate
base. Current registered market and warehouse services, lawful administration,
access, real stock, counterparty money and cargo capacity remain authoritative.
Transfers and estimates earn no output or standing. The spread remains positive;
same-market round trips lose money and cannot earn route standing.

Trade inspection shows current execution estimates and eligible warehouse
processing bills. Settlement recomputes current research, elected funding and
resource checks; an earlier estimate neither locks a discount nor bypasses any
check. Stable transaction IDs retain the existing replay history and FIFO costs.

Military snapshots use **v26**, retaining the independent v25 uppercase `O`
records for institutional court sites, distinct from corporate lowercase `o`
and banking `b`. Versions 1–24 and Customs-House-only v25 snapshots retain
their existing state and initialize institutional elections unfunded. Courts-only
v25 snapshots preserve paid institutional choices and initialize Customs Houses
unbuilt and unfunded. Missing, duplicate, invalid-controller
or future-clock current records reject in detached staging. Campaign checkpoints
include the new ledger with treasury, stock, cargo and transaction history for
late-load rollback. No outer campaign, RPG or trade schema changes are needed.

`SettledTradeServicesTests.wurst` registers separate institution-only and
Statistics-only buy/sell comparisons, combined-source arithmetic, adoption and
service/resource negatives, failed upkeep, replay, split orders, round trips,
player/AI and active/inactive parity, migration, capture, repeal/re-enactment,
save/resume and late-load rollback. The evidence verifier requires each exact
comparison's own production probes and the common lifecycle tests after full
current-source pinned execution. Corporate courts or sibling finance evidence
cannot close these findings. Focused development runs do not close release
findings. After integration the controller must run the full pinned suite and
regenerate release-blocker, runtime-acceptance and requirement-traceability audits
on the new main revision. No player QA is required.
