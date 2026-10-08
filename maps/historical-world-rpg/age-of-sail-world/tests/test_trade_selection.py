"""Generated store bindings must resolve to existing campaign authorities."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from package_wurst_map import generate, load_config, verify_generated
from wurst_execution import discover


class TradeSelectionGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.config = load_config(PROJECT / 'package.json')
        cls.generated = Path(cls.temp.name) / 'generated'
        generate(cls.config, cls.generated)
        cls.data = json.loads((cls.generated / 'scenario-runtime.json').read_text())
        cls.world = json.loads(cls.config.scenario_file.read_text())
        cls.wurst = (cls.generated / 'ScenarioData.wurst').read_text()

    def test_store_definitions_bind_all_generated_stores_without_origin_grants(self):
        definitions = self.data['tradeStoreDefinitions']
        stores = {row['id']: row for row in definitions}
        self.assertEqual(len(stores), len(definitions))
        settlements = {row['id'] for row in self.data['settlementRuntimeStates']}
        vessels = {row['id'] for row in self.world['strategicUnits'] if row['kind'] == 'ship'}
        self.assertEqual({'player_ship_hold'} | {f'warehouse:{x}' for x in settlements}
                         | {f'cargo:{x}' for x in vessels}, set(stores))
        authored = {row['id']: row for path in (PROJECT / 'scenario/settlements').glob('*-1450.json')
                    for row in json.loads(path.read_text()).get('settlements', [])}
        profiles = {row['settlementId']: row for row in json.loads((PROJECT / 'scenario/integration/release-scale-settlements.json').read_text())['settlements']}
        locations = {row['id']: row for row in self.data['interactionLocations']
                     if row['kind'] == 'settlement'}
        self.assertTrue(settlements <= set(locations))
        for row in definitions:
            with self.subTest(store=row['id']):
                self.assertNotIn('originId', row)
                if row['kind'] == 'personal':
                    self.assertEqual('player', row['authorityId'])
                    self.assertIn('runtime.registerPersonalStore()', self.wurst)
                elif row['kind'] == 'warehouse':
                    self.assertIn(row['authorityId'], locations)
                    self.assertEqual('warehouse' in authored.get(row['authorityId'], {}).get('services', profiles[row['authorityId']]['economy']['serviceHookIds']),
                                     row['warehouseService'])
                else:
                    self.assertEqual('ship', row['kind'])
                    self.assertIn(row['authorityId'], vessels)
                if row['kind'] != 'personal':
                    self.assertIn('.withAccess("{}","{}",{})'.format(
                        row['kind'], row['authorityId'], str(row['warehouseService']).lower()), self.wurst)
        verify_generated(self.config, self.generated)

    def test_production_dispatch_journey_is_in_pinned_execution_discovery(self):
        tests = {row['id'].split(':')[1] for row in discover(PROJECT)}
        self.assertTrue({
            'registeredTradeCommandsCompleteTwoCommodityTwoSettlementCargoJourney',
            'tradeCommandsRejectUnknownHiddenRemoteAndUnauthorizedTargets',
            'tradeCommandsRecheckMovementOwnershipAndCampaignAvailabilityAtCommit',
            'tradeCommitRejectsControlChangesBetweenResolutionAndMutation',
            'tradeSelectionLoadRollbackAndLegacyPersonalStoreMigrationPreserveAuthority',
            'legacySummaryTradeKeepsHistoricalStoreAndCapacityDespiteCurrentSelection',
            'tradeListsAreBoundedAndShareOnlyTheExistingMarketPauseOwner',
        } <= tests)


if __name__ == '__main__':
    unittest.main()
