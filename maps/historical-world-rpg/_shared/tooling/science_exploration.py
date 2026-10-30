"""Compile scenario-owned science contracts; no scenario IDs enter shared Wurst."""
from datetime import date
import json
import re
from pathlib import Path

METRICS = {'storm_attrition_reduction': 'observed_sea_weather',
           'unknown_route_attrition_reduction': 'unknown_overland_survey',
           'research_generation_efficiency': 'active_scholarly_center'}
NUMBERS = {'equipmentCost': 1000000, 'equipmentUnits': 10000, 'equipmentDays': 365,
           'dailyMoney': 10000, 'dailyUnits': 10000, 'workRequired': 1000000,
           'dailyWork': 10000, 'dailyProvisions': 10000, 'hazardLoss': 10000,
           'weatherPeriod': 365, 'weatherDays': 365}


def configuration(project, world, settlements, authored, trade_records):
    path = project / 'scenario/progression/science-exploration.json'
    header = '\npublic function configureGeneratedScience(ScienceLedger ledger, ScienceResearchEffects effects)\n'
    if not path.is_file():
        return header + '\tskip\n', {}, []
    data = json.loads(path.read_text())
    if data.get('schemaVersion') != 1:
        raise ValueError('science: invalid schema')
    design_path = project / data['designSource']
    if not design_path.resolve().is_relative_to(project.resolve()):
        raise ValueError('science: design source escapes scenario')
    effects = [e for e in json.loads(design_path.read_text())['effects'] if e['metric'] in METRICS]
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    if {e['metric'] for e in effects} != set(METRICS) or len(effects) != 3:
        raise ValueError('science: missing effect contract')
    observation_path = project / 'scenario/progression/chemical-classification.json'
    observation = None
    if observation_path.is_file():
        observation = json.loads(observation_path.read_text())
        node = nodes.get(observation.get('nodeId'), {})
        if (observation.get('schemaVersion') != 1
                or observation.get('unlock') not in node.get('unlocks', [])
                or observation['unlock']['kind'] != 'modifier'
                or observation.get('metric') != 'repeatable_observation_efficiency'
                or type(observation.get('bonusBasisPoints')) is not int
                or not 300 <= observation['bonusBasisPoints'] <= 600
                or type(observation.get('minimumAdministration')) is not int
                or not 1 <= observation['minimumAdministration'] <= 100):
            raise ValueError('science: invalid observation contract')
        effects.append(observation)
    lines = [header]
    q = json.dumps
    for e in effects:
        if (e['unlock'] not in nodes[e['nodeId']]['unlocks'] or e['unlock']['kind'] != 'modifier'
                or type(e['bonusBasisPoints']) is not int or not 0 < e['bonusBasisPoints'] < 10000):
            raise ValueError('science: invalid exact typed binding')
        lines.append(f'\teffects.register(new CivicEffect("modifier", {q(e["unlock"]["contentId"])}, {q(e["metric"])}, {e["bonusBasisPoints"]}))')
    if not 0 < len(data['sites']) <= 64:
        raise ValueError('science: invalid site count')
    ids = set()
    assigned_forces = set()
    forces = {x['id']: x for x in world['strategicUnits']}
    templates = {x['id']: x['warcraftUnitTypeId'] for x in world['militaryRuntimeTemplates']}
    positions = {x['id']: x for x in settlements}
    zones = {x['id']: x for x in world['navigationZones']}
    nav = json.loads((project / 'scenario/naval/navigation-efficiency.json').read_text())
    for i, d in enumerate(data['sites']):
        commissioning = d.get('commissioningOnly', False)
        if type(commissioning) is not bool:
            raise ValueError('science: invalid commissioning flag')
        coastal = commissioning is True and d['metric'] == 'coastal_position_finding' and d['capability'] == 'coastal_chart_bearings'
        if commissioning and not coastal:
            raise ValueError('science: unsupported commissioning capability')
        if d['id'] in ids or (not coastal and (d['metric'] not in METRICS or d['capability'] != METRICS[d['metric']])):
            raise ValueError('science: duplicate site or unsupported capability')
        if len(d['id']) > 64 or not re.fullmatch(r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*', d['id']):
            raise ValueError('science: invalid stable site id')
        ids.add(d['id'])
        if d['settlementId'] not in authored or d['settlementId'] not in positions or d['prerequisite'] not in nodes:
            raise ValueError('science: missing facility or prerequisite')
        row = authored[d['settlementId']][1]
        if not {'capital', 'trade_center'} & set(row['roles']) or 'market' not in row['services']:
            raise ValueError('science: facility lacks scholarly/market services')
        if not any(f'runtime.registerMarketProfile({q(d["settlementId"])},{q(d["good"])},' in x for x in trade_records):
            raise ValueError('science: required real commodity market unavailable')
        for key, maximum in NUMBERS.items():
            minimum = 0 if key in {'dailyProvisions', 'hazardLoss'} or coastal and key in {'dailyMoney', 'dailyUnits', 'dailyWork'} else 1
            if type(d[key]) is not int or not minimum <= d[key] <= maximum:
                raise ValueError('science: invalid ' + key)
        if d['weatherDays'] > d['weatherPeriod']:
            raise ValueError('science: invalid weather observation period')
        if (d['metric'] == 'research_generation_efficiency') != (d['forceId'] == ''):
            raise ValueError('science: scholarly facilities and journey actors are distinct')
        if d['forceId']:
            if not coastal and d['forceId'] in assigned_forces:
                raise ValueError('science: actor cannot run overlapping circuits')
            assigned_forces.add(d['forceId'])
            force = forces.get(d['forceId'])
            expected_kind = 'ship' if d['metric'] == 'storm_attrition_reduction' or coastal else 'formation'
            if not force or force['kind'] != expected_kind:
                raise ValueError('science: incompatible actor')
            if expected_kind == 'ship':
                ship = next((s for s in nav['ships'] if s['forceId'] == d['forceId']), None)
                if not ship or d['routeId'] not in ship['routeIds'] or d['stationPosition'] != ship['stationPosition'] or not row.get('port'):
                    raise ValueError('science: incompatible sea route/equipment capability')
            elif not d.get('routeZoneIds') or any(z not in zones or 'land' not in zones[z]['movementClasses'] for z in d['routeZoneIds']):
                raise ValueError('science: incompatible unknown overland route')
        elif d['metric'] != 'research_generation_efficiency':
            raise ValueError('science: hazard requires a real actor')
        first = date.fromisoformat(d['firstDate']).toordinal()
        args = [d[k] for k in ('id', 'settlementId', 'forceId', 'metric', 'prerequisite', 'good')] + [first] + [d[k] for k in NUMBERS]
        render = lambda v: q(v) if isinstance(v, str) else str(v)
        lines.append(f'\tlet site{i} = new ScienceSite(' + ', '.join(map(render, args)) + ')')
        if coastal:
            if any(d[k] != 0 for k in ('dailyMoney', 'dailyUnits', 'dailyWork', 'dailyProvisions', 'hazardLoss')):
                raise ValueError('science: commissioning cannot run a second voyage')
            lines.append(f'\tsite{i}.commissioningOnly = true')
        if d['forceId']:
            lines.append(f"\tsite{i}.unitTypeId = '{templates[forces[d['forceId']]['runtimeInstantiation']['runtimeTemplateId']]}'")
        pos = d['stationPosition'] or [positions[d['settlementId']]['x'], positions[d['settlementId']]['y']]
        for axis, value in zip(('X', 'Y'), pos):
            if type(value) not in (int, float) or not -32768 < value < 32768:
                raise ValueError('science: invalid station position')
            lines.append(f'\tsite{i}.station{axis} = {float(value)}')
        if observation and d['id'] == observation['siteId']:
            if d['metric'] != 'research_generation_efficiency':
                raise ValueError('science: observations require a scholarly facility')
            targets = sorted(n['id'] for n in world['technologies']
                             if n.get('branchId') == observation['targetBranchId'])
            if not targets:
                raise ValueError('science: observations require scientific targets')
            lines.append(f'\tsite{i}.observationMetric = {q(observation["metric"])}')
            lines.append(f'\tsite{i}.observationTargets = {q("|" + "|".join(targets) + "|")}')
            lines.append(f'\tsite{i}.minimumAdministration = {observation["minimumAdministration"]}')
        lines.append(f'\tledger.register(site{i})')
    if observation and observation['siteId'] not in ids:
        raise ValueError('science: missing observation facility')
    return '\n'.join(lines) + '\n', data | {'effects': effects}, [path, design_path, Path(__file__)] + ([observation_path] if observation else [])


CHEMICAL_TESTS = {
    'chemicalRegisteredResearchCommitsExactScientificWorkAgainstIdenticalControl',
    'chemicalQualifiedWorkRejectsMissingFacilitiesStaffInputsTechnologyAndUnauthorizedControl',
    'chemicalNamedSourceCompositionRoundingRepeatGrantsAndAheadOfTimeAccess',
    'chemicalActiveAbstractResumeCaptureAndMalformedLoadPreserveExactAuthority',
    'chemicalFailedCampaignLoadRollsBackWorkFractionInputsAndEarnedSource',
}

BAROMETRIC_COMPARISON = 'barometricOnlyRegisteredVoyageCommitsExactStormLossAgainstMatchedControl'
BAROMETRIC_TESTS = {
    BAROMETRIC_COMPARISON,
    'barometricCalmWeatherAndUnfundedDaysCannotCreateAvoidanceOrPartialBills',
    'barometricVoyageRejectsMissingInstrumentsTechnologyVesselRouteAndLawfulControl',
    'barometricFractionsResumeReconstructAndCaptureWithPlayerAiParity',
    'barometricFailedCampaignLoadRollsBackSupplyFractionBillsAndResearch',
    'scienceNamedSourcesDeduplicateAndDistinctSourcesStackOnlyInTheirMetricBucket',
    'scienceActiveAbstractSaveMigrationCaptureAndMalformedLoadKeepAuthorityExact',
}
BAROMETRIC_PROBES = {'research', 'dispatch', 'science_registration', 'science_action',
                     'science_advance', 'science_pay', 'science_weather',
                     'science_supply', 'science_hazard_commit'}
BAROMETRIC_UNLOCK = {'kind': 'modifier', 'contentId': 'progression_barometric_measurement'}

BOTANICAL_COMPARISON = 'botanicalOnlyRegisteredSurveyCommitsExactHazardLossAgainstMatchedControl'
BOTANICAL_TESTS = {
    BOTANICAL_COMPARISON,
    'botanicalUnfundedDaysCannotCreateAvoidanceFractionsOrPartialBills',
    'botanicalSurveyRejectsMissingEquipmentResearchFormationRouteAndLawfulControl',
    'botanicalFractionsResumeReconstructAndCaptureWithPlayerAiParity',
    'botanicalFailedCampaignLoadRollsBackSupplyFractionBillsAndResearch',
    'botanicalNamedSourcesDeduplicateAndUnrelatedResearchCannotReduceSurveyLoss',
    'scienceActiveAbstractSaveMigrationCaptureAndMalformedLoadKeepAuthorityExact',
}
BOTANICAL_PROBES = {'research', 'dispatch', 'science_registration', 'science_action',
                    'science_advance', 'science_pay', 'science_weather',
                    'science_supply', 'science_hazard_commit'}
BOTANICAL_UNLOCK = {'kind': 'modifier', 'contentId': 'progression_botanical_collecting'}



CALCULUS_COMPARISON = 'calculusOnlyRegisteredScholarshipCommitsExactWorkAndCompletionAgainstMatchedControl'
CALCULUS_TESTS = {
    CALCULUS_COMPARISON,
    'calculusScholarshipRejectsMissingPrerequisitesFacilitiesStaffAndInputs',
    'calculusNamedSourcesDeduplicateAndConditionalClassificationAddsOnce',
    'calculusFractionsResumeCaptureAndActiveInactivePlayerAiEquivalence',
    'calculusCompletionRevalidatesTargetAndDeliversUnlocksOnce',
    'calculusFailedCampaignLoadRollsBackWorkPaymentsCompletionAndEntitlements',
    'scienceActiveAbstractSaveMigrationCaptureAndMalformedLoadKeepAuthorityExact',
}
CALCULUS_PROBES = {'research', 'dispatch', 'science_registration', 'science_action',
                   'science_advance', 'science_pay', 'science_research_bill',
                   'science_work_commit', 'science_complete'}
CALCULUS_UNLOCK = {'kind': 'modifier', 'contentId': 'progression_calculus_methods'}


def _calculus_authored(project):
    """Only the approved scholarly source and exact integer coefficient qualify."""
    data = json.loads((project / 'scenario/progression/science-exploration.json').read_text())
    path = (project / data['designSource']).resolve()
    path.relative_to(project.resolve())
    effects = [e for e in json.loads(path.read_text())['effects']
               if e['nodeId'] == 'calculus_methods' or e['unlock'] == CALCULUS_UNLOCK]
    if len(effects) != 1:
        return False
    effect = effects[0]
    world = json.loads((project / 'scenario/world/world.json').read_text())
    nodes = [n for n in world['technologies'] if n['id'] == 'calculus_methods']
    return (effect['nodeId'] == 'calculus_methods'
            and effect['unlock'] == CALCULUS_UNLOCK
            and effect['metric'] == 'research_generation_efficiency'
            and effect['family'] == 'science'
            and type(effect['bonusBasisPoints']) is int and effect['bonusBasisPoints'] == 500
            and effect['activation'] == 'passive_research'
            and effect['recipient'] == 'controlled_scholarly_research_centers'
            and len(nodes) == 1 and CALCULUS_UNLOCK in nodes[0]['unlocks'])


def _botanical_authored(project):
    """Recognize only the approved overland source, not a sibling science metric."""
    data = json.loads((project / 'scenario/progression/science-exploration.json').read_text())
    path = (project / data['designSource']).resolve()
    path.relative_to(project.resolve())
    effects = [e for e in json.loads(path.read_text())['effects']
               if e['nodeId'] == 'botanical_collecting' or e['unlock'] == BOTANICAL_UNLOCK]
    if len(effects) != 1:
        return False
    effect = effects[0]
    world = json.loads((project / 'scenario/world/world.json').read_text())
    nodes = [n for n in world['technologies'] if n['id'] == 'botanical_collecting']
    return (effect['nodeId'] == 'botanical_collecting'
            and effect['unlock'] == BOTANICAL_UNLOCK
            and effect['metric'] == 'unknown_route_attrition_reduction'
            and type(effect['bonusBasisPoints']) is int and effect['bonusBasisPoints'] == 1000
            and effect['activation'] == 'passive_research'
            and effect['recipient'] == 'qualified_overland_exploration_parties'
            and len(nodes) == 1 and BOTANICAL_UNLOCK in nodes[0]['unlocks'])


def _barometric_authored(project):
    """The approved identity and coefficient, never inferred from a similar metric."""
    data = json.loads((project / 'scenario/progression/science-exploration.json').read_text())
    path = (project / data['designSource']).resolve()
    path.relative_to(project.resolve())
    effects = [e for e in json.loads(path.read_text())['effects']
               if e['nodeId'] == 'barometric_measurement'
               or e['unlock'] == BAROMETRIC_UNLOCK]
    if len(effects) != 1:
        return False
    effect = effects[0]
    world = json.loads((project / 'scenario/world/world.json').read_text())
    nodes = [n for n in world['technologies'] if n['id'] == 'barometric_measurement']
    return (effect['nodeId'] == 'barometric_measurement'
            and effect['unlock'] == BAROMETRIC_UNLOCK
            and effect['metric'] == 'storm_attrition_reduction'
            and type(effect['bonusBasisPoints']) is int and effect['bonusBasisPoints'] == 1000
            and effect['activation'] == 'passive_research'
            and effect['recipient'] == 'qualified_sea_voyages'
            and len(nodes) == 1 and BAROMETRIC_UNLOCK in nodes[0]['unlocks'])


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    """Only current complete pinned execution can close this exact finding."""
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError):
        return set()
    prefix = 'wurst/ScienceExplorationTests.wurst:'
    passed = {row['id'][len(prefix):] for row in execution['tests']
              if row['status'] == 'pass' and row['id'].startswith(prefix)}
    probes = execution.get('productionCoverage', {}).get('tests', {})
    required = {'science_registration', 'science_action', 'science_advance',
                'science_pay', 'science_complete', 'dispatch'}
    comparative = prefix + 'chemicalRegisteredResearchCommitsExactScientificWorkAgainstIdenticalControl'
    bound = set()
    if CHEMICAL_TESTS <= passed and required <= set(probes.get(comparative, [])):
        contract = json.loads((project / 'scenario/progression/chemical-classification.json').read_text())
        bound.add((contract['unlock']['kind'], contract['unlock']['contentId']))
    comparative = prefix + BAROMETRIC_COMPARISON
    try:
        if (BAROMETRIC_TESTS <= passed
                and comparative in coverage.get('barometric_voyage', [])
                and BAROMETRIC_PROBES <= set(probes.get(comparative, []))
                and _barometric_authored(project)):
            bound.add(('modifier', 'progression_barometric_measurement'))
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        pass
    comparative = prefix + BOTANICAL_COMPARISON
    try:
        if (BOTANICAL_TESTS <= passed
                and comparative in coverage.get('botanical_survey', [])
                and BOTANICAL_PROBES <= set(probes.get(comparative, []))
                and _botanical_authored(project)):
            bound.add(('modifier', 'progression_botanical_collecting'))
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        pass
    comparative = prefix + CALCULUS_COMPARISON
    try:
        if (CALCULUS_TESTS <= passed
                and comparative in coverage.get('calculus_scholarship', [])
                and CALCULUS_PROBES <= set(probes.get(comparative, []))
                and _calculus_authored(project)):
            bound.add(('modifier', 'progression_calculus_methods'))
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        pass
    return bound
