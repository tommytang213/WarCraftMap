# Issue 459 — complete equipment-set definitions and resolution

Generator v26 retains all 51 authored sets, 151 thresholds and 188 effect
references. The 49 sets with middle thresholds retain those tiers. Stable piece
identities, slot qualification, explicit/default threshold IDs, authored effect
order and existing cumulative/exclusive/replacement policies reach the shared
resolver. Invalid references and over-budget definitions fail generation.

Registered equipment actions resolve separately for each wearer. Production
projection receives complete typed wearer/set/threshold/effect layers; replacing
or removing one layer preserves other sets, wearers and unrelated modifiers.
Reconciliation visits equipped wearers and retires obsolete layers after the
complete pass. It also works without a current Warcraft representation.
Inspection shows every tier and its active, unmet or superseded status.

Set effects remain unbound references. Name-only definitions never become health
bonuses or passing gameplay-effect claims. Ordinary item eligibility, copy
conservation and uniqueness remain enforced. RPG v6 and supported legacy saves
are unchanged: equipment authority reconstructs all derived results, and rejected
restoration retains the prior loadouts and layers.

The retained validation covers the pinned Wurst suite/typecheck, inventory,
equipment generation, Python resolver parity, persistence and framework checks.
The framework's original and content-mutated campaigns both build with unchanged
shared sources. `compiled-equipment-sets.json` compares actual optimized Lua
registrations with every authored definition and includes negative controls for
dropped tiers and lost effect identities. The diagnostic archive remains under
ignored `_build`; its source identity matches the execution evidence.

`validation.json` records exact results and evidence hashes. The compressed logs
include the full pinned execution transcript and Python checks. Python packaging
tests use synthetic compiler controls to test rejection paths; they are separate
from the pinned execution and real compiled archive evidence.
`scoped-traceability.json` retains ROAD-0053's downstream blockers and verifies
that all unrelated publication blockers remain unchanged. Gameplay bindings and
the real Forsaken Kingdom native-launch smoke remain blocked. This is not a
release-candidate or native-client claim, and no player QA is requested.

All validation ran as the host user. The cached pinned compiler was copied from
an unstarted container without mounts or network; that temporary container was
removed. No services, global tooling, repository history or GitHub records were
changed. The outer worker performs the authoritative repository validation.

Reproduce from the scenario directory with pinned Grill on PATH:

```sh
python3 tests/test_equipment_sets.py --write-vectors
python3 -m unittest discover -s tests -p 'test_equipment*.py'
python3 -m unittest discover -s tests -p 'test_inventory.py'
python3 ../_shared/tooling/run_wurst_tests.py package.json
python3 ../_shared/tooling/package_wurst_map.py package.json
python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign
python3 tooling/requirement_traceability_audit.py --write --check
python3 reports/issue-459/inspect_compiled.py _build/release/AgeOfSailWorld.w3x --output reports/issue-459/compiled-equipment-sets.json
```

See [the equipment-set contract](../../docs/EQUIPMENT_SETS.md) for policy and
projection ownership details.
