# Issue #548 development evidence

The release audit now recognizes only the two supplied civic-policy and medicine
entitlements when complete, current-source pinned execution proves their real
production paths and outcomes. Missing, failed, incomplete, stale, tampered or
disconnected evidence retains the findings. The synthetic audit protocol tests
verify that valid evidence removes exactly those two findings; they are never
published as gameplay execution evidence.

The production repair requires a serving administrator with the district's
jurisdiction and positive capacity. Foreign or unavailable offices cannot enact
civic actions or supply lawful local benefits. The local diffusion mutation has
an instrumentable outcome boundary. Scenario-owned coefficients, persistent
fields and migrations remain unchanged.

`validation.json` and the compressed transcripts record final-source checks:
43 focused pinned Wurst tests, plus three original and three content-mutated
standalone framework tests, plus 146 affected Python tests. The civic cases compare actual local diffusion,
manpower, government treasury and commodity stock through registered research,
registered actions and campaign-clock replay. They cover optional enactment,
90-day transition, funded operation and failed renewal, eligible centers,
medical supply failures, missing research, jurisdiction, duplicates, 90-day
response and cooldown, shared purchase/sale budgets, active/abstract and player/AI
parity, capture during response, migrations, repeated loads and late rollback.
The focused evidence format cannot satisfy the full-suite release verifier.

`regional-payloads.json` inspects all 17 generated physical-map payloads and 794
civic districts. `packaged-registration.json` inspects a freshly compiled,
uninstrumented shipping W3X, including its archived Lua and runtime payload.
Both exact typed research effects, their approved coefficients, command/clock
paths, actual resource consumers and both trade commits survive packaging.
This single map inspection does not substitute for a full localized campaign.

The three official source reports were regenerated at the recorded revision and
dirty source identity. They remain release-blocked: 238 release findings and
7,004 traceability publication blockers, including the two supplied findings
without complete integration evidence. Unrelated failures remain visible.
The controller must run repository validation and regenerate release-blocker,
runtime-acceptance and requirement-traceability reports using fresh full-suite
execution and packaged campaign evidence on the integrated main revision.

To reproduce, run from the scenario directory:

```sh
python3 reports/issue-548/prepare-focused.py PATH_TO_CACHED_UPSTREAM_WURST_STDLIB
python3 reports/issue-548/prepare-framework.py PATH_TO_CACHED_UPSTREAM_WURST_STDLIB
```

Run each prepared `compile` directory in
`frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`,
with networking disabled and the source mounted read-only. The image's default
user is UID/GID 1001. Copy the source into container-private `/tmp` before running:

```sh
sha256sum /home/wurstuser/.wurst/wurst-compiler/wurstscript.jar
sha256sum -c inputs.sha256
grill typecheck
grill test
sha256sum -c inputs.sha256
```

Save stdout/stderr as `focused-wurst.log`, `framework-original.log` and
`framework-mutated.log` in this evidence directory. The cached library is an
upstream source dependency only; no predecessor implementation, compiler output
or execution report is used as evidence.

For shipping inspection run `prepare-shipping.py`, then run
`grill build map/AgeOfSailWorld.w3x` under the same isolation. Export only
`_build/AgeOfSailWorld.w3x` as a tar archive into
`_build/issue-548/shipping/map.tar`, retain stderr as `shipping-build.log`, then
run `inspect-packaged.py`. `inspect-payloads.py` inspects the localized generated
payloads. `record-focused.py` checks transcript results, both input-hash checks
and current source identity before retaining compressed evidence.

No player QA, commit, push, GitHub mutation or global tooling changes occurred.
All container writes stayed in private temporary storage; worktree mounts were
read-only. Python temporary fixtures stayed inside this worktree for the final
packaging and audit regression runs. Native client validation was not run.

## Integration repair after main merge

The six conflicted paths were resolved and staged without a commit. The civic
and dispatch verifiers both run in the release audit; configuration includes
both sets of source dependencies; and the execution contract preserves every
probe and system definition from both parents. No production coefficients,
persisted fields or migrations changed during conflict repair. A fresh dispatch
run exposed an outdated assertion: a local office with wrong jurisdiction or zero
capacity cannot finish an ordinary survey. The test now asserts cancellation,
cleared pending authority and no additional treasury charge for those cases;
relay-only limitations retain the 90-day fallback.
`integration-dispatch-before-repair.log.gz` retains that initial 5/6 result; the
combined final-source 49-test run validates the corrected assertion.

Fresh integration evidence uses the `integration-` prefix. The earlier files
above remain historical development evidence; no predecessor execution or
compiled artifact was used to validate this integration. The fresh focused
assembly and original/mutated framework assemblies were prepared by the scripts
above, using only cached upstream standard-library source. The pinned image ran
with networking disabled, UID/GID 1001, read-only source mounts and private
container `/tmp` builds. Both before/after input-hash checks and the pinned
compiler hash were verified. `integration-focused-results.json` records the
49 passing focused tests (including the six dispatch cases) and observed civic
outcome calls;
`integration-framework-{original,mutated}-results.json` record three passing
tests each. These remain focused evidence and cannot close release findings.

`integration-regional-payloads.json` inspects all 17 fresh generated payloads;
`integration-packaged-registration.json` inspects a freshly built uninstrumented
shipping map and its archived registration/consumers. `integration-validation.json`
records the affected Python checks and final source identity. Compressed
`integration-*.log.gz` files retain their transcripts.

The three official audits were regenerated from the integrated source, and the
traceability freshness check passed. Without full-suite execution and a complete
packaged campaign, the source-only reports correctly retain 238 release blockers
and 7,004 traceability publication blockers, including the two supplied civic
findings. The controller must perform complete repository validation and refresh
all three audits on the new main revision after integration.

## PR #552 validation repair

The failed release job at revision `f2cd383` stopped in the second execution
shard: `charteredLongCampaignActiveAbstractCostsAndConstructionMatch` exceeded
the pinned interpreter's 20-second test deadline. It passed in isolation. The
construction replay was scanning every registered technology on every work day
to find a small authored prerequisite list. It now walks those exact IDs and
checks current unlock state directly. Unknown or malformed requirements reject;
revocation still cancels construction without granting a hull or refund.
The additional registered-action regression covers those cases. No coefficients,
persisted state, migrations, test deadlines or release evidence gates changed.

Fresh repair evidence uses the `ci-repair-` prefix. Focused pinned execution
includes the civic matched controls and late rollback, dispatch integration,
naval services and chartered actions. Original and content-mutated standalone
framework scenarios also run under the pinned compiler. Containers use UID/GID
1001, disabled networking, read-only source mounts and private `/tmp` builds.
These development runs remain distinct from complete release execution evidence.

`ci-repair-validation.json` records 152 passing affected Python tests, 42 passing
focused pinned Wurst tests, the passing second 100-test CI shard (including the
previously failing 25-year case), and three passing tests in each standalone
framework variant. The focused and CI-shard selections overlap. Both input-hash
checks passed around every pinned test run. The fresh generated inspection covers
all 17 physical-map payloads and 794 districts; the fresh shipping inspection
checks the uninstrumented archived Lua and runtime payload of one W3X. Compressed
transcripts and input/result manifests accompany these summaries.

All three source reports were regenerated for the repaired source identity.
They retain 238 release findings and 7,004 traceability publication blockers,
including the two supplied findings without full integration evidence. The outer
worker must run complete repository validation and regenerate these audits with
fresh full-suite execution and packaged campaign evidence after integration.
