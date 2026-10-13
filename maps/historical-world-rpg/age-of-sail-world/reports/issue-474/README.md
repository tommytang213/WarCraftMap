# Issue #474: Pike and Shot defensive discipline

The prerequisite #469 is present in this checkout through merge `cea06c5` (PR
#477). Combat catalogue v2 binds the existing `(modifier, army_discipline)`
entitlement to `land_formation` recipients with a flat +500-bp discipline
rating. The source is `research:modifier:army_discipline`, deduplicated by typed
entitlement membership, including when multiple completed nodes deliver it.

Both shared consumers add the research rating to exact continuous discipline
and compatible named sources before the nonnegative defensive denominator.
Military authority supplies the current controller/category; neither a native
handle nor a firearm profile defines defensive eligibility. The installed
callback handles legal military/character combat while retaining weapon checks
for the separate offensive effects. Unknown recipients fail closed. Technology
and military inspection display source, magnitude, recipients and active status.

Campaign registration preserves the existing research adapter and all typed
entitlements. No research costs, prerequisites, era, roster availability, world
assignments, equipment, native abilities, food cap or campaign-save records are
changed. Derived ratings are never saved. Existing research reconstruction and
load rollback restore the same layer from completions; force/category changes,
new representations and abstract combat read current authority directly.

`validate.py` uses the repository's generator, assembly, pinned typecheck and
source-bound interpreter execution gate. The local toolchain was copied from
the immutable pinned image into ignored `_build/issue474-tools`; the standard
library uses the preceding validation's revision
`1bd90397f6c034f19602127af2ab48d332d8fff9`. No worktree was mounted writable into a
container, no global toolchain was modified, and no player testing was requested.

The focused suites cover completed versus incomplete research, typed/controller
separation, duplicate sources/delivery, continuous and nonnegative arithmetic,
ratings above 2^53, inactive maps, naval/character/unknown exclusions, recruitment,
reassignment, stale callbacks, save migration, late-load rollback and research/
military inspection. Existing milestone, research-cost and equipment suites
remain part of the checks. The catalogue's v1 migration preserves its original
weapon consumers without inventing research bindings.

The fresh release audit removes exactly
`RESEARCH-UNBOUND-PIKE-AND-SHOT-MODIFIER-ARMY-DISCIPLINE`. Its overall result remains
blocked by unrelated findings, including 219 research consumers. This work and
its automated checks provide **no native Warcraft launch evidence**; #438 remains
separate.

Validation retained in `validation.json` and compressed transcripts: the pinned
Wurst typecheck and **185/185** scoped interpreter tests pass. All **33** targeted
Python combat/research/tradition tests pass. The original and content-mutated
standalone framework campaigns also build successfully, with **2/2** pinned
interpreter tests each and unchanged shared framework sources.

The repository headless command ran **1,030** scenario tests. Its sole failure
was the publication regression's old expectation of 220 unbound consumers.
That test now expects 219, explicitly excludes Pike and Shot, and passes on a
targeted rerun; the other **1,029** tests passed in the complete run. All **162**
automation tests also pass. The complete scenario suite was not repeated after
that test-only correction; the outer worker runs the authoritative validation.
Framework/world/map-source checks and requirement-report freshness pass.

`headless-full.log.gz` retains the original run and `publication-recheck.log.gz`
retains the corrected test. Packaging tests in the Python suite use synthetic
compiler receipts; those lines are not additional pinned-Wurst execution
claims. Actual compiler evidence is in `wurst-results.json.gz` and
`wurst-execution.log.gz`, refreshed after the correction.
