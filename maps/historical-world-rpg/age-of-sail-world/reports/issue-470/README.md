# Issue 470 — individual item definitions and equipment delivery

Generator v28 retains all 468 player-use items, 899 major-stat entries, 99 effect
references and 14 complete conditional descriptors. Executable definitions retain
level, rarity, provenance, requirements, slot and set metadata. Afghan Pulwar
keeps `meleePower=40` and `mountedPower=12`; equipment never converts their sum to
maximum life.

Registered inventory inspection compares against the selected wearer's slot,
showing candidate values and positive/negative deltas for the union of stat IDs.
Effect IDs, conditions and requirements stay visible. The typed projection port
receives complete item definitions under stable wearer/slot identities. Content
fingerprints keep unchanged layers stable and retain complete metadata in the
optimized executable. Replacements and removals preserve other layers and native
modifiers. Existing wearer isolation, research eligibility and set resolution
remain covered by their production command tests.

RPG v7 and campaign save envelopes are unchanged. Supported legacy RPG v1–v6
loadouts reconstruct derived definitions without grants, loss or new eligibility
checks. Late restoration failures retain prior authority, item/set layers and
representations. Hero-defeat/recovery tests now verify typed equipment retention
and base life instead of the removed health fallback.

`validation.json` records the pinned execution/typecheck, original and mutated
framework builds, Python checks and evidence hashes. The compressed interpreter
transcript and result manifest retain every executed test. Python packaging and
framework tests contain synthetic compiler controls for rejection paths; those
are distinct from the real pinned execution and build evidence.

`compiled-items.json` reads actual optimized Lua registrations from the diagnostic
W3X, compares every item with the authoritative catalogue and rejects omitted
stats, effects and conditions. It also checks that complete descriptors and
provenance survive optimization. The archive remains under ignored
`_build/issue470-artifact-verified`; its revision and source-content identity match
the full interpreter evidence in `_build/issue470-verified`.

`scoped-traceability.json` covers definition retention, comparison and typed
delivery for REQ-0071–REQ-0077 and the item-comparison portion of ROAD-0133. It
retains parent-obligation blockers and verifies that unrelated publication
blockers are unchanged. Item stat/effect consumers, conditional activation,
merchant-context integrations, set-effect consumers and real native launch remain
separately accountable. This is neither a gameplay-effect success claim nor a
release candidate. No player QA is requested.

Validation runs as the host user. The pinned compiler/JDK were copied into this
worktree from a cached, unstarted container with no mounts or network; that
container was removed. No global tooling, services, Git history or GitHub records
were changed. The outer worker performs authoritative repository validation.

Reproduce from the scenario directory with the pinned Grill on PATH:

```sh
python3 tests/test_item_definitions.py --write-vectors
python3 -m unittest discover -s tests -p 'test_item_definitions.py'
python3 -m unittest discover -s tests -p 'test_equipment*.py'
python3 -m unittest discover -s tests -p 'test_inventory.py'
python3 -m unittest discover -s tests -p 'test_cross_map_persistence.py'
python3 -m unittest discover -s tests -p 'test_campaign_save*.py'
python3 ../_shared/tooling/run_wurst_tests.py package.json
python3 ../_shared/tooling/package_wurst_map.py package.json
python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign
python3 tooling/requirement_traceability_audit.py --write --check
python3 reports/issue-470/inspect_compiled.py _build/release/AgeOfSailWorld.w3x --output reports/issue-470/compiled-items.json
```

See [the item definition contract](../../docs/ITEM_DEFINITIONS.md) for layer
ownership, technical budgets, comparison semantics and save compatibility.
