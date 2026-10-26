# Ciphered Dispatches

`scenario/progression/dispatch-contract.json` owns the routine effect delegated
by issue #528. The existing communications branch supplies only research
entitlements: Courier Relays (1450, base 75) precedes Ciphered Dispatches (1480,
base 104), with the historical ahead-of-time formula unchanged. The Python
administration model computes capacity from skills, titles and jurisdiction
load, and efficiency from weighted skills and local conditions. Neither model
has a delivery-time consumer. The remote-region selector and command-map
transport separately enforce knowledge and live command rights. Dispatches
change none of those calculations or permissions.

The concrete consumer is the paid **cadastral survey instruction and return**.
`/civic survey DISTRICT` enters `CivicCampaignRuntime.act` and
`CivicLedger.action`; it requires the existing Cadastral Survey research, lawful
control, a local office, no previous/pending survey, and the full 1% annual-tax
bill, rounded up. The ordinary completion deadline is still 90 campaign days.
The campaign day listener calls `CivicLedger.advance` for active and abstract
holdings alike. Its pending-survey branch now resolves dispatch delivery at
each completion opportunity. Ciphered Dispatches reduces this deadline by
**1000 basis points of the normal duration**, floor rounded: **9 days**, so the
earliest completed state is day **81**. The operation carries authoritative
orders and assessed land records; it never creates geographic knowledge.

Early completion additionally pays **25 basis points (0.25%) of the district's
normal annual tax**, rounded up, minimum one minor currency unit, from the
current controller's real treasury. A 10001-unit district pays 101 for the
survey and 26 for early dispatch. Missing funds postpone early completion;
the original paid survey still finishes normally at day 90 without this bill.
No municipal enactment, Archives research, extra skill bonus or policy is used.
The completed survey retains its existing tax-assessment behavior.

A recipient qualifies only with both own completed research entitlements and
one exact authored directed relay link. The initial network is Lisbon–Goa,
Constantinople–Cairo and Goa–Malacca, each in both directions. Both endpoints
must remain lawfully administered holdings of the same controller, free of
occupation/attack, and each must have a stocked market free of blockade/hostile
occupation. The recipient's serving administrator must retain its exact district
jurisdiction, positive capacity, and physical residence in the origin region,
which must differ from the recipient region. Another region, an invented
endpoint, a resident local administrator, map viewing, mere discovery and another
controller's research supply no early-completion eligibility. The authored link
represents the supported courier corridor; endpoint access never expands it.
No force, character or commodity moves through this operation.

The adapter reads durable settlement and office identities, never native unit
handles. Eligibility is re-read at the outcome boundary, including current
control, jurisdiction, residence, research and market access. A lost link can
postpone completion back to the original deadline. Ordinary capture cancels a
pending survey; a successor must pay for its own order. A completed assessment
remains a completed local record under the existing capture rule.

No new saved fields or schema are introduced. Military v20's existing `g`
record persists survey owner, **normal** deadline, completion and replay day;
RPG research retains its ordinary typed sources. Reconstruction regenerates the
network definitions, then restores those fields without advancing or charging.
Old pending surveys keep their original deadline and gain eligibility only from
current research/access. Pre-civic migrations remain unsurveyed/unfunded.
Completion sets the existing `surveyed` flag only after payment; later days,
duplicate commands, duplicate research sources and repeated loads cannot charge
again. Staged ledger forks copy network definitions, preserving campaign failed-
load rollback. No launch behavior or evidence for #438/#455 changes.

`DispatchTests.wurst` exercises registered research and survey orders, timing and
bills against matched controls, historical research costs, access/relay/authority
negatives, office replacement, source deduplication, capture, active/abstract
replay, fresh reconstruction, migration and late campaign-load rollback.
`test_dispatch_contract.py` checks generation and fail-closed evidence binding.
Focused results are development evidence; full shipping archive inspection and
new-main release/runtime/traceability audits remain controller validation.
