# Fail-closed local focused replay

`focused_wurst_replay.py` is a new replay tool, not a correction to historical
runner files or their results. It never makes full execution-gate or native
Warcraft acceptance claims. Do not use its report as `wurst_execution` evidence.

Run from a clean committed checkout with an existing local Grill launcher,
pinned compiler jar and offline bootstrap `_build` directory containing
`common.j`, `blizzard.j` and `dependencies/wurstStdlib2`. All paths are explicit:

```sh
python maps/historical-world-rpg/_shared/tooling/focused_wurst_replay.py \
  --project maps/historical-world-rpg/age-of-sail-world \
  --revision FULL_40_CHARACTER_HEAD \
  --out /absolute/new/evidence-directory \
  --executable /absolute/grill --compiler /absolute/wurstscript.jar \
  --bootstrap /absolute/prepared/_build \
  --package QuestRewardTests --package AuthoredQuestTests --timeout 600
```

The project must belong to the same checkout as this runner, binding generator
and verifier imports to the labeled source tree. The output must be fresh and
outside the checkout. The runner uses production
assembly/generation and applies only the documented dependency URL case
normalization. Supply dependencies beforehand; the runner has no downloader or
installation step. Grill itself remains an external executable, so execute in
an appropriately offline environment if network isolation is required.

Source identity is captured before generation. Discovery, verifier input bytes,
all dependency files, compiler and launcher are frozen **before typecheck** and
checked after typecheck and each package. Source identity and clean exact HEAD
are also rechecked. This detects ordinary concurrent source/input drift, not an
adversarial change-and-revert between observations. Bootstrap provenance is not
verified: the report inventories the bytes actually supplied. JASS is included
in verifier inputs; stdlib is inventoried separately. Compiler identity must
match the repository-pinned digest both before execution and in each transcript.
This does not prove the launcher, Java runtime or dependencies came from a pinned
image, and does not assert Docker execution.

Requested packages must each have nonzero discovery. Any exit failure, timeout,
missing/malformed result, compiler mismatch or drift fails the replay and skips
remaining packages. `completed: true` requires all requested suites. Logs and
`results.json` survive execution failures; invalid output locations or an
existing evidence directory are rejected before writing. Reports are focused
local evidence only. No archived report or full-gate implementation is changed.
