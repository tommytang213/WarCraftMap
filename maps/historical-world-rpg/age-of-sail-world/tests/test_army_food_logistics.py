"""Real scenario compiler, sensitivity, packaging and fail-closed evidence guards.

Gameplay outcomes execute in ArmyFoodLogisticsTests with the pinned interpreter.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from army_food_logistics import configuration, verified_bindings, REQUIRED_TESTS


class LogisticsCompilationTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.data = json.loads((PROJECT / 'scenario/progression/army-food-logistics.json').read_text())
        self.finance = json.loads((PROJECT / 'scenario/progression/trade-finance.json').read_text())
        self.authored = {}
        for path in (PROJECT / 'scenario/settlements').glob('*-1450.json'):
            for row in json.loads(path.read_text())['settlements']:
                self.authored[row['id']] = ('region', row)
        self.positions = [{'id': sid} for sid in self.authored]
        self.trade = [f'runtime.registerMarketProfile("{sid}","{good}",90,1000)'
                      for sid in self.authored for good in ('grain', 'timber')]

    def compile(self, project=PROJECT):
        return configuration(project, self.world, self.positions, self.authored, self.trade, self.finance)

    def fixture(self, tmp, data=None, design=None, routes=None):
        root = Path(tmp)
        for relative, content in {
            'scenario/progression/army-food-logistics.json': data or self.data,
            self.data['goodsSource']: json.loads((PROJECT / self.data['goodsSource']).read_text()),
            self.data['designSource']: design or json.loads((PROJECT / self.data['designSource']).read_text()),
            self.data['canalRoutes'][0]['routeSource']: routes or json.loads((PROJECT / self.data['canalRoutes'][0]['routeSource']).read_text()),
        }.items():
            p = root / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(content))
        return root

    def test_exact_contracts_era_stock_warehouses_and_existing_paid_geography_compile(self):
        source, catalog, paths = self.compile()
        self.assertEqual({('campaign_bakeries', 800), ('canal_logistics', 1000)},
                         {(e['nodeId'], e['bonusBasisPoints']) for e in catalog['effects']})
        self.assertIn('"grain_supply_spoilage_reduction", 800, 620548', source)
        self.assertIn('"canal_freight_throughput", 1000, 646115', source)
        self.assertIn('ledger.foodShipment = 100', source)
        self.assertIn('route0.freightDestination = "zhenjiang"', source)
        self.assertIn('route0.freightCapacity = 100', source)
        self.assertIn('yangzhou', catalog['foodSiteIds'])
        self.assertEqual(5, len(paths))
        self.assertEqual(source, self.compile()[0])
        self.assertNotIn('unlock(', source)

    def test_other_scenarios_have_no_content_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, catalog, paths = self.compile(Path(tmp))
        self.assertIn('\tskip', source)
        self.assertEqual(({}, []), (catalog, paths))

    def test_scenario_owned_quantities_capacity_and_bonus_sensitivity(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = copy.deepcopy(self.data)
            data['food']['shipmentUnits'] = 120
            data['canalRoutes'][0]['dailyCapacity'] = 200
            design = json.loads((PROJECT / self.data['designSource']).read_text())
            next(e for e in design['effects'] if e['nodeId'] == 'campaign_bakeries')['bonusBasisPoints'] = 600
            source, catalog, _ = self.compile(self.fixture(tmp, data, design))
        self.assertIn('ledger.foodShipment = 120', source)
        self.assertIn('route0.freightCapacity = 200', source)
        self.assertIn('"grain_supply_spoilage_reduction", 600,', source)
        self.assertEqual(120, catalog['food']['shipmentUnits'])

    def test_rejects_free_inputs_invalid_waste_capacity_fees_and_fake_routes(self):
        changes = [lambda d: d.update(schemaVersion=2),
                   lambda d: d['food'].update(shipmentUnits=0),
                   lambda d: d['food'].update(wasteUnits=100),
                   lambda d: d['food'].update(deliveryCost=0),
                   lambda d: d['food'].update(laborUnits=True),
                   lambda d: d['food'].update(goodId='invented'),
                   lambda d: d['food'].update(goodId='timber'),
                   lambda d: d['food'].update(approachRadius=0),
                   lambda d: d['canalRoutes'][0].update(projectId='imaginary'),
                   lambda d: d['canalRoutes'][0].update(destinationId='london'),
                   lambda d: d['canalRoutes'][0].update(destinationId='yangzhou'),
                   lambda d: d['canalRoutes'][0].update(routeId='ocean_passage'),
                   lambda d: d['canalRoutes'][0].update(dailyCapacity=0),
                   lambda d: d['canalRoutes'][0].update(feeBasisPoints=0),
                   lambda d: d['canalRoutes'][0].update(goodIds=['arms']),
                   lambda d: d['canalRoutes'].append(d['canalRoutes'][0])]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                data = copy.deepcopy(self.data); change(data)
                with self.assertRaises(ValueError): self.compile(self.fixture(tmp, data))
        for kind in ('land', 'sea', 'desert'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                routes = json.loads((PROJECT / self.data['canalRoutes'][0]['routeSource']).read_text())
                next(r for r in routes['tradeRoutes'] if r['id'] == self.data['canalRoutes'][0]['routeId'])['kind'] = kind
                with self.assertRaisesRegex(ValueError, 'waterway'): self.compile(self.fixture(tmp, routes=routes))

    def test_rejects_wrong_entitlement_recipient_and_missing_real_endpoint_facilities(self):
        node = next(n for n in self.world['technologies'] if n['id'] == 'campaign_bakeries')
        node['unlocks'] = []
        with self.assertRaisesRegex(ValueError, 'typed'): self.compile()
        self.setUp()
        self.authored['zhenjiang'][1]['roles'].remove('canal_node')
        with self.assertRaisesRegex(ValueError, 'geography'): self.compile()
        self.setUp()
        self.authored['zhenjiang'][1]['services'].remove('warehouse')
        with self.assertRaisesRegex(ValueError, 'facilities'): self.compile()
        self.setUp()
        self.authored['zhenjiang'][1]['physicalMapId'] = 'pacific'
        with self.assertRaisesRegex(ValueError, 'physical maps'): self.compile()
        self.setUp()
        with tempfile.TemporaryDirectory() as tmp:
            design = json.loads((PROJECT / self.data['designSource']).read_text())
            next(e for e in design['effects'] if e['nodeId'] == 'campaign_bakeries')['recipient'] = 'all_units'
            with self.assertRaisesRegex(ValueError, 'recipient'): self.compile(self.fixture(tmp, design=design))

    def test_whole_roster_food_eligibility_does_not_require_firearms(self):
        sys.path.insert(0, str(PROJECT / 'tooling'))
        from land_army_catalog import build
        profiles = {p['id']: p for p in build()['catalog']['profiles']}
        levy = profiles['african_regional_levy']
        self.assertEqual('land_formation', levy['categoryId'])
        self.assertFalse(levy['firearm'])
        self.assertEqual(1450, levy['firstYear'])


class LogisticsEvidenceTests(unittest.TestCase):
    def test_design_or_missing_failed_stale_execution_cannot_clear_findings(self):
        self.assertEqual(set(), verified_bindings(PROJECT))
        self.assertEqual(set(), verified_bindings(PROJECT, {}, b'', 'a' * 40))
        prefix = 'wurst/ArmyFoodLogisticsTests.wurst:'
        report = {'tests': [{'id': prefix + n, 'status': 'pass'} for n in REQUIRED_TESTS],
                  'productionCoverage': {'tests': {prefix + n: ['logistics_registration', 'logistics_food',
                      'logistics_freight', 'finance_canal', 'finance_advance'] for n in REQUIRED_TESTS}}}
        # Selection logic only; this mocked verifier is never release evidence.
        with patch('integration_evidence.verify_execution_coverage'):
            self.assertEqual(2, len(verified_bindings(PROJECT, report, b'fixture', 'a' * 40)))
            report['tests'][0]['status'] = 'fail'
            self.assertEqual(set(), verified_bindings(PROJECT, report, b'fixture', 'a' * 40))
            report['tests'][0]['status'] = 'pass'
            report.pop('productionCoverage')
            self.assertEqual(set(), verified_bindings(PROJECT, report, b'fixture', 'a' * 40))
        with patch('integration_evidence.verify_execution_coverage', side_effect=ValueError('stale')):
            self.assertEqual(set(), verified_bindings(PROJECT, report, b'fixture', 'a' * 40))

    def test_production_probe_declarations_are_real_and_unique(self):
        from integration_evidence import load_contract, instrument
        for name, probe in load_contract(PROJECT)['probes'].items():
            if name.startswith('logistics_'):
                self.assertIn('print("WCM_PROBE:' + name + '")',
                              instrument((PROJECT / probe['path']).read_text(), {name: probe}))


class SupplyApproachTests(unittest.TestCase):
    def test_materialized_service_approach_is_bounded_and_traversable(self):
        from army_food_logistics import supply_anchor
        grid = dict(minX=0, minY=0, width=3, height=2, rows=['1:0,2:1,3:2,'] * 2)
        self.assertEqual((160, 20), supply_anchor({'world': [160, 20]}, grid, 128))
        self.assertEqual((192, 64), supply_anchor({'world': [64, 64]}, grid, 128))
        self.assertIsNone(supply_anchor({'world': [64, 64]}, grid, 127))
        self.assertIsNone(supply_anchor({'world': [-1000, 64]}, grid, 128))
