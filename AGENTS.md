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

## Cloud Agent environment

Python 3, Docker, and the pinned Grill compiler are installed. The Docker socket is mode 660 and owned by the `docker` group, which includes `ubuntu`. A shell started before that membership was recorded cannot access the daemon until a new login. `grill` and `wurstscript` on `PATH` run the compiler jar identified by `PINNED_COMPILER_SHA256` in `maps/historical-world-rpg/_shared/tooling/wurst_execution.py`. Grill loads that installation from `~/.wurst`.

Validate world data and the Age of Sail Python suite with:

```sh
python3 maps/historical-world-rpg/_shared/tooling/validate_world.py \
  maps/historical-world-rpg/age-of-sail-world/scenario/world/world.json
python3 -m unittest discover -s maps/historical-world-rpg/age-of-sail-world/tests -p 'test_*.py'
```

`bash automation/run_checks.sh` is the full gate, including Wurst execution. Scenario packaging goes through `package_wurst_map.py` or `tooling/package_release.sh`, which generates sources before Grill runs. `grill install` rewrites `wurst.build` and can add `.vscode/`. Restore those files when the formatting change is unintentional. The execution helper reserves an 8 GiB Java heap for the complete suite. A caller `-Xmx` in `JAVA_TOOL_OPTIONS` overrides that reservation.
