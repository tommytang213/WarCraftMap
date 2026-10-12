"""Complete emitted-definition census and player_items.compare execution vectors."""
import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT.parent / '_shared/engine')]
from package_wurst_map import generate, load_config, catalogue_paths
from equipment_items import item_definitions_wurst
from player_items import compare, validate_catalog, PlayerItemError

LITERAL = r'"(?:[^"\\]|\\.)*"'


def emitted_items(source):
    """Decode executable Wurst registrations independently of generator output JSON."""
    result = {}
    for match in re.finditer(r'let (item\d+)=new RpgItem\((.*?)\)\n(.*?)'
                             r'\truntime.inventory.registerItem\(\1\)', source, re.S):
        variable, constructor, body = match.groups()
        ident, name, slot, rarity, level = json.loads('[' + constructor + ']')
        assert ident not in result, f'duplicate item {ident}'
        fields = {field: json.loads(value) for field, value in
                  re.findall(rf'{variable}\.(\w+)=({LITERAL}|-?\d+|true|false)\n', body)}
        stats = re.findall(rf'{variable}\.addStat\(({LITERAL}),(-?\d+)\)', body)
        assert len({key for key, _ in stats}) == len(stats), 'duplicate stat'
        conditions = [json.loads('[' + arguments + ']') for arguments in
                      re.findall(rf'{variable}\.addConditionalEffect\((.*?)\)\n', body)]
        for effect_id, condition, descriptor in conditions:
            assert json.loads(descriptor)['id'] == effect_id
            assert json.loads(descriptor)['condition'] == condition
        result[ident] = {
            'id': ident, 'name': name, 'slot': slot, 'rarity': rarity, 'itemLevel': level,
            **fields,
            'majorStats': {json.loads(key): int(value) for key, value in stats},
            'effectIds': [json.loads(value) for value in re.findall(rf'{variable}\.addEffect\(({LITERAL})\)', body)],
            'conditionalEffects': [json.loads(value[2]) for value in conditions],
            **{field: [json.loads(value) for value in re.findall(rf'{variable}\.add{method}\(({LITERAL})\)', body)]
               for field, method in (('technologyIds', 'Technology'), ('institutionIds', 'Institution'))},
        }
    return result


def expected_items(catalogue):
    rarities = {row['id']: row for row in catalogue['rarities']}
    result = {}
    canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    for row in catalogue['items']:
        comparison, requirements, provenance = (row[key] for key in ('comparison', 'requirements', 'provenance'))
        result[row['id']] = {
            'id': row['id'], 'name': row['name'], 'slot': (comparison.get('slotIds') or [row['category']])[0],
            'slotIds': canonical(comparison.get('slotIds', [])), 'category': row['category'],
            'rarity': row['rarityId'], 'rarityName': rarities[row['rarityId']]['name'],
            'rarityRank': rarities[row['rarityId']]['rank'], 'itemLevel': row['itemLevel'],
            'unique': row['unique'], 'setId': comparison.get('setId', ''),
            'provenance': canonical(provenance), 'provenanceKind': provenance['kind'],
            'identityId': provenance.get('identityId', ''), 'requirements': canonical(requirements),
            'startYear': requirements.get('startYear', 0), 'endYear': requirements.get('endYear', 0),
            'requiredLevel': requirements.get('requiredLevel', 0),
            'maxEnhancement': row['enhancement']['maxRank'], 'maxRestoration': row['enhancement']['maxRestoration'],
            'majorStats': comparison.get('majorStats', {}), 'effectIds': comparison.get('effectIds', []),
            'conditionalEffects': comparison.get('conditionalEffects', []),
            **{field: requirements.get(field, []) for field in ('technologyIds', 'institutionIds')},
        }
    return result


def comparison_vectors(catalogue):
    items = catalogue['items']
    pulwar = next(row for row in items if row['id'] == 'afghan_pulwar')
    conditional = next(row for row in items if row['comparison'].get('conditionalEffects'))
    primary = [row for row in items if row['comparison'].get('slotIds') == ['primary']]
    disjoint = next(row for row in primary if not set(row['comparison']['majorStats']) & set(pulwar['comparison']['majorStats']))
    same = next(row for row in primary if row != pulwar and set(row['comparison']['majorStats']) & set(pulwar['comparison']['majorStats']))
    pairs = [(pulwar, None), (pulwar, pulwar), (pulwar, disjoint), (disjoint, pulwar),
             (pulwar, same), (same, pulwar), (conditional, None)]
    source = 'package ItemComparisonVectorsTests\n\nimport WarcraftRpgRuntime\nimport ScenarioData\n\n'
    source += '// Generated from player_items.compare by tests/test_item_definitions.py --write-vectors.\n'
    source += '@test function itemComparisonsMatchHeadlessContract()\n\tlet runtime = new WarcraftRpgRuntime(null)\n\tconfigureGeneratedRpg(runtime)\n'
    for index, (candidate, equipped) in enumerate(pairs):
        expected = compare(catalogue, candidate['id'], equipped['id'] if equipped else None)
        source += f'\tlet comparison{index} = new ItemComparison(runtime.inventory.getItem("{candidate["id"]}"), '
        source += f'runtime.inventory.getItem("{equipped["id"]}"))\n' if equipped else 'null)\n'
        source += f'\tcomparison{index}.statCount.assertEquals({len(expected["deltas"])})\n'
        for ident, delta in expected['deltas'].items():
            source += f'\tcomparison{index}.delta("{ident}").assertEquals({delta})\n'
            source += f'\tcomparison{index}.candidate.statValue("{ident}").assertEquals({expected["majorStats"].get(ident, 0)})\n'
        for field, method in (('effectIds', 'effectCount'), ('conditionalEffects', 'conditionalCount')):
            source += f'\tcomparison{index}.candidate.{method}.assertEquals({len(expected[field])})\n'
        for c, descriptor in enumerate(expected['conditionalEffects']):
            source += f'\tcomparison{index}.candidate.conditionalEffects[{c}].id.assertEquals({json.dumps(descriptor["id"])})\n'
            source += f'\tcomparison{index}.candidate.conditionalEffects[{c}].condition.assertEquals({json.dumps(descriptor["condition"])})\n'
        source += f'\tdestroy comparison{index}\n'
    return source


class ItemDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.catalogue = json.loads(catalogue_paths(PROJECT)['inventory'].read_text())
        cls.generated = Path(cls.temp.name)
        generate(load_config(PROJECT / 'package.json'), cls.generated)
        cls.source = (cls.generated / 'ScenarioData.wurst').read_text()

    def assert_catalogue(self, source, catalogue=None):
        catalogue = catalogue or self.catalogue
        actual = emitted_items(source)
        for row in actual.values():
            self.assertTrue(row.pop('requirementsText'))
        self.assertEqual(expected_items(catalogue), actual)

    def test_complete_composed_catalogue_retains_every_definition_dimension(self):
        self.assertEqual(468, len(self.catalogue['items']))
        self.assert_catalogue(self.source)
        runtime = json.loads((self.generated / 'scenario-runtime.json').read_text())
        self.assertEqual(self.catalogue, runtime['inventory'])
        self.assertEqual({'meleePower': 40, 'mountedPower': 12}, emitted_items(self.source)['afghan_pulwar']['majorStats'])

    def test_omitted_stat_effect_and_conditional_descriptor_are_detected(self):
        for method in ('Stat', 'Effect', 'ConditionalEffect'):
            broken, count = re.subn(rf'^\titem\d+\.add{method}\([^\n]+\)\n', '', self.source, count=1, flags=re.M)
            self.assertEqual(count, 1)
            with self.subTest(method=method), self.assertRaises(AssertionError):
                self.assert_catalogue(broken)

    def test_complete_conditional_descriptor_and_provenance_survive_escaping(self):
        catalogue = copy.deepcopy(self.catalogue)
        row = catalogue['items'][0]
        row['comparison']['conditionalEffects'] = [{'id': 'boarding_edge', 'condition': 'aboard "ship"\nin rain',
            'metadata': {'route': 'sea\\coast', 'detail': 'line one\nline two'}}]
        row['provenance']['source'] = {'work': 'Captain "A"', 'note': 'archive\\page'}
        self.assert_catalogue('\n'.join(item_definitions_wurst(catalogue)), catalogue)

    def test_unrepresentable_definitions_fail_instead_of_truncating(self):
        for field, values in {
            'majorStats': [None, [], {'bad': True}, {'bad': 1.5}, {'bad': 2**31}, {'': 1}, {f'stat{i}': i for i in range(65)}],
            'effectIds': [None, 'armor_guard', ['armor_guard'] * 65],
            'conditionalEffects': [None, [{'id': 'boarding_edge'}], [{'id': 'boarding_edge', 'condition': ''}],
                                   [{'id': 'boarding_edge', 'condition': 'sea'}] * 65],
        }.items():
            for value in values:
                fixture = copy.deepcopy(self.catalogue)
                fixture['items'][0]['comparison'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(PlayerItemError):
                    validate_catalog(fixture)

    def test_checked_in_wurst_vectors_match_headless_compare(self):
        self.assertEqual(comparison_vectors(self.catalogue), (PROJECT / 'wurst/ItemComparisonVectorsTests.wurst').read_text())

    def test_stat_bindings_have_no_maximum_life_fallback(self):
        source = (PROJECT.parent / '_shared/wurst/WarcraftRpgProjections.wurst').read_text()
        projector = source.split('public class WarcraftRpgProjections', 1)[1]
        self.assertNotIn('setMaxLife(', projector)
        self.assertNotIn('applyPower(', projector)
        self.assertIn('ITEM_BINDINGS_PENDING', projector)


if __name__ == '__main__':
    if '--write-vectors' in sys.argv:
        catalogue = json.loads(catalogue_paths(PROJECT)['inventory'].read_text())
        (PROJECT / 'wurst/ItemComparisonVectorsTests.wurst').write_text(comparison_vectors(catalogue))
    else:
        unittest.main()
