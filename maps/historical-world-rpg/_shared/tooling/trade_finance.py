"""Compile explicit exchange, correspondent-bank and canal-work capabilities."""
from datetime import date
import json
import re
from pathlib import Path

METRICS = {'market_transaction_fee_reduction', 'secure_remittance_fee_reduction',
           'market_slippage_reduction', 'canal_infrastructure_financing_cost_reduction'}


def configuration(project, world, settlements, authored, trade_records):
    header = '\npublic function configureGeneratedFinance(FinanceLedger ledger, FinanceResearchEffects effects)\n'
    path = project / 'scenario/progression/trade-finance.json'
    if not path.is_file():
        return header + '\tskip\n', {}, []
    data = json.loads(path.read_text())
    if data.get('schemaVersion') != 1:
        raise ValueError('finance: invalid schema')
    design = project / data['designSource']
    if not design.resolve().is_relative_to(project.resolve()):
        raise ValueError('finance: design source escapes scenario')
    effects = [e for e in json.loads(design.read_text())['effects'] if e['metric'] in METRICS]
    if len(effects) != 4 or {e['metric'] for e in effects} != METRICS:
        raise ValueError('finance: missing exact contracts')
    nodes = {n['id']: n for n in world['technologies'] + world['institutions']}
    q = json.dumps
    lines = [header]
    for e in effects:
        n = nodes[e['nodeId']]
        if (e['unlock'] not in n['unlocks'] or e['unlock']['kind'] != 'modifier'
                or type(e['bonusBasisPoints']) is not int or not 0 < e['bonusBasisPoints'] < 10000):
            raise ValueError('finance: invalid typed effect')
        first = date(n['timeCost']['preferredYear'], 1, 1).toordinal()
        lines.append(f'\teffects.register(new FinanceEffect("modifier", {q(e["unlock"]["contentId"])}, {q(e["metric"])}, {e["bonusBasisPoints"]}, {first}))')
    for key in ('commissionShareBasisPoints', 'remittanceFeeBasisPoints'):
        if type(data[key]) is not int or not 0 < data[key] < 10000:
            raise ValueError('finance: invalid fee allocation')
    if data['bankPrerequisite'] not in nodes:
        raise ValueError('finance: missing banking prerequisite')
    lines += [f'\tledger.commissionShare = {data["commissionShareBasisPoints"]}',
              f'\tledger.remittanceFee = {data["remittanceFeeBasisPoints"]}',
              f'\tledger.bankPrerequisite = {q(data["bankPrerequisite"])}']
    positions = {s['id']: s for s in settlements}
    sites = {sid: row for sid, (_, row) in authored.items() if sid in positions
             and {'market', 'warehouse'} <= set(row['services'])
             and {'trade_center', 'market_center', 'capital', 'trade_hub', 'caravan_center'} & set(row['roles'])
             and any(f'runtime.registerMarketProfile({q(sid)},' in x for x in trade_records)}
    if len(sites) > 1024:
        raise ValueError('finance: exchange capacity exceeded')
    banks = {}
    for network in data['bankNetworks']:
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', network['id']) or len(network['settlementIds']) < 2:
            raise ValueError('finance: invalid banking network')
        for sid in network['settlementIds']:
            if sid not in sites or 'banking' not in sites[sid]['services'] or sid in banks:
                raise ValueError('finance: bank lacks real service or is duplicated')
            banks[sid] = network['id']
    for sid, row in sites.items():
        lines += [f'\tledger.sites[ledger.siteCount] = new ExchangeSite({q(sid)}, {q(row["provinceId"])}, {q(banks.get(sid, ""))})',
                  '\tledger.siteCount++']
    ids, locations = set(), set()
    if not 0 < len(data['canalWorks']) <= 32:
        raise ValueError('finance: invalid project count')
    fields = ('materialUnits', 'principalCost', 'financingCost', 'laborCostPerDay', 'constructionDays', 'capacityUnits', 'laborUnits')
    for d in data['canalWorks']:
        sid = d['settlementId']
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', d['id']) or d['id'] in ids or sid in locations:
            raise ValueError('finance: invalid or duplicate project')
        ids.add(d['id']); locations.add(sid)
        if sid not in sites or 'canal_node' not in sites[sid]['roles']:
            raise ValueError('finance: actual canal geography and facilities required')
        if d['prerequisite'] not in nodes or not any(f'runtime.registerMarketProfile({q(sid)},{q(d["good"])},' in x for x in trade_records):
            raise ValueError('finance: missing technology or real materials')
        for key in fields:
            if type(d[key]) is not int or not 0 < d[key] <= 1000000:
                raise ValueError('finance: invalid project ' + key)
        first = date.fromisoformat(d['firstDate']).toordinal()
        if first < date(nodes[d['prerequisite']]['timeCost']['preferredYear'], 1, 1).toordinal():
            raise ValueError('finance: canal project precedes supporting technology')
        args = [q(d[k]) for k in ('id', 'settlementId', 'prerequisite', 'good')] + [str(first)] + [str(d[k]) for k in fields]
        lines.append('\tledger.register(new CanalWork(' + ', '.join(args) + '))')
    return '\n'.join(lines) + '\n', data | {'effects': effects, 'exchangeIds': list(sites)}, [path, design, Path(__file__)]

