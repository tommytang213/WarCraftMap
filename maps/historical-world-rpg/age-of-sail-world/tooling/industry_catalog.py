"""Compile paid workshops and evidenced mineral deposits from scenario authority.

Definitions create neither commodity stock nor market liquidity. Coal extraction
is restricted to validated authored geography; coke always consumes real coal.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = {'iron_refining_yield', 'gun_barrel_production_throughput'}
COKE_IDENTITY = ('modifier', 'progression_coke_smelted_iron')


def build(project=ROOT):
    project = Path(project)
    relative = 'scenario/progression/industry.json'
    data = json.loads((project / relative).read_text())
    if set(data['setup']) != {'days', 'money', 'equipment', 'fuel', 'workers'} or set(data['daily']) != {'money', 'supply'}:
        raise ValueError('industry: invalid setup/daily fields')
    recipes = data['recipes']
    expected = {'iron_refining', 'gun_barrels', 'mineral_iron_refining', 'coal_extraction', 'coke_preparation'}
    if data.get('schemaVersion') != 2 or {r['id'] for r in recipes} != expected or len(recipes) != len(expected):
        raise ValueError('industry: invalid schema/recipes')
    for group in ('setup', 'daily'):
        for value in data[group].values():
            if type(value) is not int or not 0 < value <= 10000:
                raise ValueError('industry: invalid cost or duration')
    world = json.loads((project / 'scenario/world/world.json').read_text())
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    goods = {g['id']: g for g in json.loads((project / 'scenario/economy/global-goods.json').read_text())['goods']}
    paid_goods = {good for good, definition in goods.items() if definition.get('paidProductionRecipe')}
    if paid_goods != {'coal', 'coke'} or any(goods[g]['ordinaryAvailability'] != 0 for g in paid_goods):
        raise ValueError('industry: mineral fuel must originate in paid production')
    goods_data = json.loads((project / 'scenario/economy/global-goods.json').read_text())
    if any(paid_goods & set(defaults['stapleGoodIds'] + defaults['tradeGoodIds']) for defaults in goods_data['regionalDefaults'].values()):
        raise ValueError('industry: opening baskets cannot grant mineral fuel or liquidity')
    design = json.loads((project / data['designSource']).read_text())
    effects = [e.copy() for e in design['effects'] if e['family'] == 'industry' and e['metric'] in METRICS]
    identities = {(e['unlock']['kind'], e['unlock']['contentId']) for e in effects}
    if len(effects) != 3 or len(identities) != 3 or {e['metric'] for e in effects} != METRICS or COKE_IDENTITY not in identities:
        raise ValueError('industry: missing or duplicate approved effect')
    for e in effects:
        n = nodes[e['nodeId']]
        if e['unlock']['kind'] != 'modifier' or e['unlock'] not in n['unlocks'] or type(e['bonusBasisPoints']) is not int or not 0 < e['bonusBasisPoints'] <= 10000:
            raise ValueError('industry: invalid typed effect')
        e['firstYear'] = n['timeCost']['preferredYear']
        if e.get('requiredFuel', '') not in ('', 'coke') or (e['nodeId'] == 'coke_smelted_iron') != (e.get('requiredFuel') == 'coke'):
            raise ValueError('industry: invalid fuel qualification')
    if data['fuelGood'] == data['equipmentGood'] or not {data['fuelGood'], data['equipmentGood']} <= goods.keys():
        raise ValueError('industry: invalid fuel/equipment')
    evidence = {e['id']: e for e in data['evidence']}
    if len(evidence) != len(data['evidence']):
        raise ValueError('industry: duplicate geographic evidence')
    for r in recipes:
        for key in ('firstYear', 'inputUnits', 'fuelUnits', 'wearUnits', 'money', 'outputUnits', 'workRequired', 'dailyWork', 'depositUnits'):
            minimum = 0 if key in ('inputUnits', 'fuelUnits', 'depositUnits') else 1
            maximum = 1000000 if key == 'depositUnits' else 10000
            if type(r[key]) is not int or not minimum <= r[key] <= maximum:
                raise ValueError('industry: invalid recipe quantity')
        if (r.get('mode') not in {'yield', 'throughput', 'batch'} or r['dailyWork'] > r['workRequired']
                or r['prerequisite'] not in nodes or r['supportingTechnology'] and r['supportingTechnology'] not in nodes):
            raise ValueError('industry: invalid work/prerequisite')
        materials = [r['inputGood'], r['outputGood'], r['fuelGood'], data['equipmentGood']]
        nonempty = [g for g in materials if g]
        if len(set(nonempty)) != len(nonempty) or not set(nonempty) <= goods.keys() or bool(r['inputGood']) != bool(r['inputUnits']) or bool(r['fuelGood']) != bool(r['fuelUnits']):
            raise ValueError('industry: invalid material/output identities')
        if r['productionRef'] and r['productionRef'] not in goods:
            raise ValueError('industry: unknown industrial production')
        expected_metric = 'iron_refining_yield' if r['mode'] == 'yield' else 'gun_barrel_production_throughput' if r['mode'] == 'throughput' else ''
        if r['metric'] != expected_metric or r['recordVersion'] != (1 if r['id'] in ('iron_refining', 'gun_barrels') else 2):
            raise ValueError('industry: invalid metric/record version')
        if r['mode'] == 'yield' and r['outputUnits'] * 2 > r['inputUnits']:
            raise ValueError('industry: refining must consume real feedstock with bounded recovery')
        if r['id'] == 'mineral_iron_refining' and (r['fuelGood'] != 'coke' or r['firstYear'] < 1710 or not r['supportingTechnology'] or r['productionRef'] != 'iron'):
            raise ValueError('industry: mineral refining requires compatible machinery, era and coke')
        if r['id'] == 'coal_extraction' and (r['inputGood'] or r['outputGood'] != 'coal' or r['depositUnits'] < r['outputUnits']):
            raise ValueError('industry: invalid coal deposit')
        if r['id'] == 'coke_preparation' and (r['inputGood'] != 'coal' or r['outputGood'] != 'coke' or r['outputUnits'] > r['inputUnits']):
            raise ValueError('industry: coke must consume coal')
        if r['id'] in ('coal_extraction', 'coke_preparation'):
            if r['productionRef'] or not r.get('evidenceIds') or not r.get('settlementIds') or goods[r['outputGood']].get('paidProductionRecipe') != r['id']:
                raise ValueError('industry: missing paid geographic production')
    sites = []
    paths = sorted((project / 'scenario/settlements').glob('*-1450.json'))
    settlement_ids = {s['id'] for s in world['settlements']}
    seen = set()
    for path in paths:
        for s in json.loads(path.read_text())['settlements']:
            production = s.get('economy', {}).get('production', s.get('productionRefs', []))
            identity = s.get('economy', {})
            ordinary = set(production + identity.get('imports', s.get('importRefs', [])) + identity.get('shortages', s.get('shortageRefs', [])))
            if ordinary & paid_goods:
                raise ValueError('industry: opening settlement markets cannot grant mineral fuel')
            for r in recipes:
                compatible = r['productionRef'] in production if r['productionRef'] else s['id'] in r['settlementIds']
                if not compatible or not set(data['requiredServices']) <= set(s.get('services', [])):
                    continue
                if not r['productionRef']:
                    for eid in r['evidenceIds']:
                        e = evidence.get(eid, {})
                        bounds, position = e.get('bounds', []), s.get('sourcePosition', [])
                        if (e.get('settlementId') != s['id'] or not e.get('url', '').startswith('https://')
                                or not e.get('note') or len(bounds) != 4 or len(position) != 2
                                or not bounds[0] <= position[0] <= bounds[2] or not bounds[1] <= position[1] <= bounds[3]
                                or r['firstYear'] < e.get('firstYear', 10000)):
                            raise ValueError('industry: invalid geographic/historical evidence')
                ident = r['id'] + ':' + s['id']
                if s['id'] not in settlement_ids or ident in seen:
                    raise ValueError('industry: unknown/duplicate facility')
                seen.add(ident)
                sites.append(dict(r, id=ident, settlementId=s['id']))
    for r in recipes:
        if not any(s['id'].startswith(r['id'] + ':') for s in sites):
            raise ValueError('industry: unreachable recipe/fuel path')
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
        lines.append(f'\teffects.registerIndustrialFuel(new CivicEffect({q(u["kind"])}, {q(u["contentId"])}, {q(e["metric"])}, {e["bonusBasisPoints"]}), {e["firstYear"]}, {q(e.get("requiredFuel", ""))})')
    # Inspection text is generated from the same paid recipe authority as work.
    for index, e in enumerate(effects):
        matching = [r for r in recipes if r['metric'] == e['metric'] and (not e.get('requiredFuel') or r['fuelGood'] == e['requiredFuel'])]
        if e.get('requiredFuel') == 'coke':
            matching += [r for r in recipes if r['id'] in ('coal_extraction', 'coke_preparation')]
        rows = []
        setup, daily = data['setup'], data['daily']
        for r in matching:
            base_days = (r['workRequired'] + r['dailyWork'] - 1) // r['dailyWork']
            if r['mode'] == 'yield':
                isolated = min(r['inputUnits'], r['outputUnits'] + r['outputUnits'] * e['bonusBasisPoints'] // 10000)
                combined_rate = sum(effect['bonusBasisPoints'] for effect in effects if effect['metric'] == r['metric'] and (not effect.get('requiredFuel') or effect['requiredFuel'] == r['fuelGood']))
                combined = min(r['inputUnits'], r['outputUnits'] + r['outputUnits'] * combined_rate // 10000)
                result = f"isolated qualifying output {isolated}; combined qualifying output {combined}, each in {base_days} funded workdays, bounded by consumed feedstock"
            elif r['mode'] == 'throughput':
                daily_work = r['dailyWork'] * (10000 + e['bonusBasisPoints'])
                days = (r['workRequired'] * 10000 + daily_work - 1) // daily_work
                result = f"qualifying output {r['outputUnits']} in {days} versus {base_days} funded workdays"
            else:
                result = f"output {r['outputUnits']} in {base_days} funded workdays; geological deposit {r['depositUnits']} units" if r['depositUnits'] else f"output {r['outputUnits']} in {base_days} funded workdays"
            rows.append(f"{r['id']}: year {r['firstYear']}, lawful administration, accessible market/warehouse, {r['prerequisite']} {r['supportingTechnology']}; commission {setup['money']} currency, {setup['equipment']} {data['equipmentGood']}, {setup['fuel']} {data['fuelGood']}, {setup['workers']} assigned workers, {setup['days']} days; batch {r['inputUnits']} {r['inputGood']}, {r['fuelUnits']} {r['fuelGood']}, {r['wearUnits']} tools, {r['money']} currency; {daily['money']} currency and {daily['supply']} supply each funded day; base {r['outputUnits']} {r['outputGood']}; {result}. Each source requires its own current-controller research and historical availability. Use /industry inspect SITE for current combined yield/workdays.")
        lines.append(f'\teffects.inspections[{index}] = {q(" ".join(rows))}')
    for i, s in enumerate(sites):
        args = [q(s[k]) for k in ('id', 'settlementId', 'metric', 'prerequisite', 'inputGood', 'outputGood')]
        args += [str(s[k]) for k in ('firstYear', 'inputUnits', 'fuelUnits', 'wearUnits', 'money', 'outputUnits', 'workRequired', 'dailyWork')]
        args.append(str(s['mode'] == 'yield').lower())
        lines.append(f'\tlet site{i} = new IndustrySite(' + ', '.join(args) + ')')
        for key in ('fuelGood', 'supportingTechnology', 'recordVersion', 'depositUnits'):
            lines.append(f'\tsite{i}.{key} = {q(s[key])}')
        lines.append(f'\tledger.register(site{i})')
    lines += ['\npublic function configureGeneratedIndustryMarkets(PlayableTradeRuntime runtime)']
    defaults = json.loads((project / 'scenario/economy/playable-trade.json').read_text())['marketDefaults']
    pairs = sorted({(s['settlementId'], g) for s in sites for g in (s['inputGood'], s['outputGood'], s['fuelGood'], data['fuelGood'], data['equipmentGood']) if g})
    for ident, good in pairs:
        g = goods[good]
        lines += [f'\tif runtime.findMarket({q(ident)}, {q(good)}) == null',
                  f'\t\truntime.registerMarketProfile({q(ident)}, {q(good)}, 0, 0, {g["basePriceMinor"]}, 1000, 1000, 0, {g["quantityUnitsPerDisplayUnit"]}, {g["priceElasticityPermille"]}, {defaults["spreadPermille"]}, {defaults["priceFloorPermille"]}, {defaults["priceCeilingPermille"]})']
    sources = [relative, data['designSource'], 'scenario/world/world.json', 'scenario/economy/global-goods.json', 'scenario/economy/playable-trade.json', 'tooling/industry_catalog.py']
    sources += [str(p.relative_to(project)) for p in paths]
    return dict(catalog=dict(rules=data, effects=effects, sites=sites, markets=pairs, consumers=[dict(nodeId=e['nodeId'], kind=e['unlock']['kind'], contentId=e['unlock']['contentId'], metric=e['metric'], bonusBasisPoints=e['bonusBasisPoints'], requiredFuel=e.get('requiredFuel', ''), recipeIds=[r['id'] for r in recipes if r['metric'] == e['metric'] and (not e.get('requiredFuel') or r['fuelGood'] == e['requiredFuel'])], runtimeConsumer='IndustryLedger.advance/IndustryResearchEffects.rateFor', qualification='commissioned_compatible_lawful_administered_paid_materials_workers_supporting_technology') for e in effects]), wurst='\n'.join(lines) + '\n', sources=sources)


COKE_COMPARISON = 'cokeOnlyRegisteredResearchConsumesPaidMineralFuelAndProduces106Against100And113Combined'
COKE_TESTS = {
    COKE_COMPARISON,
    'cokeUpstreamPaidExtractionPreparationAndTransportConserveResourcesWithoutLiquidityGrants',
    'cokeMissingBillsCompatibilityEraAuthorityStorageAndCancellationFailClosed',
    'cokeFractionsDuplicateSourcesPlayerAiInactiveCaptureAndReconstructionRetainPaidState',
    'cokeCurrentAndLegacyStableRecordsRejectPartialForgedAndMalformedRetrofitsAtomically',
    'cokeLateCampaignFailureRollsBackRetrofitFuelReservationsAndFractionalAccounts',
}
COKE_PROBES = {'research', 'dispatch', 'industry_registration', 'industry_action',
               'industry_advance', 'industry_pay', 'industry_labor', 'industry_output',
               'industry_material', 'industry_yield'}


def verified_coke_bindings(project, execution=None, execution_log=None, revision=None):
    """Only this identity's isolated production comparison can close its finding."""
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
        prefix = 'wurst/IndustryTests.wurst:'
        passed = {r['id'] for r in execution['tests'] if r['status'] == 'pass'}
        comparison = prefix + COKE_COMPARISON
        upstream = prefix + 'cokeUpstreamPaidExtractionPreparationAndTransportConserveResourcesWithoutLiquidityGrants'
        if (not {prefix + name for name in COKE_TESTS} <= passed
                or comparison not in coverage.get('mineral_fuel_industry', [])
                or not COKE_PROBES <= set(execution['productionCoverage']['tests'].get(comparison, []))
                or not {'industry_material', 'industry_pay', 'industry_labor', 'industry_output'} <= set(execution['productionCoverage']['tests'].get(upstream, []))):
            return set()
        catalog = build(project)['catalog']
        effects = [e for e in catalog['effects'] if e['nodeId'] == 'coke_smelted_iron']
        if (len(effects) != 1 or effects[0]['unlock'] != dict(zip(('kind', 'contentId'), COKE_IDENTITY))
                or type(effects[0]['bonusBasisPoints']) is not int or effects[0]['bonusBasisPoints'] != 600
                or effects[0].get('requiredFuel') != 'coke' or effects[0]['firstYear'] != 1710):
            return set()
        recipe = next(r for r in catalog['rules']['recipes'] if r['id'] == 'mineral_iron_refining')
        required = dict(inputGood='iron', inputUnits=200, fuelGood='coke', fuelUnits=50,
                        wearUnits=2, money=20, outputGood='iron_goods', outputUnits=100,
                        workRequired=1000, dailyWork=100, prerequisite='water_powered_machinery',
                        supportingTechnology='experimental_method', recordVersion=2)
        if any(type(recipe[k]) is not type(v) or recipe[k] != v for k, v in required.items()):
            return set()
        if catalog['rules']['setup'] != dict(days=90, money=120, workers=10, equipment=10, fuel=20):
            return set()
        return {COKE_IDENTITY}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError, StopIteration):
        return set()


if __name__ == '__main__':
    print(json.dumps(build()))
