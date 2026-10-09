# Issue #434: Starting profiles at live recruitment

This bridges the existing composed character catalogue to the production
`/recruit`/`/hire` path under REQ-0093.01 and ROAD-0135. Generation compares every
applicable profile by stable identity and retains explicit defaults for other
scenario characters. Historical identities and balance formulas remain in the
scenario composer. Generator version 22 records the composition inputs.

First successful recruitment initializes level, skill/mastery ranks and personal
tree with zero residual live experience and zero unspent progression points.
Availability is checked against the authoritative clock before mutation. The
saved ownership flag guards replay. Inspection and existing level-dependent
consumers read the resulting live state. The unused alternate starting formula
was removed.

RPG schema v4 persists the new rank maps; campaign envelopes 1–8 remain supported.
Populated v2/v3 snapshots retain earned progression and receive empty absent rank
maps, with no retrospective grants. Unrecruited legacy heroes initialize on
their first successful recruitment. Invalid profiles/snapshots and failed load
reconstruction preserve prior authority. Production travel and repeated
reconstruction retain earned ranks, points and personal progression.

The automated evidence covers all 107 generated starts, early/late recruits with
different roles, live command registration, rejection and replay, inspection,
equipment requirements, subsequent experience awards, expired availability,
current/legacy saves, travel and failed restoration. Existing recruitment-window
tests remain intact. Legacy fixture encoders now emit actual v2 records rather
than relabeling v4 records.

After a pinned campaign build, verify the same-revision diagnostic artifact:

```sh
python3 reports/issue-434/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/wurst-tests \
  --source-revision FULL_BASE_REVISION \
  --output-dir _build/issue434-evidence
```

The verifier binds the dirty source-tree digest as well as the base revision,
checks four execution receipts, compares compiled starting fields to the
catalogue in every regional map, and checks compiled authority mutation and
command registration. `validation.json` records the completed checks; generated
archives remain in ignored build storage. Source traceability was regenerated.

The pinned toolchain runs as `wurstuser` with the worktree and cached dependencies
mounted **read-only**. Source is copied to container-private `/tmp` before any
build. No global tooling, services, commits, publication or GitHub writes are
part of this work. No player QA is requested.

This is scoped starting-profile evidence. ROAD-0135.01, broader hero growth and
multi-axis progression, local field-group performance and native Warcraft launch
remain unresolved. The diagnostic is **not a release candidate** and does not
change `blocked_pending_real_forsaken_kingdom_launch_smoke`.

The repository-validation repair refreshes only the release-blocker report's
`package.json` hash after the profile composer was added. The stale report made
the audit exit before emitting its JSON summary. The implementation is unchanged;
all 21 existing release blockers remain recorded. `repair-validation.json` and
the `repair-*.log.gz` transcripts record the local rechecks. The retained pinned
execution was verified against the unchanged source digest and its four scoped
receipts. A fresh compiler/build run is deferred to the outer worker because
Grill is absent and Docker socket access is denied in this Codex environment.
