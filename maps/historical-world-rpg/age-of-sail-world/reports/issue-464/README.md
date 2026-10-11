# Issue #464: exact military tradition resolution

Generated traditions retain every authored coefficient and milestone, including
signed rational coefficients, exact thresholds and replacement references. The
shared resolver derives reduced rational values from expandable XP, orders reached
milestones by threshold, and removes only explicitly replaced effects. Milestone
crossings leave continuous progression intact.

Eligible represented forces receive a replaceable typed layer from their current
controller/category. XP changes, transfers, activation and reconstruction replace
that layer; retirement and loss remove it. Abstract forces derive the same values
for inspection. Earned XP stays with its controller. Native representation and load
checkpoints retain their own layer stores without changing unrelated modifiers.

Military v8 continues to save XP and consumed-loss authority, with supported v1–v7
migrations. Derived modifiers and milestones are reconstructed from current
definitions and are never serialized. Failed campaign loads restore authority,
original representations and their original layers together.

See [LIVE_COMBAT_TRADITION.md](../../docs/LIVE_COMBAT_TRADITION.md) for the runtime
contract. Attribute and named-effect gameplay consumers remain explicit blockers.
There is no placeholder health bonus, invented native ability mapping, progression
ceiling or floating-point conversion of authoritative values.

The focused Wurst journeys exercise installed combat callbacks for player/AI
controllers and land/naval categories. `resolution_oracle.py` compares the delivered
layers with the headless Fraction resolver at adjacent XP values, every authored
threshold and very large totals. Separate vectors cover negative and expandable
coefficients/denominators. Lifecycle tests cover transfers, inactive forces,
replacement representations, unrelated effects, repeated reconciliation, legacy
saves and failed restoration.

The complete pinned suite passes **463/463 tests** and explicit typecheck. All
**168 targeted Python checks** pass after refreshing the generated release-audit
input hash and rechecking its freshness test. Original and content-mutated
framework consumers each pass **2/2 tests** and build **three-map campaigns**,
with all **179 shared source hashes** unchanged. The rational oracle matches
**40 delivered layers** and **nine arithmetic vectors** from the complete run.
The final **60 traceability/evidence rechecks** pass. The diagnostic campaign
builds **17 maps**, and its scoped audit verifies executable definitions in all
**16 regional maps** against the same source identity as the final execution.

The complete pinned execution, framework conformance and diagnostic campaign
results are recorded in `validation.json`. `scoped-evidence.json` binds executed
production journeys and compiled definitions in every regional map to the same
source-tree digest and base revision. Generated map/campaign binaries stay in
ignored `_build` storage. Source-only traceability deliberately retains unexecuted
obligations as blocked.

Rebuild using the cached worktree-local toolchain (no container required):

```sh
mkdir -p _build/issue464-tmp
export TMPDIR="$PWD/_build/issue464-tmp"
python3 ../_shared/tooling/run_wurst_tests.py package.json \
  --grill "$PWD/_build/issue464-tools/bin/grill"
python3 reports/issue-458/build-diagnostic.py \
  --grill "$PWD/_build/issue464-tools/bin/grill" \
  --execution-dir _build/wurst-tests
python3 reports/issue-464/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/wurst-tests \
  --output-dir _build/issue464-evidence
```

These are automated development checks, not native Warcraft launch evidence or a
release-candidate designation. `blocked_pending_real_forsaken_kingdom_launch_smoke`
remains unchanged. No player QA, commit, push, issue/PR action or publication is
part of this work. The outer worker performs authoritative repository validation.
