# Conflict and peace authority

Political `activeConflicts` are registered by stable ID, with each original
attacker and defender recorded in `MilitarySettlementRuntime`. Country
negotiation, settlement attacks, and capture query that same registry. Only
opposing sides justify hostility. Settling a conflict retains its membership and
a settled marker; registering its scenario defaults again cannot restart it.
Another active conflict may still authorize hostility between the same parties.

The country runtime binds each offer to its original conflict, recipient, and
proposing government. Acceptance rechecks current allegiance, discovery, opposing
participation, confirmation, and the campaign peace adapter. A stale offer cannot
settle another conflict. Rejection changes only the offer's response history;
failed validation or missing confirmation changes neither offers nor warfare.
The current Wurst adapter supports `ceasefire` and
`cede:SETTLEMENT:GRANTOR:BENEFICIARY`; unsupported outcomes fail before mutation.

Settlement authority retains legal ownership separately from military control
and attributes occupations to a conflict. Cession validates the legal grantor,
opposing beneficiary, and present control. On accepted peace, named cessions
transfer title and control; other occupations belonging to that conflict return
to their legal owners. The settlement runtime reconciles cores, defenses, and
acting administrators. Sieges without remaining hostility stop and retire their
local garrisons; a siege still authorized by another conflict continues.

## Save compatibility

The campaign envelope remains schema 6. Its existing, independently versioned
`diplomacy` and `militarySettlements` domain payloads advance from **v1 to v2**:

- Military v2 stores conflict IDs, sides, active/settled state, settlement legal
  owners, occupation conflict IDs, and the attacker responsible for a siege.
- Country v2 stores each offer's conflict and proposing government. Offer statuses
  are pending (0), accepted (1), rejected (2), and legacy unbound (3).
- Military v1 pair wars are reconciled against the registered political defaults.
  A pair already explained by an authored conflict gets no additional source of
  hostility. Unattributed pair wars retain a stable `legacy:` identity.
- A populated country v1 ledger supplies the surviving active IDs; other authored
  conflicts remain settled. The old format stored only one conflict per country
  and erased IDs on peace, so lost historical membership cannot be invented.
  Empty ledgers from before diplomacy use the authored defaults. This also applies
  when an older campaign envelope receives synthesized military defaults.
- Legacy offers retain their IDs and terms, but become unbound and cannot be
  accepted: v1 did not record which conflict or government originally proposed
  them. Offer sequence numbers remain monotonic.
- Legacy settlements retain their saved controller as legal owner because v1 did
  not distinguish occupation from an accepted cession. Unattributed legacy siege
  activity stops; a new attack must pass current hostility checks.

Both domain parsers validate detached records before replacing authority. Current
saves preserve tombstones and exact membership, pending bindings, title, control,
and siege attribution across the live codec and repeated reconstruction.
`ConflictPeaceIntegrationTests.wurst` executes generated registrations, the
registered country command/controller path, the campaign peace adapter, and the
live save codec with initialized authority fixtures.
Load-transaction regressions also validate both country payloads against the
candidate's conflict membership and preserve settled conflicts, bound offers,
active sieges, and existing projections after a late reconstruction failure.
Founded-polity validation uses the military parser's v1 migration as well, so
legacy settlements and pair wars remain loadable through that adapter.

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
Automated validation does not change that release gate or require player QA.
