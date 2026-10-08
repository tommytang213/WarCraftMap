# Conflict and peace authority

## Pirate-polity founding and reconstruction

`found-free-polity` is a one-time transaction through the production piracy
bridge. Progression comes from the piracy authority. Territorial rights come
from the individual `player` controller, never from the submitted territory
list or the player's government allegiance. Every requested settlement,
including the capital, must have player control and legal title, no occupation
or active siege, and an active, surviving authoritative city core. Foreign
occupations must resolve through ordinary peace/cession before they can be
incorporated. No Warcraft object is required for an abstract settlement.

The bridge validates the entire list, capital membership, duplicate/invalid
IDs, country and military identity collisions, player identity, and registry
capacity before changing any authority. Valid grants use the settlement
authority's sovereignty transfer, which also reconciles cores, defenses,
garrisons and acting administration. Only this initial transaction changes the
founder's allegiance.

Piracy authority **v2** records `foundingTerritories` as history. Current legal
ownership, control, occupation, losses and resources remain in their existing
military and country domains. Reconstruction registers a missing country and
derived discovery/recognition idempotently; it never transfers historical land,
changes allegiance, or resets an existing treasury or material stock. A lost
capital or loss of all founding settlements does not invalidate the identity.

The explicit **v1 → v2 migration** reads the old `territories` field only as
founding history. Because the old founding bridge could leave cores, defenses
and administrators inconsistent, migration repairs those derived registrations
from each settlement's **saved current controller**. It preserves legal title,
occupation attribution, strength, supplies and inactive losses; it never guesses
a territorial entitlement or grants disputed title. Saves with malformed history
or missing referenced settlements reject before live mutation. The campaign
envelope and military/country schema versions are unchanged, and existing
campaign migrations remain supported.

Both staging and reconstruction remain inside the campaign load transaction.
Later domain or projection failure rolls back migration, identity registration,
territory, resources, allegiance and projections together. Registered-command,
capture/cession, repeated load, legacy-save and failure-injection regressions
are in `CampaignLoadTransactionTests.wurst`; startup also establishes title
through ordinary peace before founding.

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
These checks require no incremental player QA.

## Ordinary conflict and peace

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

The campaign envelope is schema 8. Its existing, independently versioned
`diplomacy` domain uses **v2**. Military **v3** adds the gameplay clock described
in [Settlement combat events](SETTLEMENT_COMBAT_EVENTS.md), retaining the conflict
records introduced by **v2**:

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
