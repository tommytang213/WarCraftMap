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
                          ('calculus_methods', 500), ('chemical_classification', 400)}, {(e['nodeId'], e['bonusBasisPoints']) for e in catalog['effects']})
        self.assertIn('site0.unitTypeId', source)
        self.assertIn('site1.unitTypeId', source)
        self.assertIn('site1.stationX = 100.0', source)
        self.assertIn('"scientific_societies", "cloth"', source)
        self.assertEqual(4, len(paths))
        self.assertIn('site2.observationMetric = "repeatable_observation_efficiency"', source)
        self.assertIn('site2.minimumAdministration = 40', source)
        self.assertIn('|chemical_classification|', source)
        self.assertNotIn('|flintlock_drill|', source)
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

    def test_observation_contract_rejects_bad_scope_bounds_identity_and_staff(self):
        contract_path = 'scenario/progression/chemical-classification.json'
        contract = json.loads((PROJECT / contract_path).read_text())
        mutations = [lambda d: d.update(bonusBasisPoints=299),
                     lambda d: d.update(bonusBasisPoints=601),
                     lambda d: d.update(bonusBasisPoints=True),
                     lambda d: d.update(minimumAdministration=0),
                     lambda d: d.update(minimumAdministration=True),
                     lambda d: d.update(metric='global_research'),
                     lambda d: d.update(siteId='missing'),
                     lambda d: d.update(siteId='channel_weather_survey'),
                     lambda d: d.update(targetBranchId='missing'),
                     lambda d: d['unlock'].update(contentId='invented')]
        for change in mutations:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name in ('scenario/progression', 'scenario/naval'):
                    (root / name).mkdir(parents=True)
                for name in ('scenario/progression/gameplay-effect-design.json',
                             'scenario/progression/science-exploration.json',
                             'scenario/naval/navigation-efficiency.json'):
                    (root / name).write_bytes((PROJECT / name).read_bytes())
                data = copy.deepcopy(contract); change(data)
                (root / contract_path).write_text(json.dumps(data))
                with self.assertRaises(ValueError): self.compile(root)

    def test_observation_binding_requires_verified_complete_execution_and_exact_traces(self):
        from science_exploration import verified_bindings, CHEMICAL_TESTS
        from unittest.mock import patch
        prefix = 'wurst/ScienceExplorationTests.wurst:'
        name = prefix + 'chemicalRegisteredResearchCommitsExactScientificWorkAgainstIdenticalControl'
        report = dict(tests=[dict(id=prefix + t, status='pass') for t in CHEMICAL_TESTS],
                      productionCoverage={'tests': {name: ['science_registration', 'science_action',
                        'science_advance', 'science_pay', 'science_complete', 'dispatch']}})
        self.assertEqual(set(), verified_bindings(PROJECT))
        with patch('integration_evidence.verify_execution_coverage', side_effect=ValueError('stale')):
            self.assertEqual(set(), verified_bindings(PROJECT, report, b'log', 'revision'))
        # Synthetic audit protocol only, never execution evidence.
        with patch('integration_evidence.verify_execution_coverage'):
            self.assertEqual({('modifier', 'progression_chemical_classification')},
                             verified_bindings(PROJECT, report, b'log', 'revision'))
            for probe in report['productionCoverage']['tests'][name][:]:
                invalid = copy.deepcopy(report)
                invalid['productionCoverage']['tests'][name].remove(probe)
                self.assertEqual(set(), verified_bindings(PROJECT, invalid, b'log', 'revision'))
            for case in report['tests']:
                invalid = copy.deepcopy(report)
                invalid['tests'] = [t for t in invalid['tests'] if t['id'] != case['id']]
                self.assertEqual(set(), verified_bindings(PROJECT, invalid, b'log', 'revision'))
