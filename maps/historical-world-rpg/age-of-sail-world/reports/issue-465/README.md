# Issue #465 validation

The scoped report closes campaign treasure resolution and persistence only.
It retains the broader treasure gameplay, native-client and release blockers.
The source tree hash in the execution and package evidence identifies the
uncommitted implementation at the recorded repository revision.

Final validation:

- Pinned Wurst typecheck and **167/167** selected execution tests passed, including
  all 28 authored treasures at seeds 1, 4 and 42, startup/save/travel reconstruction,
  physical interactions, migration and rollback.
- The compiled diagnostic map contained all **28 treasures and 35 candidates**,
  matching the generated catalogue, and the runtime resolver was present in Lua.
- Original and content-mutated framework campaigns each passed their two Wurst
  execution tests and package inspection.
- **70** focused Python treasure, navigation, interaction, save, migration and
  framework tests passed. A final **19-test** soak/treasure run, deterministic
  campaign packaging test, and **49** traceability/report checks also passed.
- World validation, framework boundary audit and `git diff --check` passed.

Earlier broad runs exposed two obsolete Wurst legacy-fixture conversions,
metadata-dependent soak hashes, stale generated reports, and packaging source
changes during concurrent editing. These were corrected and their affected
checks rerun. The final evidence does not claim a new full-suite execution.

`validate.sh` runs in the cached, pinned Wurst image with the source and cached
dependencies mounted read-only. It copies inputs to container-private `/tmp`
before compiling. `TREASURE_TARGETED=1 TREASURE_PACKAGE=1` selects this scope;
the test-selection changes affect only that private copy. No native Warcraft
client was launched and no player QA was requested.

`report.py` verifies the compressed execution transcripts, current source hashes,
packaged catalogue result and framework evidence before regenerating
`scoped-traceability.json`. Reward delivery, clue-source adapters and
guard/hazard/encounter execution remain outside this closure.
