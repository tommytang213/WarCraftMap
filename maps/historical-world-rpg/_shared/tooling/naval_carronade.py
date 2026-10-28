"""Current-source execution recognition for paid close-range naval armament.

The scenario supplies exact typed candidates. Commissioning, repair and voyage
effects have independent verifiers and cannot borrow these combat probes.
"""

COMPARISON = 'carronadeOnlyPaidMatchedVesselsUseInstalledAndAbstractDamage'
REQUIRED_TESTS = {
    COMPARISON,
    'carronadeMountAndDamageRejectEachMissingQualification',
    'carronadeCaptureReconstructionAndMaintenanceUseCurrentAuthority',
    'carronadePlayerAiActiveAbstractAndAdditiveLayersPreserveUnboundedXp',
    'carronadeLateLoadRollbackRestoresResearchMountWorkAndResources',
    'paidCarronadesUseInstalledProductionWeaponCallbacksAndRejectStaleAndIncompatibleHits',
    'navalNegativeConditionsRejectWithoutPaymentAndSaveMigrationAndLateRollbackAreAtomic',
    'combinedNavalAndLandSnapshotsPreserveBothHRecordsAndMigrateEitherVersion13Branch',
}
PROBES = {'research', 'dispatch', 'naval_registration', 'naval_action',
          'naval_pay', 'naval_advance', 'naval_mount_commit', 'naval_combat',
          'land_damage', 'land_native_weapon', 'combat_rating',
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
        comparison = prefix + COMPARISON
        if not {prefix + name for name in REQUIRED_TESTS} <= passed:
            return set()
        if not PROBES <= set(execution['productionCoverage']['tests'].get(comparison, [])):
            return set()
        return {(row['kind'], row['contentId']) for row in candidates()
                if comparison in coverage.get(row['executionSystem'], [])}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()
