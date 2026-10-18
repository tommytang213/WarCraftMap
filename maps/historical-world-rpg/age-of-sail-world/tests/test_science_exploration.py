"""Validate real scenario compilation. Production mutations run in Wurst tests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from science_exploration import configuration


class ScienceCompilationTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.data = json.loads((PROJECT / 'scenario/progression/science-exploration.json').read_text())
        self.authored = {}
        for path in (PROJECT / 'scenario/settlements').glob('*-1450.json'):
            for row in json.loads(path.read_text())['settlements']:
                self.authored[row['id']] = ('region', row)
        self.settlements = [dict(id='london', x=100., y=200.)]
        self.trade = ['runtime.registerMarketProfile("london","cloth",90,1000)']

    def compile(self, project=PROJECT, world=None):
        return configuration(project, world or self.world, self.settlements, self.authored, self.trade)

    def test_exact_design_bindings_values_eras_inputs_and_actor_routes(self):
        source, catalog, paths = self.compile()
        self.assertEqual({('barometric_measurement', 1000), ('botanical_collecting', 1000),
                          ('calculus_methods', 500)}, {(e['nodeId'], e['bonusBasisPoints']) for e in catalog['effects']})
        self.assertIn('site0.unitTypeId', source)
        self.assertIn('site1.unitTypeId', source)
        self.assertIn('site1.stationX = 100.0', source)
        self.assertIn('"scientific_societies", "cloth"', source)
        self.assertEqual(3, len(paths))
        self.assertNotIn('unlock(', source)
        self.assertEqual(source, self.compile()[0])

    def test_invalid_conditions_bills_materials_routes_and_bindings_reject(self):
        mutations = [lambda d: d['sites'][0].update(equipmentCost=0),
                     lambda d: d['sites'][0].update(dailyWork=True),
                     lambda d: d['sites'][0].update(forceId='english_guard_formation'),
                     lambda d: d['sites'][0].update(routeId='unknown'),
                     lambda d: d['sites'][1].update(routeZoneIds=['english_channel']),
                     lambda d: d['sites'][1].update(capability='reveal_hidden_map'),
                     lambda d: d['sites'][2].update(prerequisite='unknown'),
                     lambda d: d['sites'][2].update(good='invented_stock'),
                     lambda d: d['sites'][2].update(weatherDays=366),
                     lambda d: d['sites'].append(d['sites'][0])]
        for change in mutations:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name in ('scenario/progression', 'scenario/naval'):
                    (root / name).mkdir(parents=True)
                for name in ('scenario/progression/gameplay-effect-design.json', 'scenario/naval/navigation-efficiency.json'):
                    (root / name).write_bytes((PROJECT / name).read_bytes())
                data = copy.deepcopy(self.data); change(data)
                (root / 'scenario/progression/science-exploration.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError): self.compile(root)
        world = copy.deepcopy(self.world)
        next(n for n in world['technologies'] if n['id'] == 'calculus_methods')['unlocks'] = []
        with self.assertRaisesRegex(ValueError, 'exact typed'): self.compile(world=world)

    def test_framework_without_science_contract_registers_empty_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, catalog, paths = self.compile(Path(tmp))
        self.assertIn('\tskip', source)
        self.assertEqual(({}, []), (catalog, paths))
