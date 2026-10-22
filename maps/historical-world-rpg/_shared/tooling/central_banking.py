"""Scenario-owned treasury operations; independent of exchange/remittance."""
from datetime import date
import json
from pathlib import Path

from civic_governance import annual_tax_capacity
from scenario_inputs import content_path

METRICS = {'treasury_counting_cost_reduction': 'modifier',
           'treasury_reconciliation_cost_reduction': 'policy'}
RULES = {'transitionDays', 'enactmentBasisPoints', 'upkeepBasisPoints',
         'countingBasisPoints', 'reconciliationBasisPoints'}


def configuration(project, world, settlements, authored, trade_records):
    path = project / 'scenario/progression/central-banking.json'
    header = '\npublic function configureGeneratedBanking(BankingLedger ledger, BankingResearchEffects effects)\n'
    if not path.is_file():
        return header + '\tskip\n', {}, []
    data = json.loads(path.read_text())
    if data.get('schemaVersion') != 1 or set(data['rules']) != RULES:
        raise ValueError('banking: invalid schema/rules')
    for key, value in data['rules'].items():
        if type(value) is not int or not 0 < value <= (365 if key == 'transitionDays' else 1000):
            raise ValueError('banking: invalid bill or duration ' + key)
    design = content_path(project, data['designSource'])
    tax_source = content_path(project, data['taxSource'])
    tax = json.loads(tax_source.read_text())['districts']
    effects = [e for e in json.loads(design.read_text())['effects'] if e['metric'] in METRICS]
    if len(effects) != 2 or {e['metric'] for e in effects} != set(METRICS):
        raise ValueError('banking: missing distinct exact contracts')
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    if data['bankPrerequisite'] not in nodes:
        raise ValueError('banking: missing bookkeeping prerequisite')
    q = json.dumps
    lines = [header, f'\tledger.prerequisite = {q(data["bankPrerequisite"])}']
    for key, value in data['rules'].items():
        lines.append(f'\tledger.{key} = {value}')
    for e in effects:
        node = nodes[e['nodeId']]
        unlock = e['unlock']
        if (unlock not in node['unlocks'] or unlock['kind'] != METRICS[e['metric']]
                or type(e['bonusBasisPoints']) is not int or not 0 < e['bonusBasisPoints'] < 10000):
            raise ValueError('banking: invalid typed effect')
        first = date(node['timeCost']['preferredYear'], 1, 1).toordinal()
        lines.append(f'\teffects.register(new BankingEffect({q(unlock["kind"])}, {q(unlock["contentId"])}, {q(e["metric"])}, {e["bonusBasisPoints"]}, {first}))')
    ids = data['siteIds']
    if not 0 < len(ids) <= 64 or len(set(ids)) != len(ids):
        raise ValueError('banking: duplicate or excessive bank sites')
    positions = {s['id'] for s in settlements}
    sites = []
    for sid in ids:
        row = authored.get(sid, ('', {}))[1]
        if (sid not in positions or not {'banking', 'warehouse', 'market'} <= set(row.get('services', []))
                or not any(f'runtime.registerMarketProfile({q(sid)},' in x for x in trade_records)):
            raise ValueError('banking: real banking, warehouse and market infrastructure required')
        annual = annual_tax_capacity(tax, row)
        if type(annual) is not int or not 0 < annual <= 100000000:
            raise ValueError('banking: invalid normal tax capacity')
        lines.append(f'\tledger.register(new BankingSite({q(sid)}, {annual}))')
        sites.append(dict(id=sid, annualTax=annual))
    return '\n'.join(lines) + '\n', data | {'effects': effects, 'sites': sites}, [path, design, tax_source, Path(__file__), Path(__file__).with_name('civic_governance.py')]


REQUIRED_TESTS = {
    'bankingRegisteredResearchAdoptionPolicyAndRealLodgementsHaveDistinctBenefits',
    'bankingRejectsMissingInfrastructureFundsUnauthorizedStaleAndReplayQuotes',
    'bankingCaptureSaveMigrationAndFailedLoadRollbackPreserveAuthority',
    'bankingLongCampaignActiveAbstractUpkeepAndConservation',
    'bankingResearchProvenanceAndEraReconstructionNeverGrantsPolicy',
}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        verify_execution_coverage(execution, execution_log, project, revision)
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError):
        return set()
    prefix = 'wurst/BankingOperationsTests.wurst:'
    passed = {row['id'][len(prefix):] for row in execution['tests']
              if row['status'] == 'pass' and row['id'].startswith(prefix)}
    probes = execution.get('productionCoverage', {}).get('tests', {})
    required = {'banking_registration', 'banking_policy', 'banking_quote', 'banking_commit', 'banking_advance'}
    if not REQUIRED_TESTS <= passed or not required <= set(probes.get(prefix + 'bankingRegisteredResearchAdoptionPolicyAndRealLodgementsHaveDistinctBenefits', [])):
        return set()
    config = json.loads((project / 'scenario/progression/central-banking.json').read_text())
    design = json.loads(content_path(project, config['designSource']).read_text())
    return {(e['unlock']['kind'], e['unlock']['contentId']) for e in design['effects'] if e['metric'] in METRICS}
