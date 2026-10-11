# Issue 463: Complete typed research entitlements

## PR #466 CI repair

The [failed campaign job](https://github.com/tommytang213/WarCraftMap/actions/runs/38129937454/job/114441987933)
completed both campaign builds and both 462-test Wurst executions, then exited 1
with `gate stage failed: release-blocker audit does not pass`. The 220 newly
accountable research consumers were reaching this generic failure before the
existing publication-blocked result. The [original log](ci-failure.log.gz) is
retained.

The packager now returns publication-blocked exit 3 only when the audit contains
exactly the complete current set of unbound research findings, with matching
validated runtime evidence and source identity. The audit remains failed with
`candidateReady: false`; every consumer remains release-blocking. CI retains its
JSON and Markdown alongside the final traceability diagnostics and publishes no
candidate ZIP. Missing, duplicate, altered or unrelated findings, stale sources,
invalid evidence and diagnostic-write failures still fail validation. Stale
candidate files and consumer diagnostics are removed before a new attempt.

Fresh validation at checkpoint `c119e280764655f7862559fa349793eb4dcc4249`, including
the dirty source digest recorded in [ci-validation.json](ci-validation.json):

- **209 targeted Python tests and 154 automation tests passed**, covering
  research, exact costs, generation, persistence, framework boundaries,
  packaging, release auditing, upload verification and the actual CI shell
  publication branches. Compiler fixtures in these Python tests are synthetic;
  their intentional failure output is not a failed validation run.
- **462/462 pinned Wurst tests passed**, plus typecheck, map assembly and archive
  inspection. The [scoped evidence](ci-scoped-evidence.json) includes 17 passing
  research/restoration tests and the success, failure, stale and replay receipts.
- [Compiled registrations](ci-compiled-research.json) retain all **206 nodes,
  264 prerequisite edges and 220 typed unlocks**, in order, including all 13
  multi-unlock nodes and the exact historical costs. Dropped-record and
  changed-kind negative controls are detected. The executable Lua is unchanged
  from the previous implementation and contains no food-cap fallback.
- Both framework campaigns passed **2/2 pinned Wurst tests** and built all three
  maps with unchanged shared sources. World contracts, map source, framework
  boundaries and source-traceability freshness checks also passed.

The cached pinned compiler, JRE and standard library ran locally. No container,
global tooling change, service installation, commit, push or GitHub write was
used. The full two-build Age of Sail CI campaign was not repeated locally; the
updated publication control flow was exercised with recording fixtures and the
actual consumer audit. The outer worker retains authoritative repository
validation. Native launch, all 220 gameplay consumers, and unrelated requirement
and dependency blockers remain unresolved. No player QA is requested.

Recheck this evidence against the retained build with:

```sh
python3 reports/issue-463/verify_evidence.py \
  --artifact _build/release/AgeOfSailWorld.w3x \
  --execution-dir _build/issue463-ci-map/execution \
  --output reports/issue-463/ci-scoped-evidence.json
```

## Earlier checkpoint validation

Revalidated checkpoint `0b08932584cdde5c0f7575417c041b73173bf26c` after the
worker's 14,400-second repository-check timeout. No implementation changes were
needed: the authoritative source digest and compiled Lua match the original
evidence below. The new [validation record](repair-validation.json),
[scoped evidence](repair-scoped-evidence.json), and
[compiled registrations](repair-compiled-research.json) use the current checkpoint.

All **996 scenario Python tests**, **154 automation tests**, and **462 pinned
Wurst tests** passed. Typecheck, map assembly, archive inspection, and both
three-map framework campaigns also passed. The local repository preflight had a
900-second limit and stopped after 291 successful Python tests; the unchanged
discovery resumed at the interrupted test and passed all remaining 705. The
compressed transcripts, per-test results, and continuation runner are retained.
Python packaging tests deliberately exercise synthetic compiler failures; the
real pinned compiler evidence is archived separately.

The full repository command remains the outer worker's authoritative next step.
The supplied timeout alone does not establish its cause. Native launch and all
220 missing gameplay consumers remain release blockers; this validation repair
changes only evidence in this directory. The original implementation validation
record follows.

Generator v27 retains all 220 authored unlocks across 206 research nodes,
including all 13 nodes with multiple unlocks. Each reference retains its node,
kind and content ID in authored order. `mass_army_logistics` delivers
`policy/mass_conscription`, `unit/common_wagon_train` and
`modifier/supply_efficiency`. Prerequisites and exact historical costs remain
unchanged. See [the entitlement contract](../../docs/RESEARCH_ENTITLEMENTS.md).

Successful registered research commands replace only the requesting controller's
research entitlement layer. Inspection shows earned identities and binding
status. Saved completion records reconstruct these layers without replaying
grants, charging again or changing unrelated modifiers. Durable save formats
remain unchanged. Malformed definitions and rejected loads preserve authority.

The production adapter is explicitly unbound. The former universal food-cap
bonus is removed; missing consumers now have 220 individual release blockers.
This evidence covers ROAD-0045.01 definition retention and entitlement delivery
only. Broader technology/institution integration, gameplay consumers and native
Warcraft launch remain blocked. No unrelated requirement or dependency blocker
is cleared.

The machine-readable [validation record](validation.json) and
[scoped evidence](scoped-evidence.json) bind results to the source revision and
dirty input digest. Compressed transcripts retain the complete execution output.
The Python transcript includes intentional failures from negative packaging and
compiler fixtures; its final unittest result is authoritative.

Final validation:

- **462/462 pinned Wurst tests passed**, including production research commands,
  all five unlock kinds, shared content provenance, exact charges, malformed
  definitions, separate controllers, supported saves and injected load failures.
  The production adapter test preserves food capacity through research,
  reconstruction and unrelated resource changes.
- **195 targeted Python tests and 154 automation tests passed**. Coverage includes
  research, generation, persistence, packaging, execution evidence, framework
  boundaries, release blockers and requirement traceability.
- The map passed pinned typecheck, compilation and archive inspection. Its
  executable Lua retains **206 nodes, 264 prerequisite edges and 220 unlocks**
  in order, including all 13 multi-unlock nodes, with exact cost coefficients.
  Dropped-record and changed-kind negative controls fail the comparison. The
  executable contains no food-cap fallback.
- Original and content-mutated framework campaigns each passed **2/2 pinned
  Wurst tests**, built all three maps and retained identical shared sources.
- Source traceability and release reports are current; `git diff --check` passes.
  The release audit intentionally retains **241 campaign blockers**, including
  220 missing research consumers. The broader traceability gate retains 7,054
  publication blockers and `candidateReady: false`.

The pinned compiler and bundled JRE were copied from the cached container image
into ignored worktree storage and executed locally with a cached standard
library at revision `1bd90397f6c034f19602127af2ab48d332d8fff9`. Compiler SHA-256 is
`1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.
No writable container mount, global tooling change, service install,
commit, push, GitHub write or player QA was used. Generated archives remain under
`_build`.

Recheck the scoped evidence after the full pinned suite and map build:

```sh
python3 reports/issue-463/verify_evidence.py \
  --artifact _build/release/AgeOfSailWorld.w3x \
  --execution-dir _build/issue463-repair-map/execution \
  --output reports/issue-463/repair-scoped-evidence.json
```

The verifier checks all compiled definitions, registration order, prerequisite
edges, exact costs and typed unlocks, plus negative controls for dropped records
and lost kinds. It verifies four scoped command receipts inside successful
pinned tests and preserves the broader release blockers.
