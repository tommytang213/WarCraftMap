"""All authored equipment research gates survive the production generator."""
import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT.parent / '_shared/engine')]
from package_wurst_map import generate, load_config, catalogue_paths, PackagingError
from player_items import validate_catalog, PlayerItemError


def generated_equipment(source):
    result = {}
    for match in re.finditer(r'let (item\d+)=new RpgItem\("([^"]+)".*?'
                             r'runtime\.inventory\.registerItem\(\1\)', source, re.S):
        variable, ident = match.group(1, 2)
        if ident in result:
            raise AssertionError(f'duplicate generated item: {ident}')
        result[ident] = {
            field: re.findall(rf'{variable}\.add{method}\("([^"]+)"\)', match[0])
            for field, method in (('technologyIds', 'Technology'), ('institutionIds', 'Institution'))
        }
    return result


def generated_sets(source):
    """Read emitted calls, not the JSON copy of the source catalogue."""
    result = {}
    for match in re.finditer(r'let (equipmentSet\d+)=new EquipmentSet\("([^"]+)"\).*?'
                             r'runtime\.inventory\.registerSet\(\1\)', source, re.S):
        variable, ident = match.group(1, 2)
        if ident in result:
            raise AssertionError(f'duplicate set: {ident}')
        block = match[0]
        pieces = []
        for piece in re.finditer(rf'let ({variable}Piece\d+)=new EquipmentSetPiece\("([^"]+)"\)(.*?)'
                                 rf'{variable}\.addPiece\(\1\)', block, re.S):
            pieces.append({'id': piece[2],
                           'itemTypeIds': re.findall(rf'{piece[1]}\.addItem\("([^"]+)"\)', piece[3]),
                           'equipmentSlotTypes': re.findall(rf'{piece[1]}\.addSlot\("([^"]+)"\)', piece[3])})
        thresholds = []
        for tier in re.finditer(rf'let ({variable}Tier\d+)=new EquipmentSetThreshold\("([^"]+)",(\d+),"([^"]+)"\)(.*?)'
                                rf'{variable}\.addThreshold\(\1\)', block, re.S):
            thresholds.append({'id': tier[2], 'pieceCount': int(tier[3]), 'tierPolicy': tier[4],
                               'effectIds': re.findall(rf'{tier[1]}\.addEffect\("([^"]+)"\)', tier[5]),
                               'replacesThresholdIds': re.findall(rf'{tier[1]}\.addReplacement\("([^"]+)"\)', tier[5])})
        result[ident] = {'pieces': pieces, 'thresholds': thresholds,
                         'allowDuplicatePieces': f'{variable}.allowDuplicatePieces=true' in block}
    return result


class EquipmentGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.config = load_config(PROJECT / 'package.json')
        cls.paths = catalogue_paths(PROJECT)
        cls.catalogue = json.loads(cls.paths['inventory'].read_text())
        cls.generated = Path(cls.temp.name) / 'generated'
        generate(cls.config, cls.generated)
        cls.source = (cls.generated / 'ScenarioData.wurst').read_text()
        cls.expected = {
            row['id']: {field: row['requirements'].get(field, [])
                        for field in ('technologyIds', 'institutionIds')}
            for row in cls.catalogue['items']
        }

    def test_every_generated_set_and_runtime_record_matches_authoritative_catalogue(self):
        self.assertEqual(self.expected, generated_equipment(self.source))
        payload = json.loads((self.generated / 'scenario-runtime.json').read_text())
        self.assertEqual(self.catalogue, payload['inventory'])
        multiple = {ident for ident, req in self.expected.items() if len(req['technologyIds']) > 1}
        self.assertEqual(multiple, {'percussion_jungle_musket', 'precision_court_theodolite',
            'steam_era_coastal_manual', 'natural_history_island_atlas', 'kangxi_court_compass'})
        self.assertEqual(self.expected['precision_court_theodolite'], {
            'technologyIds': ['precision_engineering', 'cadastral_survey'],
            'institutionIds': ['scientific_societies']})

    def test_first_only_regression_loses_exactly_the_five_multi_technology_items(self):
        seen = set()
        def truncate(match):
            key = match.group(1, 2)
            if key in seen:
                return ''
            seen.add(key)
            return match[0]
        broken = re.sub(r'\t(item\d+)\.add(Technology|Institution)\("[^"]+"\)\n', truncate, self.source)
        actual = generated_equipment(broken)
        self.assertEqual({ident for ident in self.expected if actual[ident] != self.expected[ident]},
                         {ident for ident, req in self.expected.items() if len(req['technologyIds']) > 1})
        self.assertNotEqual(self.expected, actual)

    def generate_fixture(self, requirements):
        catalogue = copy.deepcopy(self.catalogue)
        item = next(row for row in catalogue['items'] if row['id'] == 'precision_court_theodolite')
        item['requirements'].update(requirements)
        path = Path(self.temp.name) / 'fixture.json'
        path.write_text(json.dumps(catalogue))
        destination = Path(self.temp.name) / 'fixture'
        with patch('package_wurst_map.catalogue_paths', return_value={**self.paths, 'inventory': path}):
            generate(self.config, destination)
        return generated_equipment((destination / 'ScenarioData.wurst').read_text())

    def test_multiple_institutions_and_more_than_two_technologies_survive_generation(self):
        requirements = {
            'technologyIds': ['precision_engineering', 'cadastral_survey', 'experimental_method'],
            'institutionIds': ['scientific_societies', 'movable_type_printing'],
        }
        self.assertEqual(self.generate_fixture(requirements)['precision_court_theodolite'], requirements)

    def test_generation_rejects_missing_and_wrong_kind_research_references(self):
        for requirements in ({'technologyIds': ['unknown_research']},
                             {'institutionIds': ['unknown_research']},
                             {'technologyIds': ['scientific_societies']},
                             {'institutionIds': ['precision_engineering']}):
            with self.subTest(requirements=requirements), self.assertRaisesRegex(PackagingError, 'unknown .*Ids'):
                self.generate_fixture(requirements)

    def test_catalogue_rejects_malformed_duplicate_and_over_capacity_id_lists(self):
        for field in ('technologyIds', 'institutionIds'):
            for ids in (None, 'precision_engineering', [''], ['Precision'], ['craft~guild'],
                        ['other:craft'], ['craft,forged'], ['craft|forged'], ['craft;forged'],
                        [1], [True], ['craft', 'craft'], [f'node_{i}' for i in range(513)]):
                catalogue = copy.deepcopy(self.catalogue)
                catalogue['items'][0]['requirements'][field] = ids
                with self.subTest(field=field, ids=ids), self.assertRaises(PlayerItemError):
                    validate_catalog(catalogue)

    def test_generation_is_deterministic(self):
        destination = Path(self.temp.name) / 'again'
        generate(self.config, destination)
        self.assertEqual(self.source, (destination / 'ScenarioData.wurst').read_text())

    def expected_sets(self):
        items = {row['id']: row for row in self.catalogue['items']}
        return {row['id']: {
            'allowDuplicatePieces': False,
            'pieces': [{'id': ident, 'itemTypeIds': [ident],
                        'equipmentSlotTypes': sorted(items[ident]['comparison'].get('slotIds') or [items[ident]['category']])}
                       for ident in sorted(row['itemTypeIds'])],
            'thresholds': [{'id': f'pieces_{tier["pieceCount"]}', 'tierPolicy': 'cumulative',
                            'replacesThresholdIds': [], **tier} for tier in row['thresholds']],
        } for row in self.catalogue['equipmentSets']}

    def test_all_51_sets_retain_all_151_tiers_pieces_and_effect_identities(self):
        expected = self.expected_sets()
        self.assertEqual(51, len(expected))
        self.assertEqual(49, sum(len(row['thresholds']) > 2 for row in expected.values()))
        self.assertEqual(151, sum(len(row['thresholds']) for row in expected.values()))
        self.assertEqual(expected, generated_sets(self.source))
        payload = json.loads((self.generated / 'scenario-runtime.json').read_text())
        self.assertEqual(51, len(payload['equipmentSetDefinitions']['equipmentSets']))

    def test_negative_fixtures_detect_middle_tier_and_effect_identity_loss(self):
        expected = self.expected_sets()
        def truncate(match):
            if len(re.findall(r'new EquipmentSetThreshold', match[0])) < 3:
                return match[0]
            return re.sub(r'\tlet (equipmentSet\d+Tier1)=new EquipmentSetThreshold\([^\n]+\)\n'
                          r'.*?\t(equipmentSet\d+)\.addThreshold\(\1\)\n', '', match[0], flags=re.S)
        dropped = re.sub(r'let (equipmentSet\d+)=new EquipmentSet\("[^\"]+"\).*?'
                         r'runtime\.inventory\.registerSet\(\1\)', truncate, self.source, flags=re.S)
        actual = generated_sets(dropped)
        self.assertEqual(49, sum(expected[ident] != actual[ident] for ident in expected))
        counts = re.sub(r'(\.addEffect\(")[^"]+("\))', r'\g<1>1\2', self.source)
        self.assertNotEqual(expected, generated_sets(counts))

    def test_set_reference_and_policy_validation_rejects_bad_definitions(self):
        def check(mutate):
            data = copy.deepcopy(self.catalogue)
            mutate(data['equipmentSets'][0])
            with self.assertRaises(PlayerItemError):
                validate_catalog(data)
        for value in (['missing'], [], ['set_resilience', 'set_resilience'], ['bad|id'], None):
            check(lambda row: row['thresholds'][0].update(effectIds=value))
        for value in (['missing'], [], ['buff_coat', 'buff_coat'], None):
            check(lambda row: row.update(itemTypeIds=value))
        for value in (0, True, '2', 5):
            check(lambda row: row['thresholds'][0].update(pieceCount=value))
        check(lambda row: row['thresholds'][1].update(pieceCount=2))
        check(lambda row: row['thresholds'][1].update(id='pieces_2'))
        check(lambda row: row.update(allowDuplicatePieces='yes'))
        check(lambda row: row.update(thresholds=row['thresholds'] * 22))
        check(lambda row: row['thresholds'][0].update(effectIds=[f'effect_{i}' for i in range(65)]))
        check(lambda row: row['thresholds'][1].update(tierPolicy='invented'))
        check(lambda row: row['thresholds'][1].update(tierPolicy='exclusive'))
        check(lambda row: row['thresholds'][1].update(tierPolicy='replacement'))
        check(lambda row: row['thresholds'][1].update(tierPolicy='replacement', replacesThresholdIds=['missing']))
        check(lambda row: row['thresholds'][0].update(tierPolicy='replacement', replacesThresholdIds=['pieces_3']))

    def test_generator_rejects_unresolved_effect_references(self):
        data = copy.deepcopy(self.catalogue)
        data['equipmentSets'][0]['thresholds'][1]['effectIds'] = ['missing_effect']
        path = Path(self.temp.name) / 'bad-set.json'
        path.write_text(json.dumps(data))
        with patch('package_wurst_map.catalogue_paths', return_value={**self.paths, 'inventory': path}):
            with self.assertRaisesRegex(PackagingError, 'missing effect'):
                generate(self.config, Path(self.temp.name) / 'bad-set-generated')


if __name__ == '__main__':
    unittest.main()
