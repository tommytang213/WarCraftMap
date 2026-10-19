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
    data['materialGoodIds'] = ['timber','iron','ship_provisions']
    data['yardServices'] = ['port_services','market','banking','warehouse']
    data['maximumHarborDistance'] = 1024
    data['effects'] = effects
    data['rosterBlueprint'] = hull
    return data, '\n'.join(lines) + '\n'


if __name__ == '__main__':
    data, source = build()
    sources = ['scenario/naval/services.json','scenario/naval/navigation-efficiency.json','scenario/progression/gameplay-effect-design.json','tooling/naval_services_catalog.py','tooling/validate_unit_roster.py']
    sources += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'scenario/rosters').glob('*.json'))]
    print(json.dumps(dict(catalog=data, wurst=source, sources=sources)))
