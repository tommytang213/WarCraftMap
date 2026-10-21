"""Compile scenario-owned real grain deliveries and built canal freight links."""
from datetime import date
import json
import re
from pathlib import Path

METRICS = {'grain_supply_spoilage_reduction': 'supplied_land_armies_with_grain',
           'canal_freight_throughput': 'connected_operational_canal_routes'}


def configuration(project, world, settlements, authored, trade_records, finance):
    header = '\npublic function configureGeneratedLogistics(FinanceLedger ledger, FinanceResearchEffects effects)\n'
    path = project / 'scenario/progression/army-food-logistics.json'
    if not path.is_file():
        return header + '\tskip\n', {}, []
    data = json.loads(path.read_text())
    if data.get('schemaVersion') != 1:
        raise ValueError('logistics: invalid schema')
    design = project / data['designSource']
    if not design.resolve().is_relative_to(project.resolve()):
        raise ValueError('logistics: design source escapes scenario')
    effects = [e for e in json.loads(design.read_text())['effects'] if e['metric'] in METRICS]
    if len(effects) != 2 or {e['metric'] for e in effects} != set(METRICS):
        raise ValueError('logistics: missing exact contracts')
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    q = json.dumps
    lines = [header]
    for e in effects:
        n = nodes[e['nodeId']]
        if (e['unlock'] not in n['unlocks'] or e['unlock']['kind'] != 'modifier'
                or e['activation'] != 'passive_research' or e['recipient'] != METRICS[e['metric']]
                or type(e['bonusBasisPoints']) is not int or not 0 < e['bonusBasisPoints'] < 10000):
            raise ValueError('logistics: invalid typed effect or recipient')
        first = date(n['timeCost']['preferredYear'], 1, 1).toordinal()
        lines.append(f'\teffects.register(new FinanceEffect("modifier", {q(e["unlock"]["contentId"])}, {q(e["metric"])}, {e["bonusBasisPoints"]}, {first}))')
    def positive(value, label):
        if type(value) is not int or not 0 < value <= 1000000:
            raise ValueError('logistics: invalid ' + label)
    food = data['food']
    goods_path = project / data['goodsSource']
    if not goods_path.resolve().is_relative_to(project.resolve()):
        raise ValueError('logistics: goods source escapes scenario')
    goods = {g['id']: g for g in json.loads(goods_path.read_text())['goods']}
    good = goods.get(food['goodId'], {})
    if good.get('category') != 'food' or 'army' not in good.get('consumptionHooks', []):
        raise ValueError('logistics: actual army food commodity required')
    for key in ('shipmentUnits', 'wasteUnits', 'laborUnits', 'deliveryCost', 'radius', 'approachRadius'):
        positive(food[key], key)
    if food['wasteUnits'] >= food['shipmentUnits']:
        raise ValueError('logistics: waste must be less than real food')
    for key, field in {'goodId': 'foodGood', 'shipmentUnits': 'foodShipment', 'wasteUnits': 'foodWaste',
                       'laborUnits': 'foodLabor', 'deliveryCost': 'foodCost', 'radius': 'foodRadius'}.items():
        lines.append(f'\tledger.{field} = {q(food[key])}')
    positions = {s['id'] for s in settlements}
    def market(sid, good):
        return any(f'runtime.registerMarketProfile({q(sid)},{q(good)},' in x for x in trade_records)
    sites = sorted(sid for sid, (_, row) in authored.items() if sid in positions
                   and {'market', 'warehouse'} <= set(row['services']) and market(sid, food['goodId']))
    if not sites or len(sites) > 1024:
        raise ValueError('logistics: missing real food markets or site capacity exceeded')
    for sid in sites:
        lines += [f'\tledger.foodSites[ledger.foodSiteCount] = {q(sid)}', '\tledger.foodSiteCount++']
    projects = {p['id']: p for p in finance.get('canalWorks', [])}
    sources = [path, design, goods_path, Path(__file__)]
    seen = set()
    if not data['canalRoutes']:
        raise ValueError('logistics: missing real canal links')
    for i, route in enumerate(data['canalRoutes']):
        pid = route['projectId']
        if pid not in projects or pid in seen:
            raise ValueError('logistics: freight requires unique paid canal works')
        seen.add(pid)
        origin, destination = projects[pid]['settlementId'], route['destinationId']
        if origin == destination or any(sid not in positions or sid not in authored or
                not {'market', 'warehouse'} <= set(authored[sid][1]['services']) or
                'canal_node' not in authored[sid][1]['roles'] for sid in (origin, destination)):
            raise ValueError('logistics: canal endpoints require real canal geography and facilities')
        if authored[origin][1]['physicalMapId'] != authored[destination][1]['physicalMapId']:
            raise ValueError('logistics: canal connection cannot cross physical maps')
        source = project / route['routeSource']
        if not source.resolve().is_relative_to(project.resolve()):
            raise ValueError('logistics: route source escapes scenario')
        links = json.loads(source.read_text())['tradeRoutes']
        matches = [r for r in links if r['id'] == route['routeId']]
        if len(matches) != 1 or matches[0]['kind'] not in {'river', 'canal'} or {matches[0]['fromSettlementId'], matches[0]['toSettlementId']} != {origin, destination}:
            raise ValueError('logistics: actual waterway connection required')
        if not route['goodIds'] or len(set(route['goodIds'])) != len(route['goodIds']) or any(
                not market(sid, good) for good in route['goodIds'] for sid in (origin, destination)):
            raise ValueError('logistics: freight requires real endpoint commodity markets')
        for key in ('dailyCapacity', 'feeBasisPoints', 'laborUnits'):
            positive(route[key], key)
        if route['feeBasisPoints'] > 10000:
            raise ValueError('logistics: invalid freight fee')
        lines += [f'\tlet route{i} = ledger.projects[ledger.index({q(pid)})]',
                  f'\troute{i}.freightDestination = {q(destination)}',
                  f'\troute{i}.freightGoods = {q(",".join(route["goodIds"]))}',
                  f'\troute{i}.freightCapacity = {route["dailyCapacity"]}',
                  f'\troute{i}.freightFee = {route["feeBasisPoints"]}',
                  f'\troute{i}.freightLabor = {route["laborUnits"]}']
        sources.append(source)
    return '\n'.join(lines) + '\n', data | {'effects': effects, 'foodSiteIds': sites}, sources


