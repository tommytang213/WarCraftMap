# Issue #450: combat-earned military tradition

The installed death callback now awards controller/category experience from
committed military losses using authored contribution weights and integer-floor
rounding. Player progression is independent of allegiance and AI progression.
Military v7 preserves experience with consumed force records, migrates v1–v6,
and rejects malformed current tracks before replacing authority or projections.
The headless tradition state is v2 with a migration for missing player tracks.

See [LIVE_COMBAT_TRADITION.md](../../docs/LIVE_COMBAT_TRADITION.md) for the exact
eligibility, transaction, replay and migration contract. Authored coefficient,
milestone and non-kill contribution adapters remain unfinished. The generated
HP placeholder is disabled instead of treating the authored attack/discipline
coefficients as health bonuses.

The integration repair retains the combat-tradition mappings and incoming
hero-growth mappings. Soak fixture version **2** incorporates the authored
player-controller track. [soak-fixture-refresh.json](soak-fixture-refresh.json)
proves every previous seed hash still matches when the old eligibility list is
restored: only the fixture hash and source record count change, with identical
simulated outcomes. Both profiles retain strict expected hashes.
[full-world-soak.json](full-world-soak.json) records all four seeds passing
normal, accelerated and checkpoint-resumed execution.

Validation uses the pinned compiler extracted from the cached immutable Wurst
image into ignored worktree storage. Extraction used an offline temporary
container with no worktree mounts. Java, Grill, caches and the cached standard
library are local to this worktree; no services or global tooling were changed.
The complete campaign build executes the unfiltered Wurst suite, typechecks
and builds all physical maps. Framework validation builds original and mutated
independent consumers without changing shared sources.

The merged-source pinned suite passed **418/418 tests**. The **215 targeted
Python checks** passed, including the previously failing soak tests and the
release-audit regression tests. Original and mutated framework consumers each
passed **2/2 tests** and a **three-map campaign build**; all **171 shared source
hashes** match that evidence. The diagnostic Age of Sail campaign built all
**17 physical maps** with the pinned compiler.

The retained [validation.json](validation.json), execution transcripts and
[scoped-evidence.json](scoped-evidence.json)
record the results. Scoped evidence checks the actual compiled callback/commit
calls, scenario weights in every regional map, executed production receipts,
a weighted headless oracle comparison, and exact source-tree/base-revision
identity. The generated campaign remains in ignored `_build/release` storage.

Recheck the evidence against the same diagnostic artifact:

```sh
python3 reports/issue-450/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/wurst-tests \
  --output-dir _build/issue450-evidence
```

The scoped artifact audit passes earned experience and persistence under
ROAD-0052.01, REQ-0154.01 and REQ-0164.01. Other contribution adapters, live
coefficients, qualitative milestone effects and broad system dependencies
remain explicit publication blockers. Source-only traceability reports retain
unexecuted obligations as blocked. These checks do not change
`blocked_pending_real_forsaken_kingdom_launch_smoke`, establish native Warcraft
launch success, or designate a release candidate. No player QA, commit, push,
issue/PR action or publication is part of this work. The outer worker performs
its authoritative repository validation.
