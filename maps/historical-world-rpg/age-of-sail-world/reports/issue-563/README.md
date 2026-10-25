# Issue #563: Socket Bayonet verification contract

The fourth land consumer is now recognized as exactly `bayonet_system` →
`modifier progression_bayonet_system` → `anti_cavalry_melee_defense`, at 800 bp.
The existing three land consumer gates remain. This repair extends verification
of the existing combat implementation; it changes no production combat arithmetic,
save schema, migration, earned XP, equipment, troops or historical starts.

The isolated registered-research comparison resolves incoming 108 to 100 versus
an unresearched 108 control, using actual compatible infantry roster equipment
and hostile cavalry melee. The installed weapon callback comparison independently
proves the same result. Tests cover equipment, weapon, era, prerequisite, hostility
and controller negatives, unsupported native metadata, duplicate deliveries and
research provenance, reconstruction, active/abstract parity, player/AI parity,
current save/load, legacy unknown equipment and late transactional rollback.
Independent tradition and equipment defense add before one exact rating division;
earned tradition XP remains unbounded.

Recognition requires complete passing pinned execution with the exact audited
revision, authored-source digest, compiler and interpreter inputs, and raw
transcript. Registered research, equipment qualification, attack authentication
and actual damage-resolution probes must occur in the required passing tests.
Focused execution cannot close the finding. Synthetic verifier transcripts test
protocol rejection and exact four-finding recognition; they are never gameplay
evidence. Missing callback probes or a wrong bayonet identity/coefficient preserve
the existing three recognition results and block bayonet recognition.

`focused-results.json`, `focused-wurst.log.gz` and `validation.json` retain fresh
local development evidence. The focused preparation assembles current authored
sources and generated registrations, instruments only the disposable interpreter
assembly, checks the pinned compiler and hashes its source inputs before and after
execution. No predecessor CI, results, map or execution bundle is reused. Upstream
stdlib is a cached source dependency.

The three tracked audits were refreshed through `planning_audit.regenerate`, the
same #560 ingestion path used by the controller. Without complete integrated
execution, they retain all 238 release findings (including the exact bayonet
finding), 30 runtime failures and 7,004 traceability publication blockers. The
planner now includes bayonet in its consumer comparison observations. No unrelated
blocker is suppressed and no native-client acceptance is claimed.

After integration, the controller must execute its complete repository validation
on the new main revision, stage that revision's full execution through
`_shared/tooling/execution_transport.py`, and regenerate release-blocker,
runtime-acceptance and requirement-traceability audits using that verified bundle
via `tooling/planning_audit.py --source-revision NEW_MAIN --evidence-directory BUNDLE`.
The exact bayonet finding must disappear through verified comparisons. A merged
PR, closed issue or these focused results cannot establish integrated closure.
Release/launch promotion still requires fresh zero-blocker closure and closed
repair issues. Full repository validation is reserved for the controller after
integration preflight.

From the repository root, prepare the focused sources with:

```sh
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-563/prepare-focused.py
```

Use the pinned image in `focused-results.json`, UID/GID 1001, networking disabled,
the prepared `_build/issue-563` directory mounted read-only at `/source`, and cached
upstream stdlib source mounted read-only at `/stdlib`. Run `/bin/sh /source/run.sh`;
it copies source into container-private `/tmp/compile` and builds there. Save the
transcript as scenario `_build/issue-563/focused-wurst.log`. Never mount this
worktree writable into a container or change its permissions from a container.
`record-focused.py` checks the completed local evidence and retains the focused
results and automated check logs.

Development iterations corrected a native-type variable-name collision, supplied
the installed fixture's actual authored research prerequisites, and bounded its
late-era calendar setup with a valid checkpoint and matching agricultural
deadlines instead of simulating centuries of unrelated production. Initial audit freshness failures were repaired by
regenerating reports. The retained final transcripts record the final checks.
No player QA, GitHub mutation, commit, push or global tooling change was performed.
