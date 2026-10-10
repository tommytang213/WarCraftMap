# Issue #444: Live recruited-hero defeat and recovery

REQ-0096.01 connects the installed native death listener, recruited character
authority, scenario-owned recovery timing and production campaign clock. The
existing save fields retain wounded deadlines and party locations with no living
field member. Recovery returns the same character to reserve without replaying
starting profiles, rewards, equipment or recruitment. See
[the runtime contract](../../docs/HERO_DEFEAT_RECOVERY.md).

The regression journeys exercise production registration/startup and recording
native boundaries, including duplicate/stale callbacks, teardown during
reconstruction, rejected mixed-party restoration, all-wounded parties,
mid-recovery saves into fresh services, pauses, date jumps, inspection and
idempotent equipment effects. A separate interpreter-unit journey uses the
ordinary Warcraft party and recovery adapters to verify registration retirement.
The progression oracle checks the shared deadline/state contract; generator
checks bind the duration to scenario data.

Validation on the uncommitted source tree at base
`f7655a7dc64de470cc0a8734039ea5bc8b787cb6` passed 371/371 pinned Wurst tests
and 132 Python checks covering progression, recruitment, clocks, party locations,
persistence, traceability, framework boundaries and packaging. The pinned
compiler SHA-256 is
`1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.
All 17 physical maps built, and the scoped artifact verifier passed across the
16 regional maps with four executed lifecycle receipts. The Python framework
and packaging checks use synthetic compiler fixtures; the campaign build uses
the real pinned compiler. Both original and content-mutated framework campaigns
passed 2/2 Wurst tests and built three maps each, with all 167 shared source files
unchanged between variants.

Retained evidence includes `pinned-results.json.gz`,
`pinned-execution.log.gz`, `python-checks.log.gz`, `scoped-evidence.json` and
the compressed full artifact traceability report. `validation.json` records the
complete result and `framework-conformance.json` records the independent consumer
builds. The source-tree digest in
these reports binds the uncommitted implementation independently of its base
revision. The generated campaign stays in the ignored `_build/release` directory.

Validate the scoped artifact after the pinned campaign build:

```sh
python3 reports/issue-444/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/wurst-tests \
  --source-revision FULL_BASE_REVISION \
  --output-dir _build/issue444-evidence
```

The verifier requires four executed production receipts, exact source-tree and
base-revision identity, compiled live call paths, and the authored recovery
policy in every regional map. Source reports retain unexecuted obligations as
blocked; broader hero office/progression requirements are outside this scope.
This diagnostic does not change
`blocked_pending_real_forsaken_kingdom_launch_smoke` and is not a release candidate.
The repository-wide release audit still reports 21 existing campaign blockers;
the full artifact traceability audit retains 8,716 publication blockers outside
the completed issue scope.

Container validation mounts the worktree read-only and builds a private copy as
`wurstuser`. No commits, publication, global tooling changes or player QA are part
of this work. The disposable validation container was removed after retaining
its results. `validate-container.sh` records its private-copy build commands.

## Integration with authored quest stages

The merge repair preserves the recovery policy and main's quest generation,
including both quest traceability mappings. The lifecycle test fixture now
completes the authored stage graph before earning its initial reward, so its
existing save/load and reward checks also preserve RPG v5 quest history.
Hero conditions, deadlines and party-location fields retain their existing
representation and migration behavior.

`merge-validation.json` records validation of the integrated source tree;
`merge-scoped-evidence.json` binds the lifecycle receipts and packaged campaign
to that same tree. The `merge-` transcripts and compressed reports retain the
fresh execution and framework evidence separately from the original results.
The pinned compiler was extracted from the cached immutable image with no
network or worktree mounts, then run locally with a cached standard library.
No global tools or native-launch status changed. The outer worker performs the
authoritative repository validation.
