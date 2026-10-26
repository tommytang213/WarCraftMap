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

The merge regenerated conflicted runtime, release and traceability reports from
combined source. At merge commit `6652bdb`, their revision was the precommit
baseline label a09fad86 and their combined authored-source digest was
`9742b0a76a1e91dbd3a5503e04c82c80c8e691360088031dfe91c0480810164b`.
Source-only reports retain 30 runtime failures, 238 release blockers and 7,004
traceability blockers. No release or native gate is waived.

The full prior ChatGPT conversation was not retrieved. Partial handoff context,
committed diagnostics and retained workspace evidence were reused.

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

## Required-gate terrain repair

The first required-gate attempt reported an error in deterministic campaign
packaging and was stopped by the assistant before its traceback was available.
Its original receipt is retained with a separate stopped/no-pass reconciliation.
The same case then passed two complete 17-map builds in isolation, using the
test's synthetic compiler fixture.

The next canonical attempt retained immediate unittest tracebacks without
changing result accounting. It failed Europe terrain generation at **2,262.5 ms**
against the unchanged **1,500 ms** budget. The driver stopped only its owned
process group and recorded the terminal interruption. Neither attempt reached
the real Wurst stage. The first attempt's precise exception remains unknown;
the second establishes the generation-budget failure directly.

Profiling identified repeated cell-first polygon scans. The repair paints the
same ordered surface unions while excluding rows outside each polygon's Y
extent. It preserves the exact sample and crossing arithmetic, every X sample,
surface precedence and final chokepoint overrides. Version-2 terrain generation
and all time, cell, feature, output and compiler budgets remain unchanged.

Independent review rejected the initial proposal's X clipping: crossing
interpolation can round beyond a vertex's X extrema. Its concrete small-grid
counterexample is retained and covered by a new regression. The final row-only
implementation passes review and **44 focused terrain tests**. Its complete
canonical outputs are byte-identical to the baseline for all seven authored
terrain regions. Europe predicate calls fall from **226,040 to 73,600**; the
recorded local generation observation is **131.359 ms**. The legacy full-grid
negative control fails the work-reduction assertion without changing output.

This reduces build-generation work. It neither changes the generated terrain
bytes nor establishes native loading speed or a Continue repair.

The third canonical attempt, on committed `791ce7f`, still failed the unchanged
terrain budget: `GeneratedBoundaryArrivalTests.setUpClass` reported Europe at
**2,980.4 ms** against **1,500 ms**. The assistant stopped the owned process
group after preserving that traceback. Its terminal receipt records
`interrupted`, confirmed process cleanup and no passing full-gate result.
Again, the real Wurst stage was not reached. Printed Wurst counts inside Python
packaging fixtures are synthetic compiler output, not real Wurst execution.

A separate full source-generation observation completed all seven regions;
Europe took **231.293 ms wall / 231.287 ms CPU**, with one **0.205 ms** generation-0
collection. Read-only review found no leaked trace, timer patch or GC policy
change in predecessor tests. This does not explain the slower full-suite result.
No further generator, clock, GC, timing-budget or test-discovery change is made
without evidence. The failed full-suite result remains retained.

The refreshed source audits use precommit revision label `6652bdb` and authored
source SHA-256
`91996f8be9079d4e0c3a3c6dd84b7b96f04f119ff38714765804052f7750c450`.
Their runtime, release and traceability blocker counts remain 30, 238 and 7,004.

## Validation scope

The unchanged static checks and **215 automation tests passed** on clean
`791ce7f`, with authored source unchanged before/after. The full canonical local
gate has **not passed**. The existing PR workflows are the next independent
environment for complete project Python discovery, real Wurst execution,
original/mutated framework builds and full campaign acceptance. They retain the
pinned compiler, dependency, test discovery, budgets and release gates. Their
actual checkout SHA/tree and terminal logs must be checked before claiming a
pass; source revision association alone is insufficient.

[Retained pre-CI evidence](main-594d36c-validation/manifest.json) binds scoped
source reviews, focused terrain tests, byte comparisons, negative controls,
component checks and all three interrupted canonical attempts. It explicitly
records `canonicalLocalGate=interrupted_after_failure`, CI not yet started at
collection, and native `not_run`. It is neither a full-gate success receipt nor a
standalone replay bundle. Future CI results belong in the PR's current status;
the historical receipt is not overwritten. A green campaign workflow can still
mean diagnostics-only publication when release gates remain blocked.
