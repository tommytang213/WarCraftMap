# Agent Development Rules

This repository is designed for agent-assisted development. The player is not a development QA engineer.

## Non-negotiable workflow

1. Treat source files and scenario data as authoritative; compiled .w3x output is generated.
2. Do not require the player to manually use World Editor for routine development.
3. Prefer automated validation, simulation, static checks, deterministic test scenarios, and developer-side testing.
4. Do not ask the player to test incremental features unless a near-final release candidate genuinely needs human gameplay validation.
5. Preserve campaign-save compatibility whenever practical. Schema changes require a version bump and migration path.
6. Keep reusable systems outside scenario-specific content.
7. Avoid hardcoding Age of Sail content into the shared engine.
8. Critical city/campaign state must never depend solely on the continued existence of a Warcraft object instance.
9. Release-facing text is English unless a scenario explicitly says otherwise.
10. Target the latest supported Warcraft III release and keep version-specific behavior behind compatibility modules where practical.

## Player role

The player provides design decisions and eventually plays release candidates. Development should minimize manual human involvement.
