"""Fail-closed recognition of Carvel's isolated production voyage comparison.

Commissioning, repair and combined naval traces cannot prove weather avoidance.
Only complete current pinned execution may remove this exact typed finding.
"""

COMPARISON = 'carvelOnlyRegisteredVoyagesAvoidEightPercentAgainstMatchedControl'
REQUIRED_TESTS = {
    COMPARISON,
    'carvelVoyagesRequireCompletedResearchCompatibleHullAndHistoricalService',
    'carvelRefitsRequirePaidCompletedCompatibleWork',
    'carvelVoyagesCalmUnfundedAndUnprovisionedDaysEarnNoCredit',
    'carvelVoyagesFractionsResumeInterruptAndDestroyWithoutDuplicateLoss',
    'carvelVoyagesCapturePreservesGearWithoutForeignResearch',
    'carvelVoyagesPlayerAiAndActiveInactiveUseIdenticalAuthority',
    'carvelVoyagesLateLoadRollbackRestoresHullGearResearchAndResources',
    'navalNegativeConditionsRejectWithoutPaymentAndSaveMigrationAndLateRollbackAreAtomic',
    'combinedNavalAndLandSnapshotsPreserveBothHRecordsAndMigrateEitherVersion13Branch',
}
PROBES = {'research', 'dispatch', 'naval_registration', 'naval_advance',
          'voyage_registration', 'voyage_start', 'voyage_resolve',
          'naval_voyage_weather', 'naval_weather', 'naval_hull_commit',
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
                or comparative not in coverage.get('naval_carvel', [])):
            return set()
        return {(row['kind'], row['contentId']) for row in candidates()
                if row['executionSystem'] == 'naval_carvel'}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()
