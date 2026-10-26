# PR #536: integrate main 594d36c and retain the native boundary

The Austria → Victory → Continue failure remains unresolved. Native execution
of this candidate is `not_run`; terrain and a responsive player-controlled unit
have not been observed. Keep #536 draft/unmerged and #438 open.

## Source reconciliation

The remote task head was rechecked as
`a09fad8618c38513b40c876862844e63c8752b9f`; current main was
`594d36cfdcd1660753ea4cd743132a823443dcf3`. All three existing head workflows
completed successfully. GitHub reported conflicts and no submitted reviews or
inline review threads. No other local build, worker or Git lock was found.
Work is isolated in this chat's checkout; previous worktrees are retained.

Reuse the unpublished schema-20 reconciliation from `d7376a1` rather than
reimplementing it. The merged military parser retains all incoming main code,
including the later attack-cooldown adapter changes, and the previously reviewed
detached-parser delta. The courts campaign-day rejection disposes the detached
snapshot and returns `null`, matching the object-returning API. All eleven date
bounds and both v19 migration layouts remain. The ownership/date-bound regression
is byte-identical to `d7376a1`, including borrowed naval blueprint lifetime checks.

The historical independent source review is
`combined-source-review.json`, reviewer `/root/startup_review`, SHA-256
`d8503e30714d893ea52c0c91ea4487c664d56a040b5fdde6eb53a588ae2cff7c`.
It approved the schema-20 parser resolution and this exact test file. This is
reused historical review evidence, not a fresh review of the full 594d36c tree.
The test SHA-256 is
`430ffb8719ffc0129a00165e67c02a279ed9c772685a2cda907615b51bd4344b`.

Regenerate conflicted runtime, release and traceability reports from combined
source; do not choose either parent's stale report. The recorded source revision
is the precommit baseline label a09fad86. The combined authored-source digest is
`9742b0a76a1e91dbd3a5503e04c82c80c8e691360088031dfe91c0480810164b`.
Source-only reports retain 30 runtime failures, 238 release blockers and 7,004
traceability blockers. No release or native gate is waived.

## Destination startup and first callback

The retained compiled Europe evidence and current source show this path:

1. The selector commits a pending origin request, closes its UI (unpausing the
   game), and calls `ChangeLevel(packagePath, true)` through the compatibility
   adapter. Austria still targets root member `EuropeCentralEast.w3x`.
2. Destination `main` initializes globals and Blizzard before package
   initializers. `Bootstrap.initializeRegionalCampaign` registers domains and
   synchronously calls `campaign.startup()`.
3. A new start creates and validates authority, commits its sequence checkpoint,
   writes public session/milestone checkpoints, and acknowledges the request.
   Only successful startup enables campaign timers and gameplay commands.
4. The retained model's first timer callback is the Wurst `GameTimer` bridge at
   0.03 seconds. The military timer, campaign-day advancement and recovery
   sampling first run at one second. The model records completed callbacks,
   not native scheduling, rendering or control.

The retained model starts the destination directly with a synthetic pending
request and native doubles. It does not execute selector → ChangeLevel → Continue.
It cannot establish that the actual client reached destination `main`, returned
from initialization, or ran its first timer. No new model run is represented as
native evidence, and no arbitrary delay, timer reorder, startup skip or content
removal is applied.

The existing distinct destination script-isolation tool and earlier failed
identical-map substitution remain separate evidence. The latter does not prove
the real destination's startup was entered. The next decisive native observation
must distinguish destination entry, completed startup and callback execution on
one versioned, hash-bound, reviewed candidate. No incremental player retest is
requested by this integration.

## Validation scope

Required validation must run against the combined committed candidate with the
unchanged pinned compiler, dependency, test discovery, budgets and release gates.
The previous head's passing tests and synthetic timers are not substituted for
that run. Completion evidence is recorded separately after the gate terminates.
