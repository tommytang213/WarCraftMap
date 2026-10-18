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
        if d['id'] in ids or d['metric'] not in METRICS or d['capability'] != METRICS[d['metric']]:
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
            minimum = 0 if key in {'dailyProvisions', 'hazardLoss'} else 1
            if type(d[key]) is not int or not minimum <= d[key] <= maximum:
                raise ValueError('science: invalid ' + key)
        if d['weatherDays'] > d['weatherPeriod']:
            raise ValueError('science: invalid weather observation period')
        if (d['metric'] == 'research_generation_efficiency') != (d['forceId'] == ''):
            raise ValueError('science: scholarly facilities and journey actors are distinct')
        if d['forceId']:
            if d['forceId'] in assigned_forces:
                raise ValueError('science: actor cannot run overlapping circuits')
            assigned_forces.add(d['forceId'])
            force = forces.get(d['forceId'])
            expected_kind = 'ship' if d['metric'] == 'storm_attrition_reduction' else 'formation'
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
        if d['forceId']:
            lines.append(f"\tsite{i}.unitTypeId = '{templates[forces[d['forceId']]['runtimeInstantiation']['runtimeTemplateId']]}'")
        pos = d['stationPosition'] or [positions[d['settlementId']]['x'], positions[d['settlementId']]['y']]
        for axis, value in zip(('X', 'Y'), pos):
            if type(value) not in (int, float) or not -32768 < value < 32768:
                raise ValueError('science: invalid station position')
            lines.append(f'\tsite{i}.station{axis} = {float(value)}')
        lines.append(f'\tledger.register(site{i})')
    return '\n'.join(lines) + '\n', data | {'effects': effects}, [path, design_path, Path(__file__)]
