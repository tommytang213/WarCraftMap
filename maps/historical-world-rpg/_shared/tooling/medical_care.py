"""Scenario-owned, independently verified local disease-care consumers."""
import json
from pathlib import Path

IDENTITIES = {
    ('modifier', 'progression_civic_pest_hospitals'):
        ('civic_pest_hospitals', 'isolation_care_losses_avoided', 500),
    ('modifier', 'progression_clinical_case_records'):
        ('clinical_case_records', 'case_records_losses_avoided', 500),
}
RULES = {'carePreparationDays': 90, 'careCommissionBasisPoints': 100,
         'careUpkeepBasisPoints': 50, 'careDailyMaterials': 1,
         'recordsDailyMoney': 1, 'recordsDailyMaterials': 1}


def configuration(project, world):
    path = project / 'scenario/progression/medical-care.json'
    if not path.exists():
        return [], [], {}, []
    data = json.loads(path.read_text())
    source = project / data['catalogSource']
    catalogue = json.loads(source.read_text())
    authored = {n['id']: n for n in catalogue['technologies']}
    nodes = {n['id']: n for n in world['technologies']}
    civic_source = project / 'scenario/progression/civic-governance.json'
    staff_source = project / 'scenario/progression/administrative-contracts.json'
    civic = json.loads(civic_source.read_text())
    administration = json.loads(staff_source.read_text())
    if (data['schemaVersion'] != 1 or data['rules'] != RULES
            or any(type(v) is not int for v in data['rules'].values())
            or data['recordsGood'] not in civic['districts']['medicalGoodPreference'] or len(data['effects']) != 2):
        raise ValueError('medical care: invalid schema or paid-service rules')
    consumers = []
    seen = set()
    for effect in data['effects']:
        unlock = effect['unlock']
        pair = (unlock['kind'], unlock['contentId'])
        exact = (effect['nodeId'], effect['metric'], effect['bonusBasisPoints'])
        node = nodes.get(effect['nodeId'], {})
        original = authored.get(effect['nodeId'], {})
        if (pair in seen or IDENTITIES.get(pair) != exact or type(effect['bonusBasisPoints']) is not int
                or unlock not in node.get('unlocks', [])
                or node.get('prerequisiteIds') != original.get('prerequisiteIds')
                or node.get('timeCost', {}).get('preferredYear') != original.get('preferredYear')):
            raise ValueError('medical care: exact typed binding, prerequisites and availability required')
        seen.add(pair)
        consumers.append(dict(nodeId=effect['nodeId'], kind=pair[0], contentId=pair[1],
                              metric=effect['metric'], basisPoints=effect['bonusBasisPoints'],
                              prerequisiteIds=node['prerequisiteIds'], preferredYear=node['timeCost']['preferredYear'],
                              authority='CivicLedger.advance', recipient='actual_exposed_local_manpower',
                              conditions=['current_research', 'lawful_local_staff', 'accessible_materials', 'funded_care', 'outbreak'],
                              minimumAdministration=administration['rules']['minimumAdministration'],
                              fractionDenominator=10000,
                              commissioning=dict(taxBasisPoints=data['rules']['careCommissionBasisPoints'],
                                                 taxBase='district.normalAnnualTax',
                                                 materials='district.medicalGood', units=civic['districts']['medicalUnits'],
                                                 preparationDays=data['rules']['carePreparationDays']),
                              response={key: civic['rules'][key] for key in
                                        ('responseBasisPoints', 'responseDays', 'cooldownDays', 'tradePenaltyBasisPoints')},
                              rules=data['rules'], recordsGood=data['recordsGood']))
    lines = [f'\tledger.{k} = {v}' for k, v in data['rules'].items()]
    lines.append(f'\tledger.recordsGood = {json.dumps(data["recordsGood"])}')
    return lines, data['effects'], {'consumers': consumers}, [path, source, Path(__file__), civic_source, staff_source]


def verify_registration(project, world, source, catalog):
    lines, effects, metadata, _ = configuration(project, world)
    expected = lines + [f'\tresearch.register(new CivicEffect({json.dumps(e["unlock"]["kind"])}, '
                         f'{json.dumps(e["unlock"]["contentId"])}, {json.dumps(e["metric"])}, '
                         f'{e["bonusBasisPoints"]}))' for e in effects]
    actual = [line for line in source.splitlines() if line.startswith(tuple(
        '\tledger.' + key + ' = ' for key in (*RULES, 'recordsGood')))
        or (line.startswith('\tresearch.register(new CivicEffect(')
            and any(json.dumps(v[1]) in line for v in IDENTITIES.values()))]
    if (actual != expected or catalog.get('medicalCare') != metadata
            or [e for e in catalog.get('effects', []) if e['metric'] in {v[1] for v in IDENTITIES.values()}] != effects):
        raise ValueError('medical care: executable or exact consumer metadata differs from scenario')


REQUIRED_TESTS = {
    'medicalConditionsAndAtomicDailyFundingRejectMissingInputs',
    'medicalHospitalNeedsCommissioningAndDailyInputsAndRecordsNeedActualCare',
    'medicalPreparationUpkeepCaptureAndMigrationPreserveCivicAuthority',
    'medicalFractionalCompositionDeduplicatesDaysAndSources',
    'medicalPlayerAiAndActiveInactiveCareHaveIdenticalOutcomes',
}
COMPARISONS = {
    ('modifier', 'progression_civic_pest_hospitals'):
        ('pest_hospitals', 'pestHospitalsOnlyMatchedPaidCareAvoidsFiveOfOneHundredLosses', 'isolation_care'),
    ('modifier', 'progression_clinical_case_records'):
        ('clinical_records', 'clinicalRecordsOnlyMatchedPaidResponseAvoidsFiveOfOneHundredLosses', 'case_records'),
}
ROLLBACK = 'wurst/CampaignLoadTransactionTests.wurst:lateLoadFailureRestoresMedicalCareFractionsRecordsAndPaidResources'
COMMON_PROBES = {'civic_registration', 'research', 'dispatch', 'administrative_action',
                 'administrative_advance', 'administrative_pay', 'civic_clock',
                 'civic_disease', 'medical_snapshot', 'medical_restore'}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
        prefix = 'wurst/MedicalCareTests.wurst:'
        passed = {r['id'] for r in execution['tests'] if r['status'] == 'pass'}
        if not ({prefix + name for name in REQUIRED_TESTS} | {ROLLBACK}) <= passed:
            return set()
        world = json.loads((project / 'scenario/world/world.json').read_text())
        _, effects, metadata, _ = configuration(project, world)
        authored = {(e['unlock']['kind'], e['unlock']['contentId']):
                    (e['nodeId'], e['metric'], e['bonusBasisPoints']) for e in effects}
        observed = execution['productionCoverage']['tests']
        return {pair for pair, (system, name, probe) in COMPARISONS.items()
                if authored.get(pair) == IDENTITIES[pair]
                and prefix + name in passed and prefix + name in coverage.get(system, [])
                and COMMON_PROBES | {probe} <= set(observed.get(prefix + name, []))}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()
