"""Exact, fail-closed evidence selection for separate chartered action consumers."""
import json

REQUIRED_TESTS = {
    'charteredRegisteredResearchCourtsAndPaidIndiamanRemainIndependent',
    'charteredEveryRecruitmentGateAndStaleQuotesRejectAtomically',
    'charteredCourtsRealTradesConservePrincipalAndRejectIneligibleActivity',
    'charteredCaptureMigrationMalformedSavesAndIndependentPermissionsPreserveAuthority',
    'charteredLongCampaignActiveAbstractCostsAndConstructionMatch',
    'charteredLateLoadFailureRestoresCourtConstructionAndTreasuryState',
    'charteredCourtActivationRejectsMissingPermissionInfrastructureAndOperatingFundsWithoutMutation',
    'charteredConstructionCounterLimitStaysSaveableAndDoesNotDuplicateExistingHulls',
}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError):
        return set()
    prefix = 'wurst/CharteredCompaniesTests.wurst:'
    passed = {r['id'][len(prefix):] for r in execution['tests']
              if r['status'] == 'pass' and r['id'].startswith(prefix)}
    if not REQUIRED_TESTS <= passed:
        return set()
    comparative = prefix + 'charteredRegisteredResearchCourtsAndPaidIndiamanRemainIndependent'
    if any(comparative not in coverage.get(system, [])
           for system in ('commercial_courts', 'merchant_construction')):
        return set()
    courts = json.loads((project / 'scenario/progression/commercial-courts-effects.json').read_text())
    naval = json.loads((project / 'scenario/naval/recruitment.json').read_text())
    return ({(e['unlock']['kind'], e['unlock']['contentId']) for e in courts['effects']}
            | {('unit', e['contentId']) for e in naval['blueprints']})
