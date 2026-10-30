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
    if data['schemaVersion'] != 1 or len(data['effects']) != 3:
        raise ValueError('administrative contracts: invalid schema/effects')
    for effect, node_key, kind, metric in zip(data['effects'], ('archiveNode', 'municipalNode', 'examinationsNode'),
                                           ('modifier', 'policy', 'modifier'),
                                           ('archive_tax_collection_efficiency', 'municipal_tax_collection_efficiency',
                                            'records_tax_collection_efficiency')):
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
    try:
        world = json.loads((project / 'scenario/world/world.json').read_text())
        lines, effects, _, _ = configuration(project, world)
    except (ValueError, OSError, KeyError, TypeError):
        return set()
    # Examinations has its own exact comparison and probe requirements below.
    result = {(e['unlock']['kind'], e['unlock']['contentId']) for e in effects[:2]}
    observed = execution['productionCoverage']['tests']
    examination = effects[2]
    comparison = prefix + EXAMINATIONS_COMPARISON
    if (EXAMINATIONS_REQUIRED_TESTS <= passed
            and comparison in coverage.get('civil_service_examinations', [])
            and EXAMINATIONS_PROBES <= set(observed.get(comparison, []))
            and any(r['id'] == EXAMINATIONS_ROLLBACK and r['status'] == 'pass' for r in execution['tests'])
            and examination == EXAMINATIONS_EFFECT
            and {'\tledger.archiveUpkeepBasisPoints = 25', '\tledger.minimumAdministration = 40'} <= set(lines)):
        result.add(('modifier', 'progression_civil_service_examinations'))
    return result


EXAMINATIONS_EFFECT = {
    'nodeId': 'civil_service_examinations',
    'unlock': {'kind': 'modifier', 'contentId': 'progression_civil_service_examinations'},
    'metric': 'records_tax_collection_efficiency', 'bonusBasisPoints': 500,
}
EXAMINATIONS_COMPARISON = 'examinationsRegisteredResearchMatchedControlCollectsFundedLocalRevenue'
EXAMINATIONS_REQUIRED_TESTS = {
    EXAMINATIONS_COMPARISON,
    'examinationsSharedBillAdditiveLayersAndDuplicateGrantsStayBounded',
    'examinationsCurrentQualificationFundingAndLiquidityGateCollection',
    'examinationsReplacementCaptureAndRecaptureReevaluateCurrentAuthority',
    'examinationsPlayerAiActiveAbstractSaveMigrationAndAnnualIdempotency',
}
EXAMINATIONS_ROLLBACK = 'wurst/CampaignLoadTransactionTests.wurst:lateLoadFailureRestoresExaminationsCollectionTreasuryLiquidityAndAnnualAccounting'
EXAMINATIONS_PROBES = {'civic_registration', 'research', 'dispatch', 'administrative_skill',
                       'administrative_advance', 'administrative_pay', 'administrative_collect', 'civic_clock'}


def verify_registration(project, world, source, catalog):
    """Executable rules and typed metadata must match the scenario, even if resealed."""
    lines, effects, _, _ = configuration(project, world)
    registrations = [f'\tresearch.register(new CivicEffect({json.dumps(e["unlock"]["kind"])}, '
                     f'{json.dumps(e["unlock"]["contentId"])}, {json.dumps(e["metric"])}, '
                     f'{e["bonusBasisPoints"]}))' for e in effects]
    metrics = {e['metric'] for e in effects}
    actual = [line for line in source.splitlines()
              if line.startswith(('\tledger.archiveUpkeepBasisPoints =', '\tledger.minimumAdministration =',
                                  '\tledger.municipalNode =', '\tledger.municipalMinimumUrbanization ='))
              or (line.startswith('\tresearch.register(new CivicEffect(')
                  and any(json.dumps(metric) in line for metric in metrics))]
    if (actual != lines + registrations
            or [e for e in catalog.get('effects', []) if e['metric'] in metrics] != effects):
        raise ValueError('administrative contracts: executable or runtime registration differs from scenario')
