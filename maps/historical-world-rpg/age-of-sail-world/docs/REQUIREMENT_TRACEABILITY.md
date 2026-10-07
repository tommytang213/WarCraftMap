# Requirement-to-production traceability

The requirement gate is independent of the older twenty-system runtime audit.
An earlier roadmap checkbox, source token, declared journey, successful internal
method test, or populated content file does not establish production integration.
The initial report deliberately blocks publication: it inventories the locked
design without claiming that its unverified mechanisms have been repaired.

## Authorities and stable identity

`DESIGN_LOCK.md` and `ROADMAP.md` carry invisible `<!-- req:REQ-0001 -->` /
`<!-- req:ROAD-0001 -->` anchors. `scenario/traceability/requirements.json` records
every bullet, nested bullet and prose paragraph, including exceptions, examples,
failure behavior, recovery rules and development requirements. This conservative
inventory includes descriptive authority paragraphs rather than risking their
silent omission. Checkboxes are historical planning metadata, not evidence.

There are initially 477 authority blocks and 643 obligation spans. Sentence and
semicolon clauses have separate child IDs (`REQ-0001.01`). Inline enumerations
remain verbatim in their containing obligation: satisfying one item in an
enumeration cannot satisfy that obligation. The concatenated spans must exactly
equal their authority block. Changed, missing, duplicate or untagged authority,
including a new sub-bullet, fails the inventory check. Parent IDs and wildcards
cannot be used as implementation mappings. The report includes the complete
text so reviewers can assess compound clauses and split them further as needed.

Keep IDs when relocating text. For an intentional design revision, update the
authority and ledger together; retain existing child IDs for unchanged
obligations and allocate new IDs for new obligations. Never renumber existing
requirements to make a report pass. Splitting an obligation requires explicit
mappings for all resulting children. Do not auto-generate passing mappings from
headings, parent systems or counts.

Each authority has a `mechanism`, `content` or `combination` classification and a
`runtime`, `content` or `development` kind. A combination requires both framework
and scenario evidence. Content cannot stand in for a missing reusable mechanism.
The engine in `_shared/tooling/requirement_traceability.py` has no campaign
catalogue names, geography or Age of Sail policy. A later campaign can retain
these mechanism IDs and supply its own content paths, adapter mappings, map
assignments, catalogue selectors and execution evidence.

## Mapping obligations

`scenario/traceability/mappings.json` maps individual child IDs. Missing mappings
are explicit blockers, not exclusions. An implementation mapping contains:

- `mechanism` and/or `content`: concrete source references, including a path,
  optional Wurst function `symbol`, and required source fragments in `contains`.
- `entry`: a stable entry ID, adapter kind, real production `registration`,
  ordered source `path` from registration to handler, and the adapter seam's
  `testInvocation`. The registered command/event, map start, timer, transition,
  combat callback, UI action or build entry must be identifiable.
- `state`: authoritative owner, mutation path, rejection behavior, player-visible
  outcome and source references. Warcraft handles are not state ownership.
- `persistence` and `transition`: explicit modes, reasons and concrete save,
  restore or reconstruction references. Read-only, build-only and session-only
  policies require an explanation and implementation evidence too. Persisted
  policies require separate `save` and `load` source references. Runtime
  obligations cannot substitute a build entry or build-only persistence policy.
- `tests`: individual success/failure cases, plus stale/replay cases for runtime
  requirements, with exact Wurst test IDs, assertions and adapter observations.
- `artifact`: required physical map IDs (`@regional` expands to all non-selector
  maps) and compiled call patterns for implementation and registration.

The starter help mappings document actual chat registration, routing, state and
presentation paths. Their existing tests construct local registries; they remain
**test-only**. No synthetic gate fixture is listed as production evidence.

Source checks are supplementary and function-scoped when possible. Compiled
checks inspect real call expressions, excluding declarations, comments and
diagnostic strings. These checks establish survival, not Lua control-flow
reachability or successful Warcraft client execution.
Catalogue identity patterns also recognize real ID-array assignments when the
pinned compiler inlines constructors; quoted lookalikes do not count.

## Executable evidence

The gate verifies the current pinned Wurst transcript and input hashes using the
existing execution verifier, including every discovered test and terminal
result. It rejects added, deleted or changed local/shared Wurst sources and
independently re-discovers current source tests. Shared packages are checked in
the flattened compiler namespace. Receipts must occur before the named test's
terminal result; output after suite completion cannot supply them. A mapping
to an internal method test cannot establish reachability.

A production adapter fixture must install/drive the same registration and entry
used by production, observe its effects, assert success or rejection, and check
save/transition behavior where relevant. After those assertions it emits a
single-line `TRACEABILITY` receipt using Wurst test output, for example:

```text
TRACEABILITY {"requirement":"REQ-0001.01","case":"success","entryPoint":"wc3-example-event","observed":["registration","adapter","validation","mutation","persistence","transition","outcome"]}
```

The mapping's `receipt` object must match output **inside that named successful
test**, with its own requirement, case and entry ID. A report field, copied
receipt from another test/requirement, static invocation token, or entire suite
`pass` flag cannot replace that observation. Rejection fixtures assert unchanged
authority as their mutation observation. Stateful paths observe persistence and
reconstruction; read-only/session-only exceptions stay explicit. The current
locked requirements with no such fixture remain blocked. Receipts are reviewed
test assertions, not a general proof of arbitrary source control flow; native
client smoke retains its separate evidence level.

