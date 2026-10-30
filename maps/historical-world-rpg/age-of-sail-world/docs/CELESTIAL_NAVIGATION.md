# Celestial Navigation voyage contract

Issue #523 explicitly delegates routine effect design from the catalogue's
purpose: astronomical observations improve latitude and position finding. The
bounded tuning below implements that purpose. It is a gameplay value, not a
claim of measured historical efficiency. Research prices, preferred years,
prerequisites and recruitment availability are unchanged.

`scenario/naval/navigation-efficiency.json` owns every identity and magnitude.
The initial eligible route is `channel_position_finding_circuit`: a ten-day
English Channel → North Sea/Atlantic → English Channel station-return voyage
on `europe_west`. Each graph edge must be legal for naval movement. Both ends
are the existing ship station; this operation cannot cross a physical-map
boundary, relocate a force to a destination, visit a settlement or reveal map
knowledge. The route requires the already-known `europe` region. Other routes,
including regional crossings, receive no effect from this contract.

The supported ship is the scenario's `english_patrol_ship`, with its existing
`sailing_ship_default` hull/runtime identity and explicit astronomical-observation
capability. Matching a Warcraft rawcode alone does not establish eligibility.
Other ships, land forces, missing/changed hull identities and unsupported routes
fail closed. The authored station is `(4160, -6720)` on `europe_west`; generation
checks that position against the actual packaged naval raster. Fresh campaigns
place this ship at that station instead of the former unrelated-settlement
fallback. Existing saves retain their recorded location. Departure requires the
correct map and a position within 128 world units of the station. An ordinary
movement order cannot move a vessel while its voyage is pending.

Each day consumes **5 provisions**, including a separately identified **2
provisions for position finding**. A living supported ship whose **current
controller** owns `(modifier, progression_celestial_navigation)` and whose
**purchased astronomical observation kit** remains installed reduces only that
position-finding allowance by **1,000 basis points (10%)**. The other 3 daily
provisions remain due. Ten fully eligible days consume 48 provisions, compared
with 50 under identical conditions without the research. A kit alone or research
alone consumes 50. Research union membership is boolean: repeated delivery or
multiple provenance records never multiply the reduction.

Departure reserves the full **50 undiscounted provisions**. Even a researched,
equipped ship with 49 provisions cannot depart. Each elapsed whole campaign day
consumes its reserved share; earned whole provision credits return to the ship.
Fractional credit uses integer ten-thousandths and carries across interruption,
controller transfer, equipment removal, saves and later voyages. Three eligible
days earn 6,000/10,000 of a provision; two more eligible days release one provision
exactly. Resolving the same day again does nothing. No operation advances,
rewinds, discounts or pauses campaign time.

`/voyage-kit FORCE install` purchases the kit for **120 money**, only on an idle
supported vessel at its station map. Duplicate installation is rejected without
charging. `/voyage-kit FORCE remove` removes it without a refund and can remove
it during a voyage. Research never supplies equipment. `/voyage FORCE ROUTE`
starts the circuit; `/voyage-return FORCE` interrupts it, returning only unused
reserved provisions and keeping credit already earned. The ship returns to its
original recorded station position. The active representation is absent while
at sea and is reconstructed at the end or interruption. Unloaded ships use the
same campaign-day resolution. Warcraft object existence never owns progress.

Controller transfer uses the existing `transferControl` boundary; it settles
elapsed days before changing control. Equipment changes likewise settle elapsed
days under the old inputs. Each later resolution reads current controller
research and current equipment again. Research reconciliation rebuilds the
binding without saving entitlements or reissuing equipment. The military screen
shows equipment, pending route, elapsed days, reserved provisions, fractional
credit and current research eligibility.

This research contribution is confined to the position-finding allowance. It
neither overwrites nor reads vessel XP, milestones, refits, combat ratings,
weather, storm handling or exploration rewards. Those independently owned
systems can compose their own line items without being prerequisites for this
consumer. In particular, #514 is not claimed complete by this work.

Live military snapshots advance from v9 to **v10** with optional `v` records:
`force ID, equipment, route ID, elapsed days, last resolved campaign day,
reserved provisions, fractional credit`. Versions 1–9 migrate with no kit,
no pending voyage and zero credit; migration does not copy live state or move
ships. The outer campaign envelope and RPG/research schemas are unchanged.
Detached parsing rejects duplicate records, unknown ship/route references,
invalid integers, inconsistent reserves, out-of-range credit and voyage dates
later than the candidate campaign clock. Existing campaign checkpoints roll
back the complete military record and reconstructed research on a late rejected
load. Headless military schema v2 embeds voyage state v1 when this optional
contract is enabled; schema v1 migrates purely to empty voyage inputs. Scenarios
without a voyage contract retain their existing military schema and behavior.

Automated coverage lives in `NavigationEfficiencyTests.wurst` and
`tests/test_navigation_efficiency.py`, using registered research/voyage commands,
actual campaign-day callbacks, active and unloaded authority, same-condition
controls, interrupted travel, save/resume, old-save migration and late load
failure. Pinned interpreter validation is developer evidence, not native-client
launch evidence. Remaining release blockers stay open; no player QA is needed.

Issue #574 extends this original single-source contract with typed source
composition, coastal chart/bearing commissioning and military snapshot v22. See
[Coastal Triangulation](COASTAL_TRIANGULATION.md) for the current composition,
source-fraction persistence and v10–21 migration contract. Existing celestial
prices, equipment and pending reservations are preserved.
