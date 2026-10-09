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


if __name__ == '__main__':
    unittest.main()
