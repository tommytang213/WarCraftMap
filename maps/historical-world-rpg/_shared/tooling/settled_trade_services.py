"""Independent evidence gates for the two Phase 9 settled transaction services."""
import json
from pathlib import Path

COURT = ('policy', 'progression_commercial_courts_institution')
STATISTICS = ('modifier', 'progression_commercial_statistics')
PREFIX = 'wurst/SettledTradeServicesTests.wurst:'
COMMON = {'settledServicesRejectStaleAuthorityFundsStockCapacityAndReplay',
          'settledServicesParitySplitOrdersAndRoundTripsNeverFarmStanding',
          'settledServicesMigrationCaptureReenactmentAndRollbackPreserveAuthority'}
CASES = {
    COURT: ('institutionOnlyRegisteredBuySellSettlesItsOwnProcessingBill',
            {'courts_registration', 'institution_courts_policy', 'courts_fee', 'courts_advance',
             'finance_buy_settle', 'finance_sell_settle', 'research'}),
    STATISTICS: ('statisticsOnlyRegisteredBuySellSettlesItsOwnSlippage',
                 {'finance_registration', 'finance_quote', 'finance_buy_settle',
                  'finance_sell_settle', 'research'}),
}


def adoption_configuration(project, world, contract):
    source = project / 'scenario/progression/catalog.json'
    catalog = json.loads(source.read_text())
    node_id = contract['effects'][0]['nodeId']
    authored = next(n for n in catalog['institutions'] if n['id'] == node_id)
    node = next(n for n in world['institutions'] if n['id'] == node_id)
    req = authored['adoptionRequirements']
    minimum = req['minimumUrbanization']
    if (type(minimum) is not int or not 0 <= minimum <= 100
            or not set(req['requiredNodeIds']) <= set(node['prerequisiteIds'])):
        raise ValueError('institution courts: lost adoption requirements')
    return (f'\tledger.courtNode = {json.dumps(node_id)}\n'
            f'\tledger.courtMinimumUrbanization = {minimum}\n'), [source, Path(__file__)]


def exact_contracts(project):
    """Match the approved typed sources and coefficients, independently."""
    result = set()
    for filename, node, identity, metric, rate in (
        ('institution-courts-effects.json', 'commercial_courts_institution', COURT,
         'institution_processing_cost_reduction', 400),
        ('gameplay-effect-design.json', 'commercial_statistics', STATISTICS,
         'market_slippage_reduction', 500),
    ):
        try:
            rows = [e for e in json.loads((project / 'scenario/progression' / filename).read_text())['effects']
                    if e['nodeId'] == node]
            if (len(rows) == 1 and rows[0]['unlock'] == dict(kind=identity[0], contentId=identity[1])
                    and rows[0]['metric'] == metric and type(rows[0]['bonusBasisPoints']) is int
                    and rows[0]['bonusBasisPoints'] == rate):
                result.add(identity)
        except (ValueError, OSError, KeyError, TypeError):
            pass
    return result


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        verify_execution_coverage(execution, execution_log, project, revision)
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError):
        return set()
    passed = {r['id'][len(PREFIX):] for r in execution['tests']
              if r['status'] == 'pass' and r['id'].startswith(PREFIX)}
    if not COMMON <= passed:
        return set()
    probes = execution.get('productionCoverage', {}).get('tests', {})
    result = set()
    for identity, (case, required) in CASES.items():
        if case in passed and required <= set(probes.get(PREFIX + case, [])):
            result.add(identity)
    return result & exact_contracts(project)
