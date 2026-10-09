# Issue 433: Exact equipment research prerequisites

Generator v22 retains every authored technology and institution requirement for
all 468 player-use items. References must be unique stable IDs within the runtime
budget and resolve to the correct research kind. Colonial Printed Almanac's
movable-type printing prerequisite is classified as an institution, consistent
with the authoritative research catalogue and its authoring script.

The production equip command takes its controller and date from the existing
research resource boundary. Every required ID must be completed for that exact
controller. A rejection preserves all owned copies, wearer assignments, item/set
bonuses and native projection writes, with bounded English feedback. Existing
level, date, recruitment, ownership, unique-copy and wearer-slot rules remain.

Equipment definitions are regenerated; no persisted fields changed. RPG v3,
supported v2/empty-v1 restoration and campaign envelopes 1–8 retain their existing
semantics. Loadouts earned under the earlier incomplete gate retain their items,
wearers and bonuses on load and reconstruction. Subsequent equip actions use the
full current requirements.

The nested `equipmentEligibility` mapping under REQ-0076.01 records only this
repair. The canonical traceability report still blocks the whole requirement and
DEP-equipment-technology-trade: merchant availability, broader progression and
trade integration remain incomplete. Native launch remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`. No player QA is required.

Final validation is recorded in [validation.json](validation.json),
[scoped-evidence.json](scoped-evidence.json) and the compressed logs:

- All **356 pinned Wurst tests passed**. All **17 diagnostic maps** typechecked,
  compiled and passed archive inspection. The final campaign contains **7,488
  compiled item registrations**, with all 46 technology and 6 institution
  references retained in each of its 16 gameplay maps.
- The full Python run passed **941/942** cases. Its sole failure was a stale
  release-report hash for the updated equip probe; refreshing that one output
  hash made the failing freshness test pass. All **136 automation tests**, **38
  focused inventory/research/save tests**, and **6 equipment-generation tests**
  passed. The full Python suite was not repeated after this output-only refresh.
- Original and content-mutated framework campaigns each passed **2/2 Wurst
  tests** and compiled with unchanged shared sources. The native-save
  reconstruction oracle passed; the actual client step was skipped because no
  runner is configured.
- Source traceability freshness passed. The source release audit retains **21**
  findings; the full artifact report retains **8,764** publication blockers.

The initial new reconstruction fixture reused a representation ID while resetting
its recorded base life. It now allocates a fresh identity each time and asserts
all three wearers' bonuses before and after reconstruction; the final complete
Wurst run passes. Python logs also contain intentional error output from negative
packaging and worker fixtures.

The artifact verifier
checks receipts inside the named passing production-command tests, every compiled
item requirement set in every regional map, and matching source identities. It
retains the complete blocked artifact report alongside the narrower evidence.

```sh
python3 reports/issue-433/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/wurst-tests \
  --output-dir _build/issue433-evidence
```

The cached pinned compiler and bundled Java were copied from an unstarted
container into ignored worktree storage and executed locally with an offline
standard-library cache. No worktree was mounted into a container, and no global
tools or services were changed. Generated game archives remain under `_build`.
No commits, pushes, GitHub writes or native-client execution were performed.
