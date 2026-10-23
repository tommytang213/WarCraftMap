"""Compile approved land research and actual roster equipment into shared consumers."""
import json
from pathlib import Path
from validate_unit_roster import load_catalog

ROOT = Path(__file__).resolve().parents[1]
METRICS = {'firearm_reload_efficiency': 'modifier', 'artillery_production_throughput': 'policy',
           'artillery_supply_waste_reduction': 'modifier', 'anti_cavalry_melee_defense': 'modifier'}
RULES = {'transitionDays', 'enactmentBasisPoints', 'upkeepBasisPoints', 'procurementUpkeepBasisPoints',
         'constructionDays', 'armsPerBattery', 'crewPerBattery', 'supplyPerBattery', 'shipmentArms',
         'shipmentWaste', 'supplyRadius'}


# Exact issue #550 candidates only. Bayonet research remains independently blocked.
CLOSURE_EFFECTS = {
    ('modifier', 'progression_arquebus_volley_drill'): ('arquebus_volley_drill', 'firearm_reload_efficiency', 500),
    ('policy', 'progression_artillery_offices'): ('artillery_offices', 'artillery_production_throughput', 800),
    ('modifier', 'progression_artillery_train'): ('artillery_train', 'artillery_supply_waste_reduction', 800),
}
COMMON_PROBES = {'land_registration', 'research', 'dispatch'}
COMPARATIVE_PATHS = {
    ('modifier', 'progression_arquebus_volley_drill'):
        ('land_reload', 'landReloadMatchedControlUsesAbstractDeadlinesAndNativeCooldown',
         COMMON_PROBES | {'land_reload_resolve', 'land_shot', 'land_native_reload'}),
    ('policy', 'progression_artillery_offices'):
        ('land_procurement', 'landOfficeMatchedControlRequiresEnactmentSurchargeAndRealWork',
         COMMON_PROBES | {'land_action', 'land_advance', 'land_pay', 'land_work'}),
    ('modifier', 'progression_artillery_train'):
        ('land_supply', 'landTrainMatchedControlDelivers77Versus75From100ActualStock',
         COMMON_PROBES | {'land_action', 'land_delivery'}),
}
ROLLBACK_TEST = 'wurst/CampaignLoadTransactionTests.wurst:lateLoadFailureRestoresLandArmyScienceWorkAndFiringClock'
ADAPTER_TEST = 'wurst/MilitaryCombatEventsTests.wurst:installedLandDrillAndBayonetUseProductionWeaponCallbacks'
REQUIRED_TESTS = {
    'landRegisteredResearchAndOfficeActionsChargeRealInputsAndTimeline',
    'landProductionAndSupplyRejectMissingResourcesControlRoutesAndEquipment',
    'landReloadAndBayonetAreExactEquipmentGatedAndDeduplicated',
    'landActiveAbstractReplaySnapshotMigrationAndCaptureAreIdempotent',
    'landNamedControllerSourcesAddOnceAndDoNotCrossControllers',
    'landAbstractFiringConsumesExactReloadClockAcrossReconstruction',
    'landAiUsesIdenticalLegalResearchProcurementAndWasteRules',
    'landUnfundedRenewalAndCapturedWorkCannotCreateFreeArtillery',
    'combinedLandAndScienceRecordsRoundTripAndMigrateMainVersion12',
} | {name for _, name, _ in COMPARATIVE_PATHS.values()}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    """Require current full-suite pinned execution and actual comparative outcomes."""
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
        prefix = 'wurst/LandArmyEffectsTests.wurst:'
        passed = {r['id'] for r in execution['tests'] if r['status'] == 'pass'}
        if not ({prefix + name for name in REQUIRED_TESTS} | {ROLLBACK_TEST, ADAPTER_TEST}) <= passed:
            return set()
        authored = {(e['unlock']['kind'], e['unlock']['contentId']):
                    (e['nodeId'], e['metric'], e['bonusBasisPoints'])
                    for e in build(project)['catalog']['effects']}
        observed = execution['productionCoverage']['tests']
        return {pair for pair, (system, name, probes) in COMPARATIVE_PATHS.items()
                if authored.get(pair) == CLOSURE_EFFECTS[pair]
                and prefix + name in coverage.get(system, [])
                and probes <= set(observed.get(prefix + name, []))}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()


