# Recovery support runbook

Use this deterministic, command-line sequence for a recovery report. It does not mutate the reported save.

1. Record the release identity and physical map, the requested slot stable ID, and the last successful transition. Preserve the original save bytes and compute a SHA-256 digest before analysis.
2. Validate stable IDs and authoritative references with `tests/test_world_integrity_recovery.py`. The integrity scanner emits `warcraftmap_world_recovery_report_v1`; retain its `authoritativeHash`, counts, and ordered `kind`, `domain`, and `stableId` diagnostics. Never substitute Warcraft handle IDs for stable IDs.
3. Classify the untouched save with `tests/test_release_save_compatibility.py` and `scenario/compatibility/release-save-v1.json`. Record the compatibility format `warcraftmap_release_save_compatibility_v1`, source schema, migration path, and bounded English status. A rejection must leave the active state and input bytes unchanged.
4. For a transfer or revisit, run `tests/test_cross_map_persistence.py` and `tests/test_regional_navigation.py`. Confirm the last committed checkpoint is unchanged after an interrupted transition, then reproduce destination reconstruction from the same authority and physical-map assignment.
5. For missing representations or integrity recovery, run `tests/test_world_integrity_recovery.py`. Compare authoritative hashes before and after reconstruction, check ownership/control separately, and require a clean post-recovery report. An interrupted adapter must roll back staged objects.
6. For native Warcraft save/load, run `tests/test_native_save_regression.py`; for rolling and checkpoint saves, run `tests/test_autosave_scheduler.py`, `tests/test_campaign_save.py`, and `tests/test_campaign_save_manager.py`.
7. Rebuild the release package through the repository packager and retain `_build/release/generated/provenance.json`. Verify its input/output digests before comparing a reproduction with the affected package.
8. Run `python3 tooling/validate_recovery_documentation.py`, followed by the complete repository validation. Attach the immutable compatibility fixture, integrity report, original-save digest, package provenance, test output, and minimal transition steps to the defect report.

The checked-in compatibility manifest supplies immutable migration/rejected-load fixtures. The named test modules supply interrupted-transition, map-revisit, missing-representation, integrity, native-save, autosave, and checkpoint reproductions. Do not “repair” authoritative facts: only derived indexes and runtime representations are reconstructible.

For the player selection path, execute `wurst/CampaignRecoveryTests.wurst` through
the pinned full-suite runner. It dispatches registered `/saves`, `/save`, `/load`
and `/load retry` actions using recording storage, loader and projection ports.
Compare the selected envelope and every recovery slot byte before and after
selection, destination registration, reconstruction, acknowledgement failure and
retry. Include `CampaignStartupTests.wurst`, `CampaignLoadTransactionTests.wurst`
and the position regressions in that same run.

The bootstrap namespace's `recovery_request` v1 record is separate from the
origin request and ordinary travel milestone. It copies the selected envelope,
binds it to the campaign, slot and physical map, and remains recoverable after
acknowledgement. A changed origin-request or milestone checksum supersedes it.
Absence of this new record follows the existing startup path; save schemas 1–7
and their in-memory migrations remain supported. Never overwrite a reported
source slot to manufacture a retry. Destination failure keeps gameplay locked
and exposes recovery commands until a full startup succeeds.

This evidence does not close `blocked_pending_real_forsaken_kingdom_launch_smoke`.
No incremental player QA is required.
