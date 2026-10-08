# Issue #412: select and restore saved physical maps

Registered `/saves` actions identify existing manual saves, all 15 autosaves and
both recovery checkpoints. `/load N` remains the manual shorthand; explicit
manual/autosave selectors, checkpoint names and `/load retry` use the production
command registry. Decimal parsing checks digits and overflow before any native
integer conversion. Malformed arguments cannot select or overwrite another slot.

Same-map restoration retains `CampaignSaveManager.load`. Cross-map restoration
preflights the envelope, supported schema, slot metadata, authored scenario
identity and generated destination, then atomically stores a separate v1 recovery
request containing the untouched selected envelope. Loader paths come from each
consumer's physical-map manifest, including regional maps without origins.

Destination startup waits for registrations, stages through the existing atomic
manager, writes consumption, and then publishes activation. Failed projection or
acknowledgement rolls back and retains a retry. A consumed record remains a basis
for reconstruction if the process stopped between acknowledgement and activation.
Repeated startup/retry in an activated instance has no additional effect.
Recovery preserves source slots and existing checkpoints, restores party locations
and campaign authority, and never invokes new-campaign grants. Subsequent origin
selection and boundary travel supersede the old request. A recovered campaign also
continues to supersede an interrupted origin request after later travel.

Campaign envelope schemas 1–7 and their migrations remain supported. The new
request contract is versioned independently; absence retains existing startup.
An existing codec fixture using a private slot ID remains supported, while public
player slots validate kind/index metadata. The player guide, support metadata,
contract documentation and REQ-0185.01 / REQ-0186.01 / REQ-0190.01 mappings describe
this scope.

`CampaignRecoveryTests.wurst` drives production command registration, selection,
destination registrations, startup, codecs and transactions through recording
storage, physical-loader and projection boundaries. It covers every slot kind,
all 15 autosaves, cross-map authority/coordinates, schemas 1–7, an old boundary
arrival, rejected inputs, failed request writes, failed reconstruction,
acknowledgement interruption, repeated retry, and later travel/origin selection.
Receipts are emitted only after the mapped assertions. The final artifact audit
binds those receipts to the executed source and compiled diagnostic campaign.
All three scoped requirements pass against the 17-map artifact. The remaining
9,132 traceability blockers still prevent publication; they enumerate evidence
gaps across the wider inventory, not distinct gameplay defects.

`validation.json` records final commands, results, source identity and artifact
hashes. All 308 pinned Wurst tests passed. The 916-test Python scenario run had
one stale-report error: the compatibility manifest and execution-contract hashes
in the release-blocker snapshot needed refreshing. After refreshing those two
hashes, all nine tests in the affected module passed. The blocked release status
and findings were unchanged. The first complete development run passed 295/297 tests and exposed a
native integer-conversion exception plus the private-slot codec fixture; both
were corrected before final validation. Incomplete earlier builds are development
logs, not acceptance evidence.

Validation uses the pinned Wurst image, a read-only source mount and copies in
container-private `/tmp`, building as `wurstuser`. No worktree permission changes,
commits, pushes, GitHub writes, services or global tooling changes were made.
The native-save reconstruction oracle runs headlessly; the native client runner
is unavailable. The separate automation worker suite has existing GitHub-context
fixture errors, retained in its log. No player QA was requested or performed.
Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
