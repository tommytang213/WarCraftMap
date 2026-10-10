# Issue 445 — authored live quest stages

The generated and live quest path now retains all **304 quest graphs, 943 stages
and 943 objective identities**. Production acceptance checks prerequisites;
physical visits prove only explicitly bound active objectives. Legal branch
selection, terminal readiness, a separate physical return/turn-in and existing
reward deduplication prevent The Printed Compact from completing in Lisbon alone.
RPG v5 persists the selected path, objective evidence and consumed receipts, with
explicit v1–v4 migration that preserves terminal outcomes and previous rewards.

The implementation, adapter boundary, journal precision rules and save migration
matrix are documented in [LIVE_QUEST_STAGES.md](../../docs/LIVE_QUEST_STAGES.md).
Scenario binding data remains outside the shared engine. Missing domain adapters
are intentionally fail-closed: generated output enumerates **920 objective-level
integration blockers**. A recording receipt port exercises both Printed Compact
branches; this does not claim that live diplomatic recognition or archive deposits
have been integrated. Authored reward batches and local random quests remain
separate work.

`scoped-traceability.json` records the state-machine evidence for ROAD-0054.01 and
ROAD-0130.01. Their broad event/exploration/content obligations are not closed by
this repair. The regenerated inventory retains every unrelated publication
blocker. No release gate, native-client status, scenario story choice or campaign
schema support range has been weakened. No player testing is requested.

Validation commands and results are retained in `validation.json`. Wurst uses the
repository-pinned compiler copied from the cached immutable Docker image into the
ignored worktree build directory. Java, Grill and the standard library are local
to that directory; no global tools are changed. Docker extraction uses no worktree
mount. Interpreter checks and static archive inspection do not establish native
Warcraft launch/gameplay success. The outer worker still runs its authoritative
repository validation.

The initial clean build passed typechecking and **375/375 pinned Wurst tests**.
The original and content-renamed conformance campaigns each passed **2/2 tests**
and produced W3N archives without changes to shared framework sources. Quest,
journal, physical interaction, generation, persistence/save, packaging, framework
and traceability Python checks passed. Discovery patterns overlap; the validation
report lists their individual counts instead of inflating a combined total.

`compiled-quests.json` compares the actual W3X Lua registrations and embedded
runtime data against all authored graphs. Its embedded source identity matches the
tested source tree, including uncommitted implementation changes. Reproduce this
inspection from the campaign directory with:

```sh
python3 reports/issue-445/inspect_compiled.py _build/release/AgeOfSailWorld.w3x --output reports/issue-445/compiled-quests.json
```

The compressed result JSON and execution transcripts retain the compiler identity,
test membership, input hashes and original transcript hashes. Python packaging
tests use their existing fake compiler controls; the separate pinned Wurst run
and actual archive inspection supply the compiler evidence.

## Validation repair after merging main

The merge repair preserves both authored-quest mappings and all incoming
military-order mappings. The generated traceability reports retain the same
**7,162 unrelated blockers** as incoming main. No quest implementation or
release-gate policy changed.

The repository validation failure came from a stale `package.json` hash in
`reports/release-blocker-audit.json`. The audit correctly rejected that stale
snapshot before emitting its JSON summary. Regenerating the snapshot fixes the
freshness test; the audit still reports the expected 21 campaign blockers without
execution and artifact inputs. All nine release-blocker regression tests pass.

[repair-validation.json](repair-validation.json) records validation of the merged
tree, including pinned Wurst execution and typechecking, targeted Python checks,
the framework mutation check and actual compiled quest definitions.
[repair-scoped-traceability.json](repair-scoped-traceability.json) binds the quest
evidence and preserved blockers to that same source identity. The original
implementation evidence above remains available separately. The outer worker
performs the final repository validation; native-client and broader quest
integration blockers remain open.