The ledger also identifies 49 cross-system dependency edges, including
combat/capture, war/peace, trade/cargo, piracy/diplomacy, clock/events/recruitment,
travel/save, governance/defenders, modal pause, religion/context, roster/research,
office/loyalty, treasure/knowledge, rewards/allegiance, remote orders/location,
autosave/transition, discovery/country screens, replenishment/resources/time,
religion/population/events, capture/administration and piracy/trade pressure.
Each endpoint obligation also records its dependency IDs; removing an edge
without reviewing those obligations fails the inventory check. An edge requires
explicit endpoint mappings and its own executed success,
failure and replay evidence. Passing both isolated components is insufficient.

## Final packaged content and byte composition

`scenario/traceability/catalogues.json` independently selects authoritative
source records and their runtime representation. Sixty-nine release-required
catalogues cover settlements, polities, provinces, goods, markets, meaningful
military variants, heroes, items/sets, technology/institutions, authored/personal/
local quests, events, faiths/policies, regions, boundaries, routes, navigation,
treasures, merchants, progression, military state, initial research/adoption,
offices, relationships, timeline schedules, quest locations and recovery anchors.
Omitting a census definition named by the ledger blocks release.

The census opens the **final W3N**, enumerates every member with MPQ listfile
completeness checks, extracts its actual W3X bytes, then reads each embedded
`runtime/scenario-runtime.json` and `war3map.lua`. It never substitutes generated
source files, an intermediate map directory or a source-derived manifest for the
packaged records. It checks map identity and the exact embedded map set.
For catalogues registered directly in Lua (goods, markets and campaign quests),
`runtime.representation: compiled-identities` counts the literal stable IDs in
those calls/assignments instead of requiring an unused duplicate JSON list.
This is packaging evidence only and cannot satisfy a requirement's integration
or production reachability checks.

Counts are accompanied by stable-ID differences, duplicate detection and, for
untransformed catalogues, full record comparison. Local catalogues have explicit
map partitions. Deliberately localized/replicated catalogues can use a campaign
union; missing global records and unexpected records still block. Compiled
registration identity checks supplement JSON checks; absent compiled mappings
remain blockers, even when JSON counts agree. The gate does not add unused data
to packaging merely to inflate counts or claim framework integration.
Unexpected compiled registrations also block. A campaign-union distribution
cannot put a record outside its explicitly declared geographic partition.
Shared constructors declare `compiledCompanions` as explicit authoritative
selectors (with optional ID prefixes/suffixes), such as institutions sharing the
research constructor. They cannot exempt arbitrary unknown registrations.

Reports provide per-member hashes and stored/decoded byte totals for compiled Lua,
runtime data, terrain, pathing, objects, imported assets, campaign/map metadata,
embedded maps and other members. Exact archive bytes and SHA-256 are recorded.
Outer embedded-map bytes and nested decoded composition are separate views,
avoiding double counting or treating compression overhead as missing content.
File size is not a correctness gate.
Map composition remains visible when its runtime JSON is malformed or missing.

## Commands and release policy

From the scenario directory:

```sh
# Refresh the tracked source inventory, preserving all known publication gaps.
python3 tooling/requirement_traceability_audit.py --write --check

# Normal repository check: inventory integrity and report freshness, not RC readiness.
python3 tooling/requirement_traceability_audit.py --check

# Full final-artifact audit; exits nonzero for any remaining blocker.
python3 tooling/requirement_traceability_audit.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution _build/wurst-tests/results.json \
  --transcript _build/wurst-tests/execution.log \
  --source-revision "$(git rev-parse HEAD)" \
  --write --output _build/release/requirement-traceability
```

The tracked source report is `reports/traceability/requirements.{json,md}`. It
explicitly reports missing artifact evidence; it cannot authorize publication.
Keeping it separate from the older source-audit reports allows diagnostic
compilation to proceed so the final census can inspect actual compiled output.

Every candidate attempt regenerates source traceability. After the final build,
the RC packager regenerates the complete report with pinned execution evidence
and the exact final W3N. It writes `_build/release/requirement-traceability.*`
before checking readiness, retaining failure diagnostics. Any unmapped,
static-only, test-only, data-only, unreachable, unpersisted, artifact-missing,
dependency-uncovered or census-mismatched requirement blocks ZIP publication.
An old candidate ZIP is removed before a new attempt.
Source diagnostics survive compiler cleanup/failure, old final-artifact reports
are cleared, and a new ZIP reaches its publication path only after verification.
CI retains these reports in a separate diagnostics artifact even when the gate
rejects publication. The RC command exits **3** only after both builds, pinned
Wurst execution, determinism and packaged-runtime validation succeed and the
final report still contains publication blockers. CI records this as
`ready=false`, retains diagnostics, displays the publication block in its job
summary and skips every player ZIP/W3N publication step. Build failures, invalid
inventories, stale execution and other errors still fail CI (exit **1**); CLI
argument errors use exit **2**. Exit **0** from an RC build means a verified
candidate ZIP was produced, and only that result can enable the player upload.
No blocker is waived or converted to a pass.

A successful candidate includes the complete report as metadata. Before upload,
the verifier repeats the audit on the W3N extracted from that ZIP and requires
the embedded report to match the freshly computed result. Changing checksums or
editing a stored `pass` flag cannot bypass this gate. Standalone diagnostic W3X/
W3N builds remain available for repair and automated validation.

`test_requirement_traceability.py` uses small nested MPQ and synthetic
interpreter-protocol fixtures to test detection, not to claim gameplay execution.
It removes production registration, persistence, integration mapping and compiled
markers independently; checks parent/child isolation, authority drift, stale
execution, missing observations, content-only substitution, catalogue count/ID/
record differences, byte accounting, and both candidate/upload blocking.
It also rejects omitted or changed shared sources, reduced test discovery,
receipts printed after a test finishes, and a save-only persistence mapping.
