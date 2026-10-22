"""Scenario-owned archive/municipal contracts for the civic domain consumer."""
import json


def configuration(project, world):
    path = project / 'scenario/progression/administrative-contracts.json'
    if not path.exists():
        return [], [], {}, []
    data = json.loads(path.read_text())
    source = project / data['catalogSource']
    catalogue = json.loads(source.read_text())
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    authored = {n['id']: n for n in catalogue['technologies'] + catalogue['institutions']}
    if data['schemaVersion'] != 1 or len(data['effects']) != 2:
        raise ValueError('administrative contracts: invalid schema/effects')
    for effect, node_key, kind, metric in zip(data['effects'], ('archiveNode', 'municipalNode'),
                                           ('modifier', 'policy'),
                                           ('archive_tax_collection_efficiency', 'municipal_tax_collection_efficiency')):
        node = nodes[data[node_key]]
        if (effect['nodeId'] != node['id'] or effect['unlock'] not in node['unlocks']
                or effect['unlock']['kind'] != kind or effect['metric'] != metric
                or type(effect['bonusBasisPoints']) is not int or not 0 < effect['bonusBasisPoints'] <= 1000):
            raise ValueError('administrative contracts: invalid typed binding')
    requirements = authored[data['municipalNode']]['adoptionRequirements']
    minimum = requirements['minimumUrbanization']
    if (type(minimum) is not int or not 0 <= minimum <= 100
            or data['archiveNode'] not in requirements['requiredNodeIds']
            or not set(requirements['requiredNodeIds']) <= set(nodes[data['municipalNode']]['prerequisiteIds'])):
        raise ValueError('administrative contracts: lost catalogue adoption requirements')
    if set(data['rules']) != {'archiveUpkeepBasisPoints', 'minimumAdministration'}:
        raise ValueError('administrative contracts: invalid operating rules')
    for key, maximum in (('archiveUpkeepBasisPoints', 10000), ('minimumAdministration', 100)):
        if type(data['rules'][key]) is not int or not 0 < data['rules'][key] <= maximum:
            raise ValueError('administrative contracts: invalid ' + key)
    urban = data['urbanization']
    if (set(urban) != {'urbanRoles', 'urbanPercent', 'otherPercent'} or not urban['urbanRoles']
            or any(type(urban[k]) is not int or not 0 <= urban[k] <= 100 for k in ('urbanPercent', 'otherPercent'))):
        raise ValueError('administrative contracts: invalid urbanization')
    lines = [f'\tledger.{key} = {value}' for key, value in data['rules'].items()]
    lines += [f'\tledger.municipalNode = {json.dumps(data["municipalNode"])}',
              f'\tledger.municipalMinimumUrbanization = {minimum}']
    return lines, data['effects'], urban, [path, source, __import__('pathlib').Path(__file__)]


REQUIRED_TESTS = {
    'administrativeRegisteredArchivesThenAdoptionAndMunicipalPolicyProduceConservedTaxDifferences',
    'administrativePrerequisitesUrbanizationResourcesAndForeignJurisdictionRejectWithoutMutation',
    'administrativeOfficeReplacementOperatingConditionsAndSurveySourcesCompose',
    'administrativeActiveAbstractParityCaptureMigrationAndFailedLoadRollback',
    'administrativeUpkeepLossDuplicatesAndReenactmentNeverCreatePermanentBenefits',
}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    """Only fresh pinned production execution may close research release findings."""
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError):
        return set()
    prefix = 'wurst/CivicGovernanceTests.wurst:'
    passed = {r['id'][len(prefix):] for r in execution['tests']
              if r['status'] == 'pass' and r['id'].startswith(prefix)}
    rollback = 'wurst/CampaignLoadTransactionTests.wurst:lateLoadFailureRestoresMunicipalPolicyUrbanizationAndTreasuryAtomically'
    comparative = prefix + 'administrativeRegisteredArchivesThenAdoptionAndMunicipalPolicyProduceConservedTaxDifferences'
    if (not REQUIRED_TESTS <= passed or comparative not in coverage.get('administrative_contracts', [])
            or not any(r['id'] == rollback and r['status'] == 'pass' for r in execution['tests'])):
        return set()
    world = json.loads((project / 'scenario/world/world.json').read_text())
    _, effects, _, _ = configuration(project, world)
    return {(e['unlock']['kind'], e['unlock']['contentId']) for e in effects}
