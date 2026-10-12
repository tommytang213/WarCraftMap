"""Differential discovery contract and complete scenario catalogue checks."""
import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
SHARED = PROJECT.parent / '_shared'
sys.path[:0] = [str(SHARED / 'engine'), str(SHARED / 'tooling')]
from map_discovery import CampaignMap, DiscoveryKnowledge, MapDiscoveryError, build_catalog
from map_knowledge import knowledge_catalog, configuration_lines
from campaign_save import MigrationRegistry


class VisitKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.catalog = build_catalog(json.loads((PROJECT / 'scenario/world/world.json').read_text()),
                                     json.loads((PROJECT / 'scenario/maps/world-map.json').read_text()))

    def test_live_catalog_matches_reference_names_membership_and_all_settlements(self):
        live = knowledge_catalog(PROJECT)
        expected = {row['id']: row for row in self.catalog['settlements']}
        actual = {row['id']: row for row in live['settlements']}
        for ident, row in expected.items():
            self.assertEqual((row['name'], row['regionId']), (actual[ident]['name'], actual[ident]['regionId']))
        world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.assertEqual({row['id'] for row in world['settlements']}, set(actual))
        self.assertEqual(['europe'], [row['id'] for row in live['regions'] if row['initiallyKnown']])
        self.assertNotIn('hidden_desert_ruin', json.dumps(live))
        self.assertEqual(len(actual), '\n'.join(configuration_lines(live)).count('.addSettlement('))

    def test_registered_command_cases_match_reference_discovery_policy(self):
        knowledge = DiscoveryKnowledge(self.catalog)
        knowledge.reveal_region('europe')
        knowledge.visit_settlement('lisbon')
        knowledge.visit_settlement('seville')
        view = CampaignMap(self.catalog, knowledge, 'europe', 'europe')
        self.assertEqual(['lisbon', 'seville'], [row['id'] for row in view.open_region('europe')['settlements']])
        before = view.focus
        for ident in ('africa', 'missing', 'europe extra'):
            with self.assertRaises(MapDiscoveryError):
                view.open_region(ident)
            self.assertEqual(before, view.focus)
        for ident in ('london', 'hidden_desert_ruin', 'missing'):
            with self.assertRaises(MapDiscoveryError):
                view.focus_location(ident)
        knowledge.reveal_region('africa')
        view.set_command_region('africa')
        regional = view.open_region('africa')
        self.assertEqual([], regional['settlements'])
        self.assertEqual([], regional['pointsOfInterest'])
        focused = view.focus_location('seville')
        self.assertEqual(('europe', 'africa', 'exact'),
                         (focused['physicalRegionId'], focused['commandRegionId'], focused['focus']['precision']))

    def test_schema_ten_preserves_existing_precision_search_areas_and_treasures(self):
        knowledge = DiscoveryKnowledge(self.catalog)
        knowledge.visit_settlement('lisbon')
        knowledge.reveal_approximate('hidden_desert_ruin', [dict(id='clue', regionId='africa', shape='circle', center=dict(x=4,y=5), radius=6)])
        authority = dict(mapKnowledge=knowledge.export_state(), treasures=dict(resolved={'candidate':'sealed'}, knowledge={'precision':'exact'}))
        document = dict(schemaVersion=9, state=dict(world=authority))
        original = copy.deepcopy(document)
        migrated = MigrationRegistry().migrate(document)
        self.assertEqual(10, migrated['schemaVersion'])
        self.assertEqual(original['state'], migrated['state'])
        self.assertEqual(original, document)

    def test_framework_catalog_is_scenario_owned(self):
        catalog = knowledge_catalog(PROJECT.parent / 'conformance-campaign')
        self.assertEqual({'reed_harbor', 'stone_station'}, {row['id'] for row in catalog['settlements']})
        self.assertNotIn('europe', json.dumps(catalog))


if __name__ == '__main__':
    unittest.main()
