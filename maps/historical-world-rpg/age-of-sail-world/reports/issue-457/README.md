# Issue 457 — spendable earned hero progression

The production RPG registry exposes `/progression HERO`, `/improveskill HERO SKILL`,
`/improvemastery HERO MASTERY` and `/chooseperk HERO PERK`. Generated definitions
supply skills, masteries, abilities, minimum levels, prerequisite chains and
personal-tree membership. Only the campaign player's recruited character can
spend that character's matching points. Rejections precede all mutations;
repeated perk selection cannot charge again. Inspection participates in the
existing RPG pause session. Respecialization remains unavailable.

The allocation contract matches the Python progression authority. Starting
profiles, earned levels, ranks, balances, selections and recovery persist in the
existing RPG v6 fields. Supported older records keep existing allocations with
zero missing choice balances; no retrospective points or refunds are granted.
Reconstruction does not replay rewards or allocations. Recording campaign ports
exercise full rollback after a failed restoration.

Validation passed: **441/441 pinned Wurst tests**, typechecking, **122 Python
regression tests**, **57 focused checks** after the help updates, and both
framework variants (**2/2 Wurst tests each**, with built archives). Compiled
inspection verified all **28 allocation definitions**, four action registrations
and **107 starting profiles** against the same source identity. All **7,042
unrelated publication blockers** remain unchanged.

See [HERO_ALLOCATIONS.md](../../docs/HERO_ALLOCATIONS.md) for commands and the
compatibility contract. `validation.json` retains compiler and source identities,
full pinned test results and evidence hashes. `scoped-traceability.json` compares
all unrelated blockers with the incoming revision. `compiled-allocations.json`
checks actual definition and command calls in a diagnostic W3X built from the
same dirty-source identity; the generated archive stays in the ignored build
output. It is not native-client launch evidence or a release candidate.
Python packaging fixtures include synthetic compiler controls for their rejection
tests; the separate pinned transcript and actual archive inspection supply the
compiler evidence.

Closure covers allocation and selected entitlements only. Ability-effect
consumers, broader reward-source integrations, relationships and other progression
axes remain blocked. The three compound ROAD-0051/REQ-0091.02/REQ-0092.01
obligations are intentionally not marked complete by allocation-only tests.
No player QA is requested. No repository history or external applications were
changed. The pinned cached toolchain was extracted without host mounts or network;
all validation ran as the host user.

Reproduce from the scenario directory with pinned Grill on PATH:

```sh
python3 -m unittest discover -s tests -p 'test_hero*.py'
python3 -m unittest discover -s tests -p 'test_live_hero_progression.py'
python3 ../_shared/tooling/package_wurst_map.py package.json
python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign
python3 tooling/requirement_traceability_audit.py --write --check
python3 reports/issue-457/inspect_compiled.py _build/release/AgeOfSailWorld.w3x --output reports/issue-457/compiled-allocations.json
```

The outer worker performs the authoritative configured repository validation.
