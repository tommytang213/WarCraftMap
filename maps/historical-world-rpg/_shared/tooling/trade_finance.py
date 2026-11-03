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
    if data.get('schemaVersion') != 2:
        raise ValueError('finance: invalid schema')
    design = project / data['designSource']
    if not design.resolve().is_relative_to(project.resolve()):
        raise ValueError('finance: design source escapes scenario')
    effects = [e for e in json.loads(design.read_text())['effects'] if e['metric'] in METRICS]
    if len(effects) != 5 or {e['metric'] for e in effects} != METRICS:
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
    customs = data['customsHouse']
    node = nodes.get(customs['nodeId'])
    if (not node or customs['nodeId'] != 'commodity_exchanges'
            or {'kind': 'building', 'contentId': customs['building']} not in node['unlocks']
            or {'kind': 'modifier', 'contentId': customs['modifier']} not in node['unlocks']):
        raise ValueError('finance: missing exact Customs House typed unlocks')
    fields = {'constructionTaxBasisPoints': ('customsBuildRate', 1000),
              'upkeepTaxBasisPoints': ('customsUpkeepRate', 50),
              'workers': ('customsWorkers', 10), 'constructionDays': ('customsDays', 90),
              'administration': ('customsAdministration', 30),
              'commissionReductionBasisPoints': ('customsCommission', 600),
              'slippageReductionBasisPoints': ('customsSlippage', 500)}
    for key, (field, expected) in fields.items():
        if type(customs[key]) is not int or customs[key] != expected:
            raise ValueError('finance: invalid Customs House ' + key)
        lines.append(f'\tledger.{field} = {customs[key]}')
    materials = customs['materials']
    if (len(materials) != 2 or materials[0]['good'] == materials[1]['good']
            or any(type(row['units']) is not int or row['units'] != units
                   or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', row['good'])
                   or not any(f',{q(row["good"])},' in record for record in trade_records)
                   for row, units in zip(materials, (20, 10)))):
        raise ValueError('finance: invalid existing Customs House materials/equipment')
    for row, field in zip(materials, ('Material', 'Equipment')):
        lines += [f'\tledger.customs{field}Good = {q(row["good"])}',
                  f'\tledger.customs{field}Units = {row["units"]}']
    first = date(node['timeCost']['preferredYear'], 1, 1).toordinal()
    lines += [f'\tledger.customsBuilding = {q(customs["building"])}',
              f'\tledger.customsModifier = {q(customs["modifier"])}',
              f'\teffects.register(new FinanceEffect("building", {q(customs["building"])}, "customs_commission_reduction", {customs["commissionReductionBasisPoints"]}, {first}))',
              f'\teffects.register(new FinanceEffect("modifier", {q(customs["modifier"])}, "customs_slippage_reduction", {customs["slippageReductionBasisPoints"]}, {first}))']
    lines += [f'\tledger.customsNode = {q(node["id"])}',
              f'\tledger.customsFirstDay = {first}']
    if (not customs['eligibility'] or not customs['roles'] or len(set(customs['roles'])) != len(customs['roles'])
            or not set(customs['roles']) <= {'major_port', 'port', 'trade_center', 'market_center', 'trade_hub', 'caravan_center'}):
        raise ValueError('finance: invalid historical Customs House geography/commerce')
    positions = {s['id']: s for s in settlements}
    sites = {sid: row for sid, (_, row) in authored.items() if sid in positions
             and {'market', 'warehouse'} <= set(row['services'])
             and {'major_port', 'port', 'trade_center', 'market_center', 'capital', 'trade_hub', 'caravan_center'} & set(row['roles'])
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
        lines.append(f'\tledger.registerSite({q(sid)}, {q(row["provinceId"])}, {q(banks.get(sid, ""))}, {str(bool(set(row["roles"]) & set(customs["roles"]))).lower()})')
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
    consumers = [dict(nodeId=node['id'], kind=kind, contentId=content,
                      metric=metric, bonusBasisPoints=rate,
                      runtimeConsumer=consumer,
                      construction=dict(taxBasisPoints=customs['constructionTaxBasisPoints'],
                                        materials=materials, workers=customs['workers'], days=customs['constructionDays']),
                      operation=dict(taxBasisPoints=customs['upkeepTaxBasisPoints'], prepaidDays=365,
                                     administration=customs['administration']),
                      costBucket=metric, requiresCounterpartyLiquidity=(kind == 'modifier'),
                      qualification='paid_completed_lawful_administered_market_warehouse_current_controller_earned_prepaid_operation',
                      siteIds=[sid for sid, row in sites.items() if set(row['roles']) & set(customs['roles'])])
                 for kind, content, metric, rate, consumer in (
                     ('building', customs['building'], 'market_transaction_fee_reduction', customs['commissionReductionBasisPoints'],
                      'FinanceCampaignRuntime.customsAction/advanceCustoms/amount'),
                     ('modifier', customs['modifier'], 'market_slippage_reduction', customs['slippageReductionBasisPoints'],
                      'FinanceCampaignRuntime.operatingCustoms/amount'))]
    return '\n'.join(lines) + '\n', data | {'effects': effects, 'consumers': consumers, 'exchangeIds': list(sites)}, [path, design, Path(__file__)]


def verify_generated(project, world, settlements, authored, source, catalogue):
    """Reject disconnected recipes and per-identity metadata, even if rehashed."""
    records = [line for line in source.splitlines() if 'runtime.registerMarketProfile(' in line]
    expected, expected_catalogue, _inputs = configuration(project, world, settlements, authored, records)
    if catalogue != expected_catalogue or source.count(expected) != 1:
        raise ValueError('finance: executable catalogue or exact consumer metadata differs from scenario')

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


CUSTOMS_COMPARISONS = {
    ('building', 'customs_house'): 'registeredPaidCustomsCompletionConsumesInputsTimeAndOperationBeforeSettledCommissionBenefit',
    ('modifier', 'credit_liquidity'): 'registeredCreditLiquidityIncrementalSettledCostUsesExistingFundsAndActualCargo',
}
CUSTOMS_TESTS = {
    'customsRejectsMissingMaterialsWorkersTreasuryAccessResearchAndUnsupportedSites',
    'customsStackingLiquidityStaleQuotesSplitsAndExpirationConserveCosts',
    'customsCaptureDestructionReconstructionSaveResumeAndLegacyMigrationRetainOnlyPaidAuthority',
    'customsPlayerAiActiveInactiveAndLateLoadRollbackUseSameAuthority',
    'customsSettlementsRecheckEntitlementsCounterpartyFundsAccessAndSavedDeadlines',
}
CUSTOMS_PROBES = AUCTION_PROBES | {'customs_action', 'customs_advance', 'customs_operation'}

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
    customs_passed = {row['id'].rsplit(':', 1)[-1] for row in execution['tests']
                     if row['status'] == 'pass' and row['id'].startswith('wurst/CustomsHouseTests.wurst:')}
    if CUSTOMS_TESTS <= customs_passed:
        for identity, name in CUSTOMS_COMPARISONS.items():
            if name in customs_passed and CUSTOMS_PROBES <= set(probes.get('wurst/CustomsHouseTests.wurst:' + name, [])):
                bindings.add(identity)
    bindings.discard(("modifier", "progression_commercial_statistics"))
    return bindings
