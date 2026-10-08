# Issue #413: live autosave reconstruction

Campaign schema 8 persists the next rolling slot and remaining unpaused seconds
through manual saves, autosaves, recovery checkpoints and physical-map transfers.
Snapshots sample elapsed native timer time without requesting another save. An
autosave serializes its post-commit scheduler state; the save manager publishes
that state only after a successful transactional write, including deferred
retries. Coalesced requests and callbacks from retired timers cannot complete a
second time. Failed and aborted loads retain the old scheduler and timer; committed
loads discard old autosave intent and reconstruct the restored deadline.

Schemas 1–7 remain supported. Omitted scheduler metadata defaults deterministically
to slot 1 and the configured interval. Explicit v0 last-completed-slot records
migrate to v1 next-slot records. Invalid, duplicate, negative and nonfinite timing
metadata rejects before authority changes. Binary real encoding retains fractional
seconds without native string-format rounding. The headless envelope migration
preserves existing metadata verbatim.

The production fixtures compare 18 consecutive autosaves with 18 fresh map-service
reconstructions, including slot 15 wraparound. They also exercise generated
registration and destination startup, manual/session/milestone restores, paused
and overdue snapshots, storage failure, deferred manager retries, coalescing,
failed-load rollback, staged abort, stale callbacks and repeated loads. Timer and
storage boundaries are deterministic; no wall-clock sleeps or player QA are used.

`validation.json` identifies the base revision, exact working source tree, pinned
compiler, execution transcript and diagnostic W3N. Compressed execution and Python
logs retain the verification results. The final traceability report binds
REQ-0184.01 and REQ-0187.01 to their production entry, state, persistence, test
receipts and compiled calls in all regional maps. The tracked source inventory
continues to report absent execution/artifact inputs when run on its own.

Validation used the pinned Wurst image with the worktree mounted read-only. Source
was copied to container-private storage for compilation. Generated W3X/W3N files
remain build outputs. The diagnostic campaign is not a player release. Unrelated
requirements and dependency coverage remain blocked, and real-client status stays
`blocked_pending_real_forsaken_kingdom_launch_smoke`. No retail Warcraft execution
or incremental player testing is claimed.

The integration repair preserves schema 8 alongside main's versioned recovery
request, and combines both branches' requirement mappings without changing any
mapping. The incoming help fixture scopes its six obligations explicitly, fixing
the previous total-mapping-count failure. Recovery fixtures compare against the
committed autosave state and assert rotation through slot 15. Autosave metadata
also uses main's bounded decimal parser; six additional malformed slot/exponent
records verify rejection before authority or timer changes.

The original `validation.json` and logs remain historical evidence. The repair
evidence is recorded separately in `repair-validation.json` and `repair-*` logs.
`verify-repair-evidence.py` checks the two autosave requirements together with the
three merged recovery and six help obligations against the rebuilt diagnostic
campaign. It verifies the current source identity, all 44 requirement receipts,
and retained publication blockers. It accepts explicit artifact, execution and
output directories for reviewing a build copied from a read-only source container.

The final repair run passed all 321 pinned Wurst tests, 923 scenario Python tests
and 129 automation tests. Both shared-framework campaign variants passed their
tests and builds with all 157 shared source hashes verified. All 17 physical maps
typechecked, compiled and passed archive inspection. The artifact-bound audit
passes all 11 scoped obligations and retains 9,074 publication blockers across
the wider inventory. No player QA or real-client execution is claimed.
