# Issue #432: Remote command authorization

Under ROAD-0062, this repairs the access boundary after #305. The registered
`/region` command uses `PlayableRegionAccess` backed by current campaign
settlement and force records. Discovery still filters requests before command
authorization; revealing or visiting a region no longer grants control.

The existing campaign controller is `Player(0)` / `player`. A controlled
settlement, including an abstract settlement or captured holding, permits its
region to be managed. A living, active army or fleet controlled by that player
also permits access. AI local defenses do not independently confer command.
Citizenship, allegiance, an administrative office, or legal title to territory
under hostile control cannot substitute for current control. No additional
explicit remote-delegation contract is currently registered by the campaign;
the existing `RegionAccessPolicy` seam remains available for authoritative
contracts. Region selection never assigns owners or controllers to entities.

Location matching uses generated scenario assignments for logical regions,
physical chapters and legacy regional instances. Unknown labels fail closed.
The shared engine contains no Age of Sail region IDs. Each request rereads the
campaign arrays, including requests for the current view, so capture, control
loss, force destruction and restored records take effect without cached grants.
Rejected authorization makes no context-adapter calls and acquires no pause
token. Return to the known physical region requires no remote grant.

A committed load reconstructs the physical region and resets the selector,
releasing only its own modal token. Rejected validation and failed reconstruction
preserve the previous authority, command view and pause owners. Access and view
state remain reconstructible; there are no new saved fields. Campaign schemas
1–8 and the existing military-domain migrations are unchanged.

`RemoteRegionAuthorityTests.wurst` dispatches the production registered command
with populated campaign authorities and recording context adapters. It covers
knowledge, citizenship, allegiance, visitation, another player slot, hidden
owned forces, abstract holdings, logical/physical/legacy location IDs, captures,
control loss while a view is open, ineligible forces, repeated reconstruction,
successful and rejected loads, adapter failure, nested pause ownership, and
return to the physical region. Authority snapshots include party locations,
orders, settlement control and unrelated forces.

The mappings and scoped packaged verifier cover REQ-0296.01 and REQ-0305.01 at
this authorization boundary. **Physical cross-map command transport remains
unfinished under REQ-0300.01 and ROAD-0062.01. Native launch confirmation and
release acceptance remain blocked.** No player QA, CI change, publication or
release approval is part of this work.

After a pinned campaign build, reproduce the packaged check with:

```sh
python3 reports/issue-432/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/wurst-tests \
  --source-revision FULL_BASE_REVISION \
  --output-dir _build/issue432-evidence
```

The source-tree digest distinguishes uncommitted implementation bytes from the
base revision. The outer worker must regenerate evidence for any later commit.
Local validation results are recorded in `validation.json`.
