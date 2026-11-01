# Issue #587: Combined-arms Columns and PR #594 CI repair

The scenario-authored 500 bp Columns source uses the existing exact defense
bucket and military order authority. Its registered-research, installed native
callback and abstract comparisons cover 105 → 100 versus 105 controls, current
equipment/composition, support roles, supply, shared orders, connected terrain,
inclusive 768-unit distance, hostile weapon authentication, source stacking,
controller/region parity, reconstruction, migration and failed-load rollback.
Research costs, starting forces and saved formats remain unchanged.

PR #594's [artifact job](https://github.com/tommytang213/WarCraftMap/actions/runs/41286601549/job/124789059226)
passed all 810 interpreter tests but rejected the compiled Europe West Lua size.
The separate Wurst/framework, world-contract and stress workflows passed.
Fresh local compilation reproduced the base-map excess at 16,797,241 bytes.

The repair emits bounded loops for consecutive identical terrain rows in the
shared party and recovery generators. Every component label and row is retained;
no runtime navigation, combat, save or acceptance rule changes. The independent
geography check expands executable initialization for every physical map and all
movement classes and compares every row with the authoritative packaged raster.

Fresh pinned compilation produces 16,629,197-byte base-map Lua, saving 168,044
bytes. The actual materialized Europe West archive contains 16,632,204-byte Lua,
145,012 bytes below the unchanged 16 MiB budget. Normal compiled-script acceptance,
archive inspection and packaged land/recovery/pathing verification pass.

The local pinned typecheck and 43/43 interpreter cases pass, including all land
comparisons, installed Columns/Bayonet callbacks, save/load rollback, military
orders, boundary arrival, live recovery and framework registration. Probe
verification checks the Columns comparison's weapon, composition, support and final
resolution probes and the installed callback's complete required probe set.
`ci-repair-validation.json`, the compressed raw transcript and the three Lua
reports retain the measured results. This is focused evidence, not a full-suite
execution bundle or native-client acceptance claim.

Python validation covers land compilation/binding evidence (15 cases), combat
and research generation (24), raster/pathing (2), boundary arrival (8), and
framework conformance (9): **58 cases pass**. The shared framework boundary,
world contract, canonical map source and traceability freshness checks pass.
The framework Python transcript includes synthetic compiler/execution fixtures;
their printed 810-case summaries are orchestration checks, not real Wurst runs.

Validation used the pinned compiler/image recorded in the JSON, with networking
disabled, UID/GID 1001 and read-only mounts. Each compiler wrote only to its
container-private `/tmp`; the host copied out completed artifacts for inspection.
No player QA, commit, push, GitHub mutation or global tooling change was performed.

All three tracked audits were regenerated for current authored sources and retain
their unresolved findings. The outer worker must run complete repository and
framework validation. After merge, regenerate release-blocker, runtime-acceptance
and requirement-traceability audits on integrated main with that revision's full
verified execution bundle. A merged PR or this focused evidence cannot close the
Columns finding.
