"""Fail-closed execution recognition for paid dockside repair consumers.

Commissioning and combined naval traces cannot replace the isolated repair
comparison. Scenario builders supply exact typed candidates and repair bills.
"""

COMPARISON = 'careeningOnlyRegisteredRepairsChargeEachDayAgainstMatchedControl'
REQUIRED_TESTS = {
    COMPARISON,
    'careeningRepairsBoundFullHullAndPreserveLegacyHullFractions',
    'careeningRepairsRejectMissingInputsAndInaccessibleRecipientsWithoutMutation',
    'careeningRepairsSuspendUnfundedDaysAndCancelOnLostAccess',
    'careeningRepairsCaptureAndControllerTransferCancelPaidWork',
    'careeningRepairsPlayerAiAndActiveInactiveUseIdenticalAuthority',
    'careeningRepairsLateLoadRollbackRestoresPaidWorkAndResources',
    'navalNegativeConditionsRejectWithoutPaymentAndSaveMigrationAndLateRollbackAreAtomic',
    'combinedNavalAndLandSnapshotsPreserveBothHRecordsAndMigrateEitherVersion13Branch',
}
PROBES = {'research', 'dispatch', 'naval_registration', 'naval_action',
          'naval_pay', 'naval_payment', 'naval_advance', 'naval_repair',
          'naval_snapshot', 'naval_restore'}


def verified_consumers(project, candidates, execution=None, execution_log=None, revision=None):
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
        prefix = 'wurst/NavalServicesTests.wurst:'
        passed = {row['id'] for row in execution['tests'] if row['status'] == 'pass'}
        comparative = prefix + COMPARISON
        if (not {prefix + name for name in REQUIRED_TESTS} <= passed
                or not PROBES <= set(execution['productionCoverage']['tests'].get(comparative, []))
                or comparative not in coverage.get('naval_repair', [])):
            return set()
        return {(row['kind'], row['contentId']) for row in candidates()
                if row['executionSystem'] == 'naval_repair'}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()