# These are production tests, not a design approval or source-name heuristic.
# Release consumes only a verified full current-source interpreter transcript.
REQUIRED_TESTS = {
    'financeLongCampaignConservesWealthAndMissedLaborNeverReplaysFreeWork',
    'registeredAuctionAndBrokerageResearchReduceExistingSettlementCostsPrecisely',
    'registeredBillsResearchReducesOnlyPaidBankFeesAndConservesPrincipal',
    'registeredCanalFinancePaysMaterialsPrincipalReducedFeeAndDailyLaborBeforeDurableOutput',
    'financeMissingTechEraControlRecipientAccessFundsStockAndGearNeverBypassAuthority',
    'financeResearchNamedLayersDeduplicateRepairAndStackDistinctSourcesOnce',
    'canalActiveInactiveTravelCaptureSaveMigrationAndFailedLoadRemainDeterministic',
    'failedCampaignLoadRollsBackPaidCanalWorkWithOtherAuthority',
    'registeredTradeCommandUsesFinanceAndStillRequiresPhysicalPresence',
}

# Auction closure additionally proves the isolated approved effect through real
# command settlement. Keep every original finance-suite and sibling gate.
AUCTION_TESTS = {
    'auctionOnlyRegisteredPurchaseAndSaleMatchControlsAndConserveAuthority',
    'auctionCommitRechecksResearchFacilitiesControlAccessAndStaleStock',
    'auctionTinyOrdersReplayReconstructionAndFailedLoadKeepAuthority',
}
AUCTION_PROBES = {'finance_registration', 'research', 'trade_command',
                  'finance_quote', 'finance_buy_settle', 'finance_sell_settle'}
AUCTION_BINDING = ('modifier', 'progression_auction_markets')


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    """Fail closed until same-revision execution verifies every finance consumer."""
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        verify_execution_coverage(execution, execution_log, project, revision)
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError):
        return set()
    passed = {row['id'].rsplit(':', 1)[-1] for row in execution['tests']
              if row['status'] == 'pass' and row['id'].startswith('wurst/TradeFinanceTests.wurst:')}
    if not REQUIRED_TESTS <= passed:
        return set()
    probes = execution.get('productionCoverage', {}).get('tests', {})
    required_probes = {
        'registeredAuctionAndBrokerageResearchReduceExistingSettlementCostsPrecisely': {'finance_registration', 'finance_quote'},
        'registeredBillsResearchReducesOnlyPaidBankFeesAndConservesPrincipal': {'finance_registration', 'finance_remit'},
        'registeredCanalFinancePaysMaterialsPrincipalReducedFeeAndDailyLaborBeforeDurableOutput': {'finance_registration', 'finance_canal', 'finance_advance'},
    }
    if any(not required <= set(probes.get('wurst/TradeFinanceTests.wurst:' + name, []))
           for name, required in required_probes.items()):
        return set()
    design = json.loads((project / 'scenario/progression/gameplay-effect-design.json').read_text())
    bindings = {(e['unlock']['kind'], e['unlock']['contentId'])
                for e in design['effects'] if e['metric'] in METRICS}
    if (not AUCTION_TESTS <= passed or not AUCTION_PROBES <= set(probes.get(
            'wurst/TradeFinanceTests.wurst:auctionOnlyRegisteredPurchaseAndSaleMatchControlsAndConserveAuthority', []))):
        bindings.discard(AUCTION_BINDING)
    return bindings
