# Issue 463: Complete typed research entitlements

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
  --execution-dir _build/issue463-verified-map/execution \
  --output reports/issue-463/scoped-evidence.json
```

The verifier checks all compiled definitions, registration order, prerequisite
edges, exact costs and typed unlocks, plus negative controls for dropped records
and lost kinds. It verifies four scoped command receipts inside successful
pinned tests and preserves the broader release blockers.
