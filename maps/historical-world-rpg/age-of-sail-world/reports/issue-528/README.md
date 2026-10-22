# Issue #528 focused verification

Ciphered Dispatches now consumes its exact modifier entitlement in the existing
paid cadastral-survey instruction/return operation. The scenario contract,
network, conditions, arithmetic and production entry point are documented in
[Ciphered Dispatches](../../docs/CIPHERED_DISPATCHES.md). A qualified remote survey
finishes on day 81 instead of day 90, paying an additional 0.25% of normal annual
tax. No municipal enactment or Archives effect is involved. Courier Relays and
the historical research cost curve are unchanged.

**30/30 real pinned Wurst interpreter tests passed**, after full assembled-source
typechecking. These include six Dispatch cases, all 14 CivicGovernance cases,
research costs, remote-region command authority and shared framework conformance.
`focused-results.json` lists each passing case and observed production probes;
`focused-wurst.log.gz` retains the transcript, and `focused-inputs.json.gz` records
exact assembly hashes. The compiler JAR hash is
`1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.

The new cases exercise registered research and `/civic survey`, matched controls,
exact bills and historical costs, absent relay/research/access, unpaid bills,
invalid jurisdiction/residence/capacity, foreign/unknown commands, unknown-region
knowledge, duplicate actions and named sources, lost eligibility, successor
controllers, active/abstract replay, fresh reconstruction and pre-civic migration.
The live campaign save manager also rejects a candidate after military, RPG and
resource restoration, rolls back its pending survey and research layer, then
successfully loads completed and pending candidates without double payment.
No new save fields are introduced: the existing normal deadline and completed
flag reconstruct against current scenario definitions; military v20 and its
existing migrations remain compatible.

**54/54 Python tests passed** across dispatch contracts (6), civic generation (4),
administrative contracts (4), administration (6), research generation (11),
framework conformance (9), release audit regressions (10), and runtime/traceability
freshness (4). Framework Python fixtures print synthetic compiler batches; those
are orchestration checks, not additional real interpreter executions. The shared
content/implementation boundary audit also passes. `validation.json` records
counts and log hashes; compressed Python logs are retained here.

`generated-identities.json` inspects the current generated release assembly:
exact typed modifier, six directed authored links, bounded effect and completion
bill, and source/provenance hashes. The verifier rejects altered executable or
JSON registration even after hashes are resealed. This is generated-payload
inspection; shipping W3N/W3X inspection belongs to controller validation.

All three official release-blocker, runtime-acceptance and requirement-traceability
reports were regenerated for this revision and source tree. They intentionally
retain publication blockers without complete same-source execution and built
campaign evidence. `validation.json` records their current hashes/statuses.
The controller must run complete repository validation, inspect shipping archives
and regenerate closure audits again on integrated main. No predecessor branch,
CI result or compiled artifact was used as evidence for this implementation.

`prepare-focused.py CACHED_WURST_STDLIB_SOURCE` regenerates and assembles the
focused suite from current source. `run-focused.sh` expects that assembly mounted
at `/source` read-only, and copies it to container-private `/tmp/compile` before
any compiler write. Validation used the pinned cached image, UID/GID 1001 and
network disabled. `collect-focused.py TRANSCRIPT` verifies all expected results,
current input hashes and generated registration. No commit, push, GitHub mutation,
global installation, writable container mount or player QA was performed.

Integration repair regenerated and staged the three conflicting audit JSON files
from the combined dispatch and Chemical Classification sources. No source conflict
or implementation change was needed. The focused assembly was regenerated and all
30 pinned Wurst tests passed again, including full assembled-source typechecking
and generated registration inspection. `integration-validation.json` records this
combined source identity, the additional Python integration checks, and refreshed
audit hashes. The earlier `validation.json` describes the original pre-integration
run; the focused Wurst and generated-identity files now describe the combined tree.
