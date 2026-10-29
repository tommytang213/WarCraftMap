"""Compile paid naval services against the approved design and resolved roster."""
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / '_shared/engine'))
from validate_unit_roster import load_catalog

METRICS = {'unlock_recruitment', 'hull_repair_throughput',
           'close_range_naval_gunfire_damage', 'voyage_hull_weather_resilience'}


def commissioning_consumers(data):
    """Exact closure candidates, separate from the other registered naval effects.

    Bills and eligibility come from the resolved roster and scenario recipes.
    This metadata describes the consumer; execution remains a separate gate.
    """
    candidates = [e for e in data['effects'] if e['nodeId'] == 'battlefleet_doctrine'
                  or e['unlock'] == {'kind': 'unit', 'contentId': 'ship_of_the_line'}]
    hull = data['rosterBlueprint']
    if len(candidates) != 1:
        return []
    effect = candidates[0]
    if (effect['nodeId'] != 'battlefleet_doctrine'
            or effect['unlock'] != {'kind': 'unit', 'contentId': 'ship_of_the_line'}
            or effect['metric'] != 'unlock_recruitment'
            or type(effect['bonusBasisPoints']) is not int or effect['bonusBasisPoints'] != 0
            or effect['activation'] != 'commissioning_unlock'
            or effect['recipient'] != 'qualified_warship_yards'
            or hull['id'] != 'ship_of_the_line_generic'
            or effect['nodeId'] not in hull['technologyIds']):
        return []
    return [dict(nodeId=effect['nodeId'], **effect['unlock'], metric=effect['metric'],
                 rosterId=hull['id'], action='build', executionSystem='naval_commissioning',
                 dockPrerequisites=sorted({y['prerequisite'] for y in data['yards']}),
                 boardRequired=True, requiredResearch=hull['technologyIds'] + hull['institutionIds'],
                 availability=hull['availability'], currency=hull['cost'], upkeep=hull['upkeep'],
                 provisions=hull['supply'], manpower=data['crewStrength'],
                 timber=data['rules']['buildWood'], iron=data['rules']['buildIron'],
                 constructionDays=data['constructionDays'])]


def repair_consumers(data):
    """Careening is a paid repair consumer, independently verified from builds."""
    candidates = [e for e in data['effects'] if e['nodeId'] == 'careening_stations'
                  or e['unlock'] == {'kind': 'modifier', 'contentId': 'progression_careening_stations'}]
    if len(candidates) != 1:
        return []
    effect = candidates[0]
    if (effect['nodeId'] != 'careening_stations'
            or effect['unlock'] != {'kind': 'modifier', 'contentId': 'progression_careening_stations'}
            or effect['metric'] != 'hull_repair_throughput'
            or type(effect['bonusBasisPoints']) is not int or effect['bonusBasisPoints'] != 1500
            or effect['activation'] != 'passive_research'
            or effect['recipient'] != 'ships_at_operational_careening_ports'):
        return []
    return [dict(nodeId=effect['nodeId'], **effect['unlock'], metric=effect['metric'],
                 bonusBasisPoints=effect['bonusBasisPoints'], recipient=effect['recipient'],
                 action='repair', executionSystem='naval_repair',
                 dockPrerequisites=sorted({y['prerequisite'] for y in data['yards']}),
                 operationalDockRequired=True, ownedDocksideRecipientRequired=True,
                 currency=data['rules']['repairCost'], timber=data['rules']['repairWood'],
                 provisions=1, localSupply=1, baseOutput=data['rules']['repairOutput'],
                 billing='per_funded_day', maximumIntegrity=10000,
                 outputBound='actual_missing_hull', ordinaryMaintenanceIndependent=True)]


