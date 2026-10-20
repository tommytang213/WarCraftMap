"""Compile qualified industrial sites from authored production, never town count.

Raw `iron` is the existing ore/feedstock aggregate; output is manufactured
`iron_goods`. Missing supply/output markets start empty and have no liquidity.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = {'iron_refining_yield', 'gun_barrel_production_throughput'}


def build(project=ROOT):
    project = Path(project)
    relative = 'scenario/progression/industry.json'
    data = json.loads((project / relative).read_text())
    if set(data['setup']) != {'days', 'money', 'equipment', 'fuel', 'workers'} or set(data['daily']) != {'money', 'supply'}:
        raise ValueError('industry: invalid setup/daily fields')
    if data.get('schemaVersion') != 1 or {r['metric'] for r in data['recipes']} != METRICS or len(data['recipes']) != 2:
        raise ValueError('industry: invalid schema/recipes')
    for group in ('setup', 'daily'):
        for value in data[group].values():
            if type(value) is not int or not 0 < value <= 10000:
                raise ValueError('industry: invalid cost or duration')
    world = json.loads((project / 'scenario/world/world.json').read_text())
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    goods = {g['id']: g for g in json.loads((project / 'scenario/economy/global-goods.json').read_text())['goods']}
    design = json.loads((project / data['designSource']).read_text())
    effects = [e.copy() for e in design['effects'] if e['metric'] in METRICS]
    if len(effects) != 2 or {e['metric'] for e in effects} != METRICS:
        raise ValueError('industry: missing or duplicate approved effect')
    for e in effects:
        n = nodes[e['nodeId']]
        if e['unlock']['kind'] != 'modifier' or e['unlock'] not in n['unlocks'] or type(e['bonusBasisPoints']) is not int or not 0 < e['bonusBasisPoints'] <= 10000:
            raise ValueError('industry: invalid typed effect')
        e['firstYear'] = n['timeCost']['preferredYear']
    if data['fuelGood'] == data['equipmentGood'] or not {data['fuelGood'], data['equipmentGood']} <= goods.keys():
        raise ValueError('industry: invalid fuel/equipment')
    for r in data['recipes']:
        for key in ('firstYear', 'inputUnits', 'fuelUnits', 'wearUnits', 'money', 'outputUnits', 'workRequired', 'dailyWork'):
            if type(r[key]) is not int or not 0 < r[key] <= 10000:
                raise ValueError('industry: invalid recipe quantity')
        if r.get('mode') not in {'yield', 'throughput'} or r['dailyWork'] > r['workRequired'] or r['prerequisite'] not in nodes:
            raise ValueError('industry: invalid work/prerequisite')
        identities = {r['inputGood'], r['outputGood'], data['fuelGood'], data['equipmentGood']}
        if len(identities) != 4 or not identities <= goods.keys():
            raise ValueError('industry: invalid material/output identities')
        if r['productionRef'] not in goods:
            raise ValueError('industry: unknown industrial production')
        if r['metric'] == 'iron_refining_yield' and r['outputUnits'] * 2 > r['inputUnits']:
            raise ValueError('industry: refining must consume real feedstock with bounded recovery')
    sites = []
    paths = sorted((project / 'scenario/settlements').glob('*-1450.json'))
    settlement_ids = {s['id'] for s in world['settlements']}
    seen = set()
    for path in paths:
        for s in json.loads(path.read_text())['settlements']:
            production = s.get('economy', {}).get('production', s.get('productionRefs', []))
            for r in data['recipes']:
                if r['productionRef'] in production and set(data['requiredServices']) <= set(s.get('services', [])):
                    ident = r['id'] + ':' + s['id']
                    if s['id'] not in settlement_ids or ident in seen:
                        raise ValueError('industry: unknown/duplicate facility')
                    seen.add(ident)
                    sites.append(dict(r, id=ident, settlementId=s['id']))
    sites.sort(key=lambda s: s['id'])
    if not sites or len(sites) > 64:
        raise ValueError('industry: facility capacity')
    q = json.dumps
    lines = ['\npublic function configureGeneratedIndustry(IndustryLedger ledger, IndustryResearchEffects effects)']
    for key, value in data['setup'].items():
        lines.append(f'\tledger.setup{key.title()} = {value}')
    for key, value in data['daily'].items():
        lines.append(f'\tledger.daily{key.title()} = {value}')
    for key in ('fuelGood', 'equipmentGood'):
        lines.append(f'\tledger.{key} = {q(data[key])}')
    for e in effects:
        u = e['unlock']
        lines.append(f'\teffects.registerIndustrial(new CivicEffect({q(u["kind"])}, {q(u["contentId"])}, {q(e["metric"])}, {e["bonusBasisPoints"]}), {e["firstYear"]})')
    for s in sites:
        args = [q(s[k]) for k in ('id', 'settlementId', 'metric', 'prerequisite', 'inputGood', 'outputGood')]
        args += [str(s[k]) for k in ('firstYear', 'inputUnits', 'fuelUnits', 'wearUnits', 'money', 'outputUnits', 'workRequired', 'dailyWork')]
        args.append(str(s['mode'] == 'yield').lower())
        lines.append('\tledger.register(new IndustrySite(' + ', '.join(args) + '))')
    lines += ['\npublic function configureGeneratedIndustryMarkets(PlayableTradeRuntime runtime)']
    # Add definitions for imported inputs and finished products, with no grants.
    defaults = json.loads((project / 'scenario/economy/playable-trade.json').read_text())['marketDefaults']
    pairs = sorted({(s['settlementId'], g) for s in sites for g in (s['inputGood'], s['outputGood'], data['fuelGood'], data['equipmentGood'])})
    for ident, good in pairs:
        g = goods[good]
        lines += [f'\tif runtime.findMarket({q(ident)}, {q(good)}) == null',
                  f'\t\truntime.registerMarketProfile({q(ident)}, {q(good)}, 0, 0, {g["basePriceMinor"]}, 1000, 1000, 0, {g["quantityUnitsPerDisplayUnit"]}, {g["priceElasticityPermille"]}, {defaults["spreadPermille"]}, {defaults["priceFloorPermille"]}, {defaults["priceCeilingPermille"]})']
    sources = [relative, data['designSource'], 'scenario/world/world.json', 'scenario/economy/global-goods.json', 'scenario/economy/playable-trade.json', 'tooling/industry_catalog.py']
    sources += [str(p.relative_to(project)) for p in paths]
    return dict(catalog=dict(rules=data, effects=effects, sites=sites, markets=pairs), wurst='\n'.join(lines) + '\n', sources=sources)


if __name__ == '__main__':
    print(json.dumps(build()))