REQUIRED_TESTS = {
    'registeredBakeriesDeliverRealGrainAndReduceOnlySpoilage',
    'registeredCanalLogisticsMoves110Versus100RealFreightAfterPaidConstruction',
    'logisticsRejectsMissingEraControllerGearResourcesInfrastructureAndDisconnectedRoutes',
    'logisticsNamedLayersRepairDeduplicateAndAddCompatibleRatesOnce',
    'logisticsCaptureTravelSaveMigrationAndRollbackKeepDailyCapacity',
    'failedCampaignLoadRollsBackFoodFreightTreasuryAndResearch',
    'logisticsLongCampaignConservesGrainAndCannotBankOrReplayCapacity',
}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        verify_execution_coverage(execution, execution_log, project, revision)
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError):
        return set()
    prefix = 'wurst/ArmyFoodLogisticsTests.wurst:'
    passed = {r['id'][len(prefix):] for r in execution['tests']
              if r['status'] == 'pass' and r['id'].startswith(prefix)}
    probes = execution.get('productionCoverage', {}).get('tests', {})
    if not REQUIRED_TESTS <= passed:
        return set()
    for name, required in {
        'registeredBakeriesDeliverRealGrainAndReduceOnlySpoilage': {'logistics_registration', 'logistics_food'},
        'registeredCanalLogisticsMoves110Versus100RealFreightAfterPaidConstruction': {'logistics_registration', 'logistics_freight', 'finance_canal', 'finance_advance'},
    }.items():
        if not required <= set(probes.get(prefix + name, [])):
            return set()
    design = json.loads((project / 'scenario/progression/gameplay-effect-design.json').read_text())
    return {(e['unlock']['kind'], e['unlock']['contentId']) for e in design['effects'] if e['metric'] in METRICS}


def supply_anchor(anchor, grid, radius):
    """Use a service's actual land cell or a bounded local road approach.

    Component rows are the same immutable terrain raster used by party travel.
    This does not move a settlement, make terrain passable or invent a route.
    """
    px, py = anchor['world']
    column = int((px - grid['minX']) // 128)
    row_index = int((py - grid['minY']) // 128)
    if 0 <= column < grid['width'] and 0 <= row_index < grid['height']:
        for end, label in re.findall(r'(\d+):(\d+),', grid['rows'][row_index]):
            if column < int(end):
                if int(label) > 0:
                    return px, py
                break
    candidates = []
    for y, row in enumerate(grid['rows']):
        cy = grid['minY'] + (y + .5) * 128
        if abs(cy - py) > radius:
            continue
        start = 0
        for end, label in re.findall(r'(\d+):(\d+),', row):
            end, label = int(end), int(label)
            if label > 0:
                x = min(end - 1, max(start, column))
                cx = grid['minX'] + (x + .5) * 128
                distance = (cx - px) ** 2 + (cy - py) ** 2
                if distance <= radius ** 2:
                    candidates.append((distance, cx, cy))
            start = end
    if not candidates:
        return None
    _, x, y = min(candidates)
    return x, y
