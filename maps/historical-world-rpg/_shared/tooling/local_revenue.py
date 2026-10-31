"""Scenario-owned local law and overseas council consumers and exact evidence gate."""
import json
from pathlib import Path

METRICS = ('law_tax_collection_efficiency', 'council_tax_collection_efficiency')


def configuration(project, world):
    path = project / 'scenario/progression/local-revenue-contracts.json'
    if not path.exists():
        return [], [], [], []
    data = json.loads(path.read_text())
    source = project / data['catalogSource']
    catalog = json.loads(source.read_text())
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    authored = {n['id']: n for n in catalog['technologies'] + catalog['institutions']}
    if data['schemaVersion'] != 1 or len(data['effects']) != 2:
        raise ValueError('local revenue: invalid schema/effects')
    for effect, kind, metric in zip(data['effects'], ('modifier', 'policy'), METRICS):
        node = nodes.get(effect['nodeId'], {})
        if (effect['unlock'] not in node.get('unlocks', []) or effect['unlock']['kind'] != kind
                or effect['metric'] != metric or type(effect['bonusBasisPoints']) is not int
                or not 0 < effect['bonusBasisPoints'] <= 1000):
            raise ValueError('local revenue: invalid typed binding')
    council = nodes[data['councilNode']]
    requirements = authored[data['councilNode']]['adoptionRequirements']
    minimum = requirements['minimumUrbanization']
    if (data['effects'][1]['nodeId'] != council['id'] or type(minimum) is not int
            or not 0 <= minimum <= 100 or data['archiveNode'] not in requirements['requiredNodeIds']
            or not set(requirements['requiredNodeIds']) <= set(council['prerequisiteIds'])):
        raise ValueError('local revenue: lost catalogue adoption requirements')
    if set(data['rules']) != {'councilTransitionDays', 'councilEnactmentBasisPoints', 'councilUpkeepBasisPoints'}:
        raise ValueError('local revenue: invalid rules')
    if any(type(v) is not int or not 0 < v <= (365 if k.endswith('Days') else 10000)
           for k, v in data['rules'].items()):
        raise ValueError('local revenue: invalid operating rule')
    settlement_sources = sorted((project / 'scenario/settlements').glob('*-1450.json'))
    settlements = {row['id']: (p.stem, row) for p in settlement_sources
                   for row in json.loads(p.read_text())['settlements']}
    connections = data['connections']
    pairs = {(x['originId'], x['recipientId']) for x in connections}
    if not 0 < len(connections) <= 64 or len(pairs) != len(connections):
        raise ValueError('local revenue: duplicate/invalid connections')
    for link in connections:
        a, b = link['originId'], link['recipientId']
        if a not in settlements or b not in settlements or settlements[a][0] == settlements[b][0]:
            raise ValueError('local revenue: requires documented overseas endpoints')
        rows = [settlements[x][1] for x in (a, b)]
        evidence = set(link['evidenceIds'])
        if (not evidence or any(not row.get('port') or not evidence.intersection(row['historicalEvidenceIds'])
                                for row in rows)
                or not evidence <= set().union(*(set(row['historicalEvidenceIds']) for row in rows))):
            raise ValueError('local revenue: missing maritime geography evidence')
    q = json.dumps
    lines = [f'\tledger.{key} = {value}' for key, value in data['rules'].items()]
    lines += [f'\tledger.councilNode = {q(data["councilNode"])}',
              f'\tledger.councilMinimumUrbanization = {minimum}']
    lines += [f'\tledger.addCouncilLink({q(x["originId"])}, {q(x["recipientId"])})' for x in connections]
    return lines, data['effects'], connections, [path, source, Path(__file__), *settlement_sources]


def verify_registration(project, world, source, catalog):
    lines, effects, connections, _ = configuration(project, world)
    expected = lines + [f'\tresearch.register(new CivicEffect({json.dumps(e["unlock"]["kind"])}, '
                        f'{json.dumps(e["unlock"]["contentId"])}, {json.dumps(e["metric"])}, '
                        f'{e["bonusBasisPoints"]}))' for e in effects]
    actual = [line for line in source.splitlines() if line.startswith(('\tledger.council', '\tledger.addCouncilLink('))
              or line.startswith('\tresearch.register(new CivicEffect(') and any(json.dumps(m) in line for m in METRICS)]
    if (actual != expected or [e for e in catalog.get('effects', []) if e['metric'] in METRICS] != effects
            or catalog.get('councilConnections', []) != connections):
        raise ValueError('local revenue: executable or runtime metadata differs from scenario')


COMPARISONS = {
    ('modifier', 'progression_codified_law'): ('codified_law', 'lawRegisteredResearchMatchedControlCollectsPaidRevenue',
                                             'codified_law', METRICS[0], 500),
    ('policy', 'progression_colonial_councils'): ('colonial_councils', 'councilsRegisteredResearchMatchedControlRequiresPaidElection',
                                               'colonial_councils', METRICS[1], 400),
}
REQUIRED_TESTS = {
    'revenueSharedRecordsAndCouncilSourcesRoundOnceWithinCapacityAndLiquidity',
    'revenueQualificationFundingAndOverseasAuthorityFailClosed',
    'revenueAdoptionPrerequisitesUrbanizationAndAtomicBills',
    'revenueReplacementCaptureAndRecapturePreservePoliticalAuthority',
    'revenuePlayerAiActiveInactiveSaveResumeAndLegacyMigration',
    'revenueMalformedCouncilRecordsRejectAtomically',
}
ROLLBACK = 'wurst/CampaignLoadTransactionTests.wurst:lateLoadFailureRestoresLawCouncilFundingAndActualRevenue'
PROBES = {'civic_registration', 'research', 'dispatch', 'administrative_skill',
          'administrative_advance', 'administrative_pay', 'administrative_collect', 'civic_clock'}
COUNCIL_PROBES = PROBES | {'administrative_adoption', 'administrative_action', 'council_authority'}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
        prefix = 'wurst/LocalRevenueTests.wurst:'
        passed = {r['id'] for r in execution['tests'] if r['status'] == 'pass'}
        if not ({prefix + n for n in REQUIRED_TESTS} | {ROLLBACK}) <= passed:
            return set()
        world = json.loads((project / 'scenario/world/world.json').read_text())
        lines, effects, _, _ = configuration(project, world)
        from administrative_governance import configuration as administrative_configuration
        admin, _, _, _ = administrative_configuration(project, world)
        required = {'\tledger.councilTransitionDays = 90', '\tledger.councilEnactmentBasisPoints = 100',
                    '\tledger.councilUpkeepBasisPoints = 50', '\tledger.councilMinimumUrbanization = 16',
                    '\tledger.councilNode = "colonial_councils"', '\tledger.archiveUpkeepBasisPoints = 25',
                    '\tledger.minimumAdministration = 40'}
        if not required <= set(lines + admin):
            return set()
        authored = {(e['unlock']['kind'], e['unlock']['contentId']):
                    (e['nodeId'], e['metric'], e['bonusBasisPoints']) for e in effects}
        observed = execution['productionCoverage']['tests']
        return {pair for pair, (system, test, node, metric, bonus) in COMPARISONS.items()
                if authored.get(pair) == (node, metric, bonus) and prefix + test in passed
                and prefix + test in coverage.get(system, [])
                and (COUNCIL_PROBES if system == 'colonial_councils' else PROBES)
                <= set(observed.get(prefix + test, []))}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()
