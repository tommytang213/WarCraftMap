# Issue 365: selector handoff and regional startup

Base revision: `484c62a8ef08248898f8e1f41e73638d608aac1a`. Results describe the
uncommitted implementation in the isolated issue worktree. Compiler input hashes
bind the executed code, including generated scenario records, to this snapshot.
No commit, push, issue/PR update or artifact upload was performed.

The minimal selector now uses the same versioned `CampaignHandoff` contract as
regional startup. Persistence precedes local identity commitment and the loader.
Failure leaves the origin selector usable. Pending requests take precedence over
older milestones and remain recoverable through a sequence-bound codec checkpoint
until publication and acknowledgement finish. A consumed request cannot re-run
new-campaign initialization or recursively load the destination.

`CampaignRegistration` is the shared production registration phase used by
Bootstrap and the executable regressions. RPG, military, trade, country, religion
and piracy definitions and ports precede reconstruction. Simulation, autosaves and
commands become available after successful startup. Party projection is a native
boundary with failure reporting. Generated starting positions reuse the map
materializer's settlement placement, including origins without a military object.
Transfers use the same materialized arrival point without requiring the prior
settlement to have a military object on the destination. Invalid saved origins
are rejected before reconstruction. The selector assembly retains only its six
transitive project source packages. Regional registration is absent from that
compile.

Transfer reconstruction preserves mutable authority and current allegiance.
Founded polities register before saved country resources are restored, and
reconciliation no longer resets an existing treasury. The campaign field reader
also preserves semicolons in supported trade store IDs. Campaign schemas 1–5 and
their encoding remain unchanged; registered migration defaults reconstruct older
transfers, and old selector cache fields migrate to handoff version 1.

The pinned Wurst interpreter passed **95/95 tests**, including **17 new startup
regressions**. [Per-test results](issue-365/execution.json) and the
[compressed transcript](issue-365/execution.log.gz) retain revision, compiler and
input hashes. Tests execute production registration, writer, consumer, travel and
codec code with recording storage/loader/projection ports. They cover generated
European, Asian and African origins, an abstract starting settlement, failed
selector/destination commits, malformed requests, physical-map mismatches,
interrupted acknowledgement, consumed requests, unrelated old milestones,
populated transfer authority, transfers from abstract settlements, unknown saved
origins and legacy migration. The lifecycle fixtures bound authority populations
after executing all generated registrations to respect the interpreter's
20-second per-test limit. Domain, lifecycle and codec implementations are unchanged
in these fixtures. Catalogue-wide generation and stress checks remain separate
gates.

[Validation summary](issue-365/validation.json) records repository, packaging and
artifact-verification outcomes and the changed-source hashes. Validation containers
mount the worktree read-only and copy sources into private `/tmp`; all builds and
ownership changes occur on that private copy. Compiled maps remain generated
validation artifacts.

The final repository run passed **792 scenario tests and 67 automation tests**,
plus source, world and geography validation. The host command explicitly skipped
its Wurst step because Grill is container-only; each of the two campaign builds
executed the complete **95-test Wurst suite** with the pinned compiler. The six
release-save compatibility tests also passed separately. No checks were waived in
the release packaging or artifact-verification gates.

The first artifact inspection exposed a compiler-inlining mismatch in the static
checker: `configureGeneratedReligion` was inlined into registration. The checker
now requires the actual faith-registration, character-faith and influence calls,
plus the player-facing religion entry point. A new regression rejects diagnostic
strings without those calls. All 17 compiled maps passed the corrected inspection.
The [initial failed gate](issue-365/initial-release-gate.json) and
[transcript](issue-365/release-candidate-initial.log.gz) are retained as historical
evidence; the validation summary records the final rerun separately.

The [final packaging run](issue-365/container-validation.json) passed both clean
campaign builds and the subsequent artifact verifier. The normalized campaign
contents match across builds. [Artifact inspection](issue-365/artifact-validation.json)
covers all 17 physical maps, 230 origins and 34 transitions. The
[verified ZIP](issue-365/ci-artifact.json) has SHA-256
`0fa4ef86cc96ed8b8c628ef799a85afbdf621c25b676ba89172af7c08f9d6578`.
It is retained as generated output under the worktree's
`_build/issue-365-validation/`, without publication or upload.

[Input comparison](issue-365/input-comparison.json) confirms that all production
inputs match the validated snapshot. Only this issue report changed while that
build was running; final validation evidence is recorded afterward. Regenerating
`ScenarioData.wurst` from the current authoritative data also reproduces the
executed compiler-input hash. Grill normalizes YAML ordering and the standard
library URL's case in its private copy of `wurst.build`; the source configuration
was not changed.

The native-save reconstruction oracle passed. Actual Warcraft execution reports
`runtime_unavailable`; no native launch, gameplay or native-save success is claimed.
Release status remains **`blocked_pending_real_forsaken_kingdom_launch_smoke`**.
These startup repairs do not establish the cause of the reported native crash.