def carvel_consumers(data):
    """Describe actual voyage hull losses, independently of repair and combat."""
    candidates = [e for e in data['effects'] if e['nodeId'] == 'carvel_hull_construction'
                  or e['unlock'] == {'kind': 'modifier', 'contentId': 'progression_carvel_hull_construction'}]
    if len(candidates) != 1:
        return []
    effect = candidates[0]
    if (effect['nodeId'] != 'carvel_hull_construction'
            or effect['unlock'] != {'kind': 'modifier', 'contentId': 'progression_carvel_hull_construction'}
            or effect['metric'] != 'voyage_hull_weather_resilience'
            or type(effect['bonusBasisPoints']) is not int or effect['bonusBasisPoints'] != 800
            or effect['activation'] != 'passive_research'
            or effect['recipient'] != 'carvel_hulled_or_validly_refitted_vessels'):
        return []
    rules = data['rules']
    return [dict(nodeId=effect['nodeId'], **effect['unlock'], metric=effect['metric'],
                 bonusBasisPoints=effect['bonusBasisPoints'], recipient=effect['recipient'],
                 action='voyage', executionSystem='naval_carvel', firstDate=data['carvelFirstDate'],
                 builtProfiles=data['carvelBuiltProfiles'], refitProfiles=data['carvelRefitProfiles'],
                 refit=dict(currency=rules['carvelCost'], timber=rules['carvelWood'],
                            iron=rules['carvelIron'], days=rules['carvelDays']),
                 weather=dict(exposure=rules['stormLoss'], period=rules['weatherPeriod'],
                              exposedDays=rules['weatherDays']),
                 currentOwnerResearchRequired=True, fundedMaintenanceRequired=True,
                 completedCompatibleHullRequired=True, outputBound='actual_voyage_hull_weather_loss',
                 provisionsIndependent=True, navigationIndependent=True, combatIndependent=True)]


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    from naval_commissioning import verified_consumers as commissioning
    from naval_repair import verified_consumers as repairs
    from naval_carvel import verified_consumers as carvel
    # Keep commissioning's evidence restricted to its original consumer.
    def candidates(system):
        return lambda: [c for c in build(project)[0]['consumers'] if c['executionSystem'] == system]
    return (commissioning(project, candidates('naval_commissioning'), execution, execution_log, revision)
            | repairs(project, candidates('naval_repair'), execution, execution_log, revision)
            | carvel(project, candidates('naval_carvel'), execution, execution_log, revision))


