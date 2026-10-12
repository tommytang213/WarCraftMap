"""Verify mixed cargo execution/package evidence without closing broader gates."""
import gzip
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
SHARED = PROJECT.parent / '_shared'
sys.path[:0] = [str(SHARED / 'tooling'), str(PROJECT / 'tooling')]
from integration_evidence import source_identity
from requirement_traceability_audit import build_report
from validate_framework_fixture import source_hashes
from wurst_execution import verify_evidence

OUT = Path(__file__).parent

def read_gzip(name):
    return gzip.decompress((OUT / name).read_bytes())

execution = json.loads(read_gzip('wurst-results.json.gz'))
log = read_gzip('wurst-execution.log.gz')
verify_evidence(execution, log, execution['sourceRevision'])
identity = source_identity(PROJECT, execution['sourceRevision'])
assert execution['sourceIdentity'] == identity, 'stale execution sources'
package = json.loads((OUT / 'packaged-cargo.json').read_text())
assert package['sourceIdentity'] == identity, 'stale packaged sources'
assert package['catalogueDefinitionsMatch'] and package['compiledMixedCargoAndCommands']
framework = json.loads(read_gzip('framework-conformance.json.gz'))
assert framework['status'] == 'pass'
assert framework['frameworkSources'] == source_hashes(SHARED), 'stale shared framework'
for prefix in ('framework-original', 'framework-mutated'):
    verify_evidence(json.loads(read_gzip(prefix + '-results.json.gz')),
                    read_gzip(prefix + '-execution.log.gz'), execution['sourceRevision'])

cases = {
    'MixedCargoVectorsTests.wurst:registeredMixedCargoOracleOrder0': 'Registered buy/explicit transfer/sale journey compared at every step with headless balances, market stock, currency and FIFO cost.',
    'MixedCargoVectorsTests.wurst:registeredMixedCargoOracleOrder1': 'Reverse sale order preserves each quantity, all currency and the exact 94 total acquisition cost.',
    'MixedCargoTests.wurst:mixedCargoRejectsAmbiguityCapacityCompatibilityAndReplayAtomically': 'Mixed capacity, incompatible destinations, insufficient selected commodity, ambiguous shorthand and duplicate transactions reject atomically.',
    'MixedCargoTests.wurst:mixedCargoInspectionAndAccessRetainPhysicalStoreAuthority': 'Paged registered inspection; personal, warehouse and vessel checks retain physical presence, control and stale-selection rejection.',
    'MixedCargoTests.wurst:mixedCargoKeepsUncostedGoodsSeparateFromOtherCommodityLots': 'Uncosted mixed cargo cannot borrow another commodity cost basis or earn ordinary standing.',
    'MixedCargoTests.wurst:mixedCargoSnapshotRejectsMalformedBalancesAndCrossCommodityOverAttribution': 'Fresh v4 reconstruction, malformed/duplicate/overflowing balances, mismatched summaries and cross-commodity provenance rejection.',
    'MixedCargoTests.wurst:supportedSingleCommoditySavesMigrateThenAdmitMixedUncostedCargoExactly': 'Literal v2/v3 records preserve quantities, costs, uncosted portions, archival history and replay; unknown legacy identities stay separate.',
    'MixedCargoTests.wurst:mixedCargoSurvivesFailedStorageFreshServicesPhysicalTravelAndReturn': 'Failed transactional storage preserves the old slot and live cargo; fresh services and physical travel/return preserve complete trade authority.',
    'MixedCargoTests.wurst:mixedCargoLateExtensionAndPartyFailuresRestoreEveryBalanceAndLot': 'Late extension/party failures restore mixed balances, lots, other authority and projections together.',
    'PlayableTradeTests.wurst:mixedCommoditySplitsKeepDestinationFifoOriginsAndExactRemainders': 'Two mixed stores retain destination FIFO, original identities, integer remainders and legitimate zero-cost lots separately per commodity.',
    'PiracyCommandTests.wurst:prizeAdapterPreservesMixedDestinationAndRejectsAmbiguousSource': 'Single-commodity prizes preserve unrelated destination cargo/provenance; mixed-source claims reject without loss.',
}
tests = {row['id']: row for row in execution['tests']}
executed = []
for name, purpose in cases.items():
    row = tests['wurst/' + name]
    assert row['status'] == 'pass'
    executed.append(dict(**row, validates=purpose))
parents = {'REQ-0060', 'REQ-0066', 'ROAD-0046'}
trace = build_report()
requirements = [row for row in trace['requirements'] if row['parent'] in parents]
assert len(requirements) == 6
report = dict(
    format='warcraftmap_issue475_mixed_cargo_v1', sourceIdentity=identity,
    mixedCargoStatus='pass', tradeDomainVersion=4, campaignEnvelopeVersion=10,
    scope='Simultaneous commodity balances within existing live trade stores only.',
    entryPoints=['/trade select MARKET COMMODITY', '/trade store STORE', '/trade buy QUANTITY',
                 '/trade sell QUANTITY', '/trade move SOURCE DESTINATION COMMODITY QUANTITY',
                 '/trade inspect [PAGE]', '/trade stores [PAGE]'],
    authority='Shared CargoBalances keyed by stable commodity identity; FIFO CargoProvenance scoped to store and commodity; generated capacities/access remain unchanged.',
    migration='Supported unversioned 16/17/19/20-field records and v2/v3 singletons retain quantities, currency, exact costs, uncosted cargo and history; v4 uses sparse good=quantity entries.',
    referenceParity='test_mixed_cargo.py regenerates literal Wurst states from engine/economy.py and engine/trade.py; 22 registered transaction snapshots conserve each good, all currency and allocated cost in two sale orders.',
    executedTests=executed,
    executionSummary={key: execution[key] for key in ('discovered', 'succeeded', 'status')},
    packagedDefinitions=package, frameworkStatus=framework['status'],
    requirementScope=sorted(parents), broaderRequirements=requirements,
    closedPortions=[
        dict(id='REQ-0060.01', scope='Mixed buy/sell/transfer conserve quantities and currency with independent FIFO costs.'),
        dict(id='REQ-0060.02', scope='Existing personal, warehouse and vessel stores share their finite capacity across all compatible commodities.'),
        dict(id='REQ-0066.01', scope='Mixed balances, costs and history persist through fresh services, migration, travel and rollback.'),
        dict(id='ROAD-0046.01', scope='Single-commodity live cargo authority gap repaired.')],
    remainingBlockers=[
        'Broader economic simulation and other economic-integration obligations.',
        'Broader merchant reputation, route diversity and progression contributions.',
        'Mixed-source prize history remains outside the single-commodity prize contract and rejects atomically.',
        'Native Warcraft launch and real-client gameplay validation: blocked_pending_real_forsaken_kingdom_launch_smoke.',
        'Other repository publication blockers remain in the exhaustive traceability report.'],
    nativeClient='not_run', releaseReady=False)
(OUT / 'scoped-traceability.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(f'Mixed cargo: {len(executed)} focused production cases, {execution["succeeded"]} passing Wurst tests; same-source packaged/framework evidence; native blocker retained')
