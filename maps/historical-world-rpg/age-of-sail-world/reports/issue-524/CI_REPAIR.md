# Issue 524: PR 543 packaging repair

The existing Central Banking implementation is ready for outer repository
validation. This repair preserves its distinct institution policy and technology
consumers, scenario contracts, production treasury operations and v18 migrations.

Read-only inspection of `gh pr checks 543` and the failed job's transcript found
that all **671 interpreter cases passed** in CI. Candidate acceptance subsequently
rejected Europe West's compiled Lua for exceeding the **16,777,216-byte** limit.
The failed job is
https://github.com/tommytang213/WarCraftMap/actions/runs/39583962263/job/119168138103.

The shared source generator now marks `configureGeneratedSettlementAuthority`
as `@noinline`. Inlining the complete save reconciler expanded early-return
guards over 827 settlement records. Retaining a normal function call reduces the
pinned compiler's regional Lua from **16,808,306** to **16,327,732 bytes**:
**480,574 bytes removed**, with **449,484 bytes of headroom**. The existing size,
line, string, command-registration and production-call gates remain unchanged.
No compiler options, research prerequisites, costs, adoption rules or financial
benefits changed.

Fresh verification is bound to the source identity in `ci-repair-validation.json`:

- Pinned Wurst typecheck and **35/35 real interpreter cases passed**, including
  six banking cases, finance/logistics integration, legacy military migrations,
  research costs and framework conformance. The banking fixture independently
  executes registered research/adoption, paid policy activation and treasury
  lodgements without an exchange/remittance consumer. Exact rounding,
  conservation, stale/replayed quotes, unauthorized actors, missing facilities,
  insufficient funds, capture, reload, rollback and long-campaign active/abstract
  upkeep remain covered. `ci-repair-final-wurst.log.gz` and
  `ci-repair-inputs.json.gz` retain the transcript and compiler input hashes.
- **52 core Python cases passed**, covering research contracts, economy,
  multi-century invariants, framework conformance and evidence verification.
  **27 save/integration cases** and **35 runtime/generation regressions** passed.
  The final transcripts are `ci-repair-final-core.log`, `ci-repair-saves.log` and
  `ci-repair-audit-regressions.log`.
- **Two targeted packaging/provenance cases passed**, for compiler-option
  preservation and stale localized-manifest rejection, giving **116 passing
  Python cases** total. See `ci-repair-packaging-targeted.log`. An expanded full
  Python packaging sweep was stopped in favor of these focused checks after the
  real regional archive and all-map materialized-data checks passed. Full
  repository validation remains assigned to the outer worker.
- A real, fully materialized Europe West W3X passed normal archive inspection,
  physical-map inspection and runtime packaged-data checks, including the Lua
  budget. `ci-repair-packaged-map.json` records its SHA-256, binary measurements
  and static acceptance result. This is compiled artifact verification, not
  Warcraft client execution. The compiler transcript is
  `ci-repair-materialized-build.log.gz`.
- Framework content/implementation boundary, canonical map source validation,
  generated-data verification and requirement-report freshness passed.

The Python orchestration suites use synthetic compilers. Their printed
671-test summaries are fixtures, not additional real Wurst execution evidence.
Only the separately retained 35-case interpreter run is new local Wurst
execution evidence for this repair.

`prepare-regional.py PATH_TO_CACHED_WURST_STDLIB [PHYSICAL_MAP_ID]`, run from the
scenario directory, reproduces generation, localization, budget checks, normal
production assembly and materialization for one regional map. The existing
`prepare-integration.py PATH_TO_CACHED_WURST_STDLIB` reproduces the focused test
assembly. Validation used the pinned image
`frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`,
UID/GID 1001, networking disabled, and read-only assembly mounts. Each container
copied its inputs into private `/tmp/compile` before compiler writes. No container
wrote to the worktree or changed its ownership or permissions.

Official release-blocker, runtime-acceptance and requirement-traceability audits
were regenerated for the tested source identity. They remain fail-closed pending
complete-suite and packaged-campaign evidence; this focused repair makes no
blocker-closure claim. The outer worker must run authoritative repository
validation and regenerate closure audits again on the new main revision after
merge. No commit, push, GitHub mutation, global tooling change or player QA was
performed.
