# Issue 449 — authoritative earned hero growth

Live XP now follows the headless convex curve through level 300. The runtime
explicitly reconciles residual and cumulative XP, applies the generated
skill/mastery/choice cadence only to newly earned levels, validates arithmetic
before mutation, and exposes the same balances in character inspection.
Registered quest turn-ins preserve stage/physical validation and deliver the
reward once to the selected eligible character.

RPG v6 retains earlier rank and quest-stage fields and adds choice balances.
Supported old records keep their recorded levels, residual XP, allocations and
reward history without replaying growth or starting profiles. See
[LIVE_HERO_GROWTH.md](../../docs/LIVE_HERO_GROWTH.md) for the numeric range and
migration contract. The repair preserves #434 recruitment, #444 recovery and
#445 authored stages.

The executable vectors independently check every threshold against both a
summation oracle and the Python authority. Recording adapters also cover
registered rewards, arithmetic limits, multiple characters, accomplished
recruits, repeated reconstruction, legacy migration and rejected-load rollback.
The diagnostic W3X inspection compares all generated hero cadence/starting
definitions with source content and retains the quest and recovery definitions.

Validation results, compiler/source identities and retained evidence hashes are
in `validation.json`. The final build passed **408/408 pinned Wurst tests** and
typechecking. The targeted Python suite passed **114 tests**, traceability passed
**48**, and the release audit passed **9**. Both conformance campaigns passed
**2/2 Wurst tests** and built their archives. Static inspection verified all
**107 hero definitions**, the recovery duration and **304 quest definitions** in
the same-source diagnostic W3X. The source inventory preserves all **7,120
unrelated publication blockers**.

`scoped-traceability.json` records the four affected
obligations and compares all unrelated blockers with the incoming revision.
The checked-in inventory remains blocked for publication. Broader reward-source
bindings, point spending, ability effects and remaining independent hero axes
are outside this repair's closure claim. A diagnostic W3X is not a release
candidate or native-client launch result; #438 and unrelated release blockers
remain unresolved. No player QA is requested.

Compiler/Java files were extracted from the repository-pinned cached image into
the ignored build directory using a container with no host mounts or network.
All compilation ran as the host user. No global tooling, services, external
applications or repository history were changed. The cached standard library
was copied into that same local tool directory for offline dependency setup.

Reproduce the relevant checks from the scenario directory with the pinned Grill
on PATH:

```sh
python3 -m unittest discover -s tests -p 'test_*hero*progression*.py'
python3 -m unittest discover -s tests -p 'test_hero_starting_profiles.py'
python3 ../_shared/tooling/run_wurst_tests.py package.json
python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign
python3 tooling/requirement_traceability_audit.py --check
python3 reports/issue-449/inspect_compiled.py _build/release/AgeOfSailWorld.w3x --output reports/issue-449/compiled-growth.json
```

The outer worker performs the authoritative repository validation. Python
packaging fixtures use their established synthetic compiler controls; the
separate pinned interpreter transcript and actual W3X inspection supply the
compiler evidence.
