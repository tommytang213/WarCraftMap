# Issue 367: Research registration and complete prerequisites

`/research ID` now reaches the production action handler. `/technology` and
`/institutions` open the read-only screen; `/unlock ID` and `/institution ID`
remain action aliases. RPG registration returns the first conflict, and the
production bootstrap checks that result before installing the registry.

Generator version 14 emits all 264 prerequisite edges from the scenario's
181 technologies and 25 institutions, preserving authored IDs and order.
`TechnologyRuntime.unlock()` checks every prerequisite against the requesting
controller before adding a completion or projecting its effect. The command
charges only a successful unlock. Tests exercise the production registry and
handlers with controlled campaign time, currency and output.

Research definitions are not persisted. RPG state schema 2, campaign envelope
schema 5, and existing `u,controller,id` completion records are unchanged, so no
save migration is required. Already earned completions remain valid even when
they were obtained under the former truncated prerequisite check.

Validation on base revision `484c62a8ef08248898f8e1f41e73638d608aac1a` with the
uncommitted implementation:

- Required `python3 ../_shared/tooling/run_wurst_tests.py package.json`:
  **84/84 passed**, including six new research tests. Subsequent `grill typecheck`
  passed. The pinned image was mounted with the worktree read-only; source,
  dependencies and build output lived in container-private storage.
- Research tests cover registry dispatch, read-only screens, name/alias
  collisions, neither/either/both prerequisites for generated `flintlock_drill`
  and `scientific_societies`, controller isolation, a third prerequisite,
  insufficient funds, unknown IDs, rejection atomicity, exact charging and
  effect application, duplicate requests, and resumed/uninterrupted equivalence.
  The live codec tests all supported envelope schemas 1–5 and retains legacy
  completions without retroactive prerequisite enforcement.
- **55 Python tests passed** across `test_technology_institutions`,
  `test_research_generation`, `test_campaign_save`, `test_campaign_save_manager`,
  `test_release_save_compatibility`, `test_wurst_execution`, and
  `test_runtime_acceptance`. Generation compares every authored prerequisite
  list and rejects a negative fixture retaining only each node's first edge.
- **35 packaging tests passed** via `test_*packaging.py`, including deterministic
  rebuilds. Their synthetic compiler protocol is packaging-test evidence;
  interpreter execution is established by the separate pinned suite above.
- World validation, canonical map-source validation and `git diff --check`
  passed.

Pinned compiler image:
`frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`.
Compiler JAR SHA-256:
`1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.
Passing Wurst input-set SHA-256:
`1db47535125e0e70798b5a71a442a6f1f09528d79ad68d824e7c4347c8318b90`.
The execution evidence was verified with `wurst_execution.verify_evidence`, and
every authored Wurst source hash was compared with the tested input manifest.
Local transcripts and results are under the worktree's `_build/issue-367/`.

These automated results do not establish a Warcraft client launch or gameplay
smoke result. Release status remains
**`blocked_pending_real_forsaken_kingdom_launch_smoke`**. No player QA was requested.