def build(project=ROOT):
    project = Path(project)
    data = json.loads((project / 'scenario/progression/land-army.json').read_text())
    if data.get('schemaVersion') != 1 or set(data['metrics']) != set(METRICS) or set(data['rules']) != RULES:
        raise ValueError('land army: invalid schema/metrics/rules')
    for key, value in data['rules'].items():
        if type(value) is not int or not 0 < value <= 10000:
            raise ValueError('land army: invalid ' + key)
    if data['rules']['shipmentWaste'] >= data['rules']['shipmentArms']:
        raise ValueError('land army: shipment must contain actual useful ammunition')
    world = json.loads((project / 'scenario/world/world.json').read_text())
    design = json.loads((project / data['designSource']).read_text())
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    effects = [e for e in design['effects'] if e['metric'] in METRICS]
    if len(effects) != 4 or len({e['metric'] for e in effects}) != 4:
        raise ValueError('land army: missing exact approved effect')
    for e in effects:
        if (e['unlock'] not in nodes[e['nodeId']]['unlocks'] or e['unlock']['kind'] != METRICS[e['metric']]
                or type(e['bonusBasisPoints']) is not int or not 0 < e['bonusBasisPoints'] <= 10000):
            raise ValueError('land army: invalid typed effect')
    roster = load_catalog()
    pred = data['predicates']
    for key in ('firearmWeapons', 'cavalryWeapons', 'artilleryWeapons'):
        if not set(pred[key]) <= set(roster.weapons):
            raise ValueError('land army: unknown weapon')
    for key in ('firearmEquipment', 'bayonetEquipment'):
        if not set(pred[key]) <= set(roster.references['equipment']):
            raise ValueError('land army: unknown equipment')
    q = json.dumps
    lines = ['public function configureGeneratedLandArmy(LandArmyLedger ledger, LandResearchEffects research, int day)']
    lines += ['\tledger.research = research']
    for key, value in data['rules'].items():
        lines.append(f'\tledger.{key} = {value}')
    for key in ('armsGood', 'commissionProfile'):
        lines.append(f'\tledger.{key} = {q(pred[key])}')
    for e in effects:
        u = e['unlock']
        lines.append(f'\tresearch.register(new CivicEffect({q(u["kind"])}, {q(u["contentId"])}, {q(e["metric"])}, {e["bonusBasisPoints"]}))')
    profiles = []
    for ident, unit in sorted(roster.archetypes.items()):
        if unit.get('abstract') or roster.movement_classes[unit['movementClassId']]['domain'] != 'land':
            continue
        weapons = set(unit['weaponIds'])
        equipment = set(unit.get('equipmentIds', []))
        category = pred['formationCategory'] if unit['category'] in {'infantry', 'marine', 'cavalry', 'artillery'} else ''
        firearm = bool(unit['category'] in {'infantry', 'marine'} and unit['movementClassId'] == 'foot'
                       and weapons.intersection(pred['firearmWeapons']) and equipment.intersection(pred['firearmEquipment']))
        bayonet = bool(firearm and unit['category'] == 'infantry' and equipment.intersection(pred['bayonetEquipment']))
        cavalry = bool(unit['category'] == 'cavalry' and unit['movementClassId'] == 'mounted' and weapons.intersection(pred['cavalryWeapons']))
        artillery = bool(unit['category'] == 'artillery' and weapons.intersection(pred['artilleryWeapons']))
        if not category:
            continue
        if artillery:
            category = pred['formationCategory']
        availability = unit.get('availability', {})
        p = dict(id=ident, unitTypeId=roster.templates[unit['runtimeTemplateId']]['warcraftUnitTypeId'],
                 categoryId=category, firearm=firearm, bayonet=bayonet, cavalry=cavalry, artillery=artillery,
                 firstYear=availability.get('historicalStartYear', 1450), lastYear=availability.get('historicalEndYear', 1820),
                 cost=unit['cost'], strength=unit['strategicStrength'],
                 primaryNativeAttack=pred['nativeAttackByTemplate'].get(unit['runtimeTemplateId'], ''),
                 baseReloadMillis=pred['firearmReloadMillisByTemplate'].get(unit['runtimeTemplateId'], 0) if firearm else 0,
                 requiredResearch=','.join([''] + unit.get('technologyIds', []) + unit.get('institutionIds', []) + ['']))
        if any(n not in nodes for n in unit.get('technologyIds', []) + unit.get('institutionIds', [])):
            raise ValueError('land army: unregistered historical prerequisite')
        if (firearm or cavalry) and p['primaryNativeAttack'] not in {'normal', 'pierce', 'siege'}:
            raise ValueError('land army: missing primary native weapon classification')
        if firearm and (type(p['baseReloadMillis']) is not int or not 0 < p['baseReloadMillis'] <= 60000):
            raise ValueError('land army: missing firearm runtime reload interval')
        profiles.append(p)
    if pred['commissionProfile'] not in {p['id'] for p in profiles if p['artillery']}:
        raise ValueError('land army: commission requires an actual artillery roster')
    for start in range(0, len(profiles), 30):
        lines.append(f'\tconfigureLandProfiles{start}(ledger)')
    arsenal_ids = []
    settlement_ids = {row['id'] for row in world['settlements']}
    settlement_sources = sorted((project / 'scenario/settlements').glob('*-1450.json'))
    for path in settlement_sources:
        for row in json.loads(path.read_text())['settlements']:
            if pred['arsenalProductionRef'] in row.get('productionRefs', []):
                if row['id'] not in settlement_ids or row['id'] in arsenal_ids:
                    raise ValueError('land army: unknown or duplicate arsenal settlement')
                arsenal_ids.append(row['id'])
    for ident in sorted(arsenal_ids):
        lines.append('\tledger.register(' + q(ident) + ', day)')
    for start in range(0, len(profiles), 30):
        lines.append(f'\nfunction configureLandProfiles{start}(LandArmyLedger ledger)')
        for index, p in enumerate(profiles[start:start + 30]):
            values = [q(p['id']), "'" + p['unitTypeId'] + "'", q(p['categoryId'])]
            values += [str(p[k]).lower() for k in ('firearm', 'bayonet', 'cavalry', 'artillery', 'firstYear', 'lastYear', 'cost', 'strength')]
            lines += [f'\tlet profile{index} = new LandProfile(' + ', '.join(values) + ')',
                      f'\tprofile{index}.primaryNativeAttack = ' + q(p['primaryNativeAttack']),
                      f'\tprofile{index}.baseReloadMillis = ' + str(p['baseReloadMillis']),
                      f'\tprofile{index}.requiredResearch = ' + q(p['requiredResearch']), f'\tledger.registerProfile(profile{index})']
    sources = ['scenario/progression/land-army.json', data['designSource'], 'tooling/land_army_catalog.py', 'tooling/validate_unit_roster.py']
    sources += [str(p.relative_to(project)) for p in settlement_sources]
    sources += [str(p.relative_to(project)) for p in sorted((project / 'scenario/rosters').glob('*.json'))]
    authored = {(e['unlock']['kind'], e['unlock']['contentId']):
                (e['nodeId'], e['metric'], e['bonusBasisPoints']) for e in effects}
    consumers = [dict(nodeId=node, kind=pair[0], contentId=pair[1], metric=metric,
                      bonusBasisPoints=bonus, executionSystem=COMPARATIVE_PATHS[pair][0])
                 for pair, (node, metric, bonus) in CLOSURE_EFFECTS.items()
                 if authored.get(pair) == (node, metric, bonus)]
    return dict(catalog=dict(rules=data['rules'], effects=effects, consumers=consumers,
                             profiles=profiles, predicates=pred, arsenalIds=sorted(arsenal_ids)),
                wurst='\n'.join(lines) + '\n', sources=sources)


if __name__ == '__main__':
    print(json.dumps(build()))
