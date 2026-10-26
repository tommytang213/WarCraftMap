"""Fail-closed execution recognition for paid naval commissioning consumers.

Scenario builders supply exact candidates and authoritative bills. This verifier
uses the existing revision-bound execution transport, never retained PR evidence.
"""

COMPARISON = 'doctrineOnlyRegisteredCommissioningRequiresPaidWorkAgainstMatchedControl'
REQUIRED_TESTS = {
    COMPARISON,
    'doctrineCommissioningRejectsEachMissingConditionWithoutMutation',
    'doctrineCommissioningCaptureCancelsAndReconstructionNeverRepeatsCompletion',
    'doctrineCommissioningPlayerAiAndActiveInactiveUseIdenticalAuthority',
    'doctrineCommissioningLateLoadRollbackRestoresPaidWorkAndResources',
    'navalNegativeConditionsRejectWithoutPaymentAndSaveMigrationAndLateRollbackAreAtomic',
    'combinedNavalAndLandSnapshotsPreserveBothHRecordsAndMigrateEitherVersion13Branch',
}
PROBES = {'research', 'dispatch', 'naval_registration', 'naval_action',
          'naval_pay', 'naval_advance', 'naval_complete', 'naval_snapshot', 'naval_restore'}


def verified_consumers(project, candidates, execution=None, execution_log=None, revision=None):
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
        prefix = 'wurst/NavalServicesTests.wurst:'
        passed = {row['id'] for row in execution['tests'] if row['status'] == 'pass'}
        if not {prefix + name for name in REQUIRED_TESTS} <= passed:
            return set()
        comparative = prefix + COMPARISON
        probes = execution['productionCoverage']['tests'].get(comparative, [])
        if not PROBES <= set(probes):
            return set()
        return {(row['kind'], row['contentId']) for row in candidates()
                if comparative in coverage.get(row['executionSystem'], [])}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()