def build(project=ROOT):
    project = Path(project)
    data = json.loads((project / 'scenario/naval/services.json').read_text())
    design_path = (project / data['designSource']).resolve()
    if not design_path.is_relative_to(project.resolve()) or data['schemaVersion'] != 1:
        raise ValueError('naval: invalid design source or schema')
    design = json.loads(design_path.read_text())
    effects = [e for e in design['effects'] if e['metric'] in METRICS]
    if len(effects) != 4 or {e['metric'] for e in effects} != METRICS:
        raise ValueError('naval: missing effect contract')
    roster = load_catalog()
    hull = roster.archetypes[data['blueprint']]
    if (hull['countryId'] is not None or hull['category'] != 'warship' or not hull['portRequired']
            or hull['equipmentIds'] != ['naval_ordnance'] or hull['reformIds'] != ['permanent_naval_board']
            or hull['resourceIds'] != ['ship_provisions']):
        raise ValueError('naval: blueprint requires an unsupported roster predicate')
    world = json.loads((project / 'scenario/world/world.json').read_text())
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    for e in effects:
        bp = e['bonusBasisPoints']
        if (e['unlock'] not in nodes[e['nodeId']]['unlocks']
                or (e['metric'] == 'unlock_recruitment') != (e['unlock']['kind'] == 'unit')
                or (type(bp) is not int or not 0 <= bp < 10000 or (bp == 0) != (e['metric'] == 'unlock_recruitment'))):
            raise ValueError('naval: invalid exact typed binding')
    if any(type(v) is not int or not 0 < v <= 10000 for v in data['rules'].values()):
        raise ValueError('naval: invalid calibration')
    if not 1 <= data['constructionDays'] <= 3650 or data['rules']['weatherDays'] > data['rules']['weatherPeriod']:
        raise ValueError('naval: invalid duration')
    if data['rules']['repairOutput'] * 20000 >= 2147483647 or data['rules']['stormLoss'] * 10000 >= 2147483647:
        raise ValueError('naval: fixed-point range exceeded')
    q = json.dumps
    lines = ['public function configureGeneratedNaval(NavalLedger ledger, NavalResearchEffects effects)']
    lines.append('\tledger.defaultEntitlement = ' + q(next(e['unlock']['contentId'] for e in effects if e['metric'] == 'unlock_recruitment')))
    for field, good in [('woodGood','timber'),('ironGood','iron'),('supplyGood','ship_provisions')]:
        lines.append(f'\tledger.{field} = {q(good)}')
    for e in effects:
        lines.append('\teffects.register(new CivicEffect(' + ', '.join((q(e['unlock']['kind']), q(e['unlock']['contentId']), q(e['metric']), str(e['bonusBasisPoints'] or 0))) + '))')
    for k,v in data['rules'].items():
        lines.append(f'\tledger.{k} = {v}' + ('.' if k == 'closeRange' else ''))
    lines += [f'\tledger.buildDays = {data["constructionDays"]}',
              f'\tledger.mountFirstDay = {date.fromisoformat(data["mountFirstDate"]).toordinal()}',
              f'\tledger.carvelFirstDay = {date.fromisoformat(data["carvelFirstDate"]).toordinal()}']
    profile_ids = set()
    for key in ('carvelBuiltProfiles','carvelRefitProfiles','carronadeMountProfiles'):
        if len(data[key]) != len(set(data[key])) or not set(data[key]) <= set(roster.archetypes):
            raise ValueError('naval: unknown or duplicate hull profile')
        profile_ids.update(data[key])
    for ident in sorted(profile_ids):
        row = roster.archetypes[ident]
        if not row.get('shipId') or roster.movement_classes[row['movementClassId']]['domain'] != 'naval':
            raise ValueError('naval: invalid hull profile')
        if ident in data['carronadeMountProfiles'] and ('broadside' not in row['abilityIds'] or row['category'] != 'warship' or not {'heavy_broadside','naval_guns'}.intersection(row['weaponIds'])):
            raise ValueError('naval: incompatible carronade battery')
        rawcode = roster.templates[row['runtimeTemplateId']]['warcraftUnitTypeId']
        flags = [str(ident in data[k]).lower() for k in ('carvelBuiltProfiles','carvelRefitProfiles','carronadeMountProfiles')]
        lines.append(f'\tledger.addProfile(new NavalProfile({q(ident)}, \'{rawcode}\', '+', '.join(flags)+'))')
    # Keep all other naval profiles repairable, without inventing hull/gear identity.
    for ident, row in roster.archetypes.items():
        if row.get('shipId') and ident not in profile_ids:
            rawcode = roster.templates[row['runtimeTemplateId']]['warcraftUnitTypeId']
            lines.append(f'\tledger.addProfile(new NavalProfile({q(ident)}, \'{rawcode}\', false, false, false))')
    nav = json.loads((project / 'scenario/naval/navigation-efficiency.json').read_text())
    settlements = {s['id']: s for p in (project / 'scenario/settlements').glob('*-1450.json') for s in json.loads(p.read_text())['settlements']}
    ids = set()
    if not 1 <= len(data['yards']) <= 64:
        raise ValueError('naval: invalid yard count')
    for yard in data['yards']:
        ident = yard['settlementId']; row = settlements[ident]
        station = next(s for s in nav['ships'] if s['forceId'] == yard['stationForceId'])
        if ident in ids or not row.get('port') or not {'port_services','market','banking','warehouse'} <= set(row['services']) or yard['prerequisite'] not in nodes:
            raise ValueError('naval: yard lacks real port, banking or supporting services')
        ids.add(ident)
        if row['physicalMapId'] != station['mapId']:
            raise ValueError('naval: wrong-map station')
        requirements = '|' + '|'.join(hull['technologyIds'] + hull['institutionIds']) + '|'
        first_year = hull['availability']['earlyAccessYear'] # early tech requirements remain mandatory
        if not set(hull['availability']['earlyAccessTechnologyIds']) <= set(hull['technologyIds']):
            raise ValueError('naval: unsupported early-access predicate')
        args = [q(ident), q(station['mapId']), *(str(float(v)) for v in station['stationPosition']), q(yard['prerequisite']), q(requirements), q(hull['id']), "'"+roster.templates[hull['runtimeTemplateId']]['warcraftUnitTypeId']+"'", str(date(first_year,1,1).toordinal()), str(date(hull['availability']['historicalEndYear'],12,31).toordinal()), str(hull['cost']),str(hull['upkeep']),str(hull['supply']),str(roster.ships[hull['shipId']]['crewStrength']),str(hull['strategicStrength'])]
        lines.append('\tledger.register(new NavalYard(' + ', '.join(args) + '))')
    recruitment_path = project / 'scenario/naval/recruitment.json'
    recruitment = json.loads(recruitment_path.read_text())
    if recruitment.get('schemaVersion') != 1 or not recruitment.get('blueprints'):
        raise ValueError('naval: invalid recruitment contracts')
    seen = set()
    for binding in recruitment['blueprints']:
        row = roster.archetypes[binding['rosterId']]
        unlock = {'kind': 'unit', 'contentId': binding['contentId']}
        if (row['id'] in seen or unlock not in nodes[binding['nodeId']]['unlocks']
                or row['category'] != 'merchant' or row.get('countryId') is not None
                or row.get('equipmentIds') or row.get('reformIds') or row.get('resourceIds')
                or not row.get('shipId') or roster.movement_classes[row['movementClassId']]['domain'] != 'naval'
                or not set(row['availability']['earlyAccessTechnologyIds']) <= set(row['technologyIds'])):
            raise ValueError('naval: unsupported merchant recruitment predicates')
        lines.append('\teffects.register(new CivicEffect("unit", ' + q(binding['contentId']) + ', "merchant_unlock_recruitment", 0))')
        seen.add(row['id'])
        requirements = '|' + '|'.join(row['technologyIds'] + row['institutionIds']) + '|'
        args = [q(row['id']), '""', '0.', '0.', '""', q(requirements), q(row['id']),
                "'" + roster.templates[row['runtimeTemplateId']]['warcraftUnitTypeId'] + "'",
                str(date(row['availability']['earlyAccessYear'], 1, 1).toordinal()),
                str(date(row['availability']['historicalEndYear'], 12, 31).toordinal()),
                str(row['cost']), str(row['upkeep']), str(row['supply']),
                str(roster.ships[row['shipId']]['crewStrength']), str(row['strategicStrength'])]
        lines.append('\tlet recruitment = new NavalYard(' + ', '.join(args) + ')')
        lines.append('\trecruitment.entitlement = ' + q(binding['contentId']))
        lines.append('\trecruitment.boardRequired = false')
        lines.append('\tledger.addBlueprint(recruitment)')
    data['recruitment'] = recruitment['blueprints']
    data['recruitmentBlueprints'] = [roster.archetypes[b['rosterId']] for b in recruitment['blueprints']]
    data['materialGoodIds'] = ['timber','iron','ship_provisions']
    data['yardServices'] = ['port_services','market','banking','warehouse']
    data['maximumHarborDistance'] = 1024
    data['effects'] = effects
    data['rosterBlueprint'] = hull
    data['crewStrength'] = roster.ships[hull['shipId']]['crewStrength']
    data['consumers'] = commissioning_consumers(data) + repair_consumers(data) + carvel_consumers(data)
    return data, '\n'.join(lines) + '\n'


if __name__ == '__main__':
    data, source = build()
    sources = ['scenario/naval/recruitment.json','scenario/naval/services.json','scenario/naval/navigation-efficiency.json','scenario/progression/gameplay-effect-design.json','tooling/naval_services_catalog.py','tooling/validate_unit_roster.py']
    sources += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'scenario/rosters').glob('*.json'))]
    print(json.dumps(dict(catalog=data, wurst=source, sources=sources)))
