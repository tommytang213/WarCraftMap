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
