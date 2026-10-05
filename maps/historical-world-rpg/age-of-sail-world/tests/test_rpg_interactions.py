import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from package_wurst_map import generate, load_config
from package_wurst_campaign import load_campaign_config
from materialize_physical_map import materialize, physical_layout
from physical_interactions import interaction_locations
from wurst_execution import discover


class RpgInteractionGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.generated = Path(cls.temp.name) / 'generated'
        cls.config = load_config(PROJECT / 'package.json')
        cls.campaign = load_campaign_config(PROJECT / 'physical-maps.json')
        cls.world = json.loads(cls.config.scenario_file.read_text())
        generate(cls.config, cls.generated)
        cls.runtime = json.loads((cls.generated / 'scenario-runtime.json').read_text())
        cls.locations = cls.runtime['interactionLocations']
        cls.points = {row['id']: row for row in cls.locations if row['kind'] != 'region'}

    def test_every_settlement_and_quest_alias_matches_materialized_coordinates(self):
        self.assertEqual({s['id'] for s in self.world['settlements']},
                         {s['id'] for s in self.locations if s['kind'] == 'settlement'})
        for physical in self.campaign.maps:
            if physical.bootstrap:
                continue
            folder = Path(self.temp.name) / physical.id
            shutil.copytree(physical.source_map, folder)
            settlements = [s for s in self.world['settlements']
                           if s['regionalInstanceId'] in physical.regional_instance_ids]
            manifest = materialize(PROJECT, folder, self.generated, physical,
                                   {'settlementDefinitions': settlements})
            for settlement in manifest['objects']['settlements']:
                with self.subTest(settlement=settlement['id']):
                    point = self.points[settlement['id']]
                    self.assertEqual(physical.id, point['mapId'])
                    self.assertEqual(settlement['world'], point['world'])
        for alias in self.world['questLocations']:
            record, settlement = self.points[alias['id']], self.points[alias['settlementId']]
            self.assertEqual(settlement['world'], record['world'])
            self.assertEqual(settlement['mapId'], record['mapId'])
            self.assertEqual(settlement['id'], record['eventId'])
        for quest in self.world['quests']:
            self.assertIn(quest['journal']['turnIn']['id'], self.points)
        for origin in self.runtime['newCampaignOrigins']:
            start = origin['startingLocation']
            self.assertEqual(start['worldPosition'], self.points[start['settlementId']]['world'])

    def test_candidates_use_compatible_free_cells_and_regions_only_cover_own_maps(self):
        candidates = self.runtime['treasures']['candidateLocations']
        self.assertEqual({c['id'] for c in candidates if c['accessible']},
                         {r['id'] for r in self.locations if r['kind'] == 'treasure'})
        for physical in self.campaign.maps:
            if physical.bootstrap:
                continue
            width, height, cells, layouts = physical_layout(self.generated, physical)
            local = [r for r in self.locations if r['mapId'] == physical.id]
            reserved = {tuple(r['world']) for r in local if r['kind'] == 'settlement'}
            for record in local:
                if record['kind'] == 'region':
                    self.assertIn(record['id'], physical.logical_region_ids)
                    self.assertIn(record['bounds'], [[(ox-width/2)*128., (oy-height/2)*128.,
                        (ox+iw-width/2)*128., (oy+ih-height/2)*128.] for ox, oy, iw, ih in layouts.values()])
                elif record['kind'] == 'treasure':
                    x, y = record['world']
                    cx, cy = int(x / 128 + width / 2), int(y / 128 + height / 2)
                    cell = cells[cy * width + cx]
                    self.assertIn(cell, (1, 2))
                    self.assertTrue(set(record['movements']) <= {0 if cell == 1 else 1, 2, 3})
                    self.assertNotIn(tuple(record['world']), reserved)
                    reserved.add(tuple(record['world']))

    def test_inaccessible_candidates_are_not_targets_and_bad_map_bindings_fail_generation(self):
        treasures = copy.deepcopy(self.runtime['treasures'])
        candidate = treasures['candidateLocations'][0]
        candidate['accessible'] = False
        locations = interaction_locations(PROJECT, self.generated, self.world, self.campaign.maps,
                                          treasures, [p for _, p in self.config.regional_terrain])
        self.assertNotIn(candidate['id'], {r['id'] for r in locations})
        candidate['accessible'] = True
        for invalid_map in ('africa', 'unknown_map'):
            candidate['physicalMapId'] = invalid_map
            with self.assertRaisesRegex(ValueError, 'incompatible physical map'):
                interaction_locations(PROJECT, self.generated, self.world, self.campaign.maps,
                                      treasures, [p for _, p in self.config.regional_terrain])

    def test_command_regressions_are_required_by_pinned_execution_discovery(self):
        tests = {row['id'].split(':')[1] for row in discover(PROJECT)}
        self.assertTrue({
            'rpgCommandsRejectRemoteDistantUnknownAndInvalidRecipientsWithoutMutation',
            'rpgTurnInRejectsAnotherAuthoredDestinationDespiteLocalPartyAndReadyObjectives',
            'rpgLocalTurnInUsesAuthoredDestinationAndSurvivesMissingBuildings',
            'rpgLocalInteractionUsesQuestAliasesAndEligibleActorForAutomaticTurnIn',
            'rpgTreasureCommandsRequireLocalCluesAndResolvedGeneratedCandidate',
            'rpgRevalidatesActorAtCommitAndPhysicalMapDuringReconstruction',
            'rpgCommitRechecksCoordinatesAndLoadedMapWithoutRetainingAuthorization',
            'rpgRemoteCommandAndTrackingNeverConferPhysicalPresence',
        } <= tests)


if __name__ == '__main__':
    unittest.main()
