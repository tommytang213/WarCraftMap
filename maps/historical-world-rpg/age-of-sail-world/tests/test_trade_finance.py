"""Scenario compiler guards; production outcomes execute in TradeFinanceTests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from trade_finance import configuration


class TradeFinanceCompilationTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.data = json.loads((PROJECT / 'scenario/progression/trade-finance.json').read_text())
        self.authored = {}
        for path in (PROJECT / 'scenario/settlements').glob('*-1450.json'):
            for row in json.loads(path.read_text())['settlements']:
                self.authored[row['id']] = ('region', row)
        self.settlements = [{'id': sid} for sid in self.authored]
        self.trade = [f'runtime.registerMarketProfile("{sid}","timber",90,1000)' for sid in self.authored]

    def compile(self, project=PROJECT, **kwargs):
        return configuration(project, kwargs.get('world', self.world), self.settlements,
                             kwargs.get('authored', self.authored), self.trade)

    def test_compiles_exact_bindings_real_facilities_paid_canal_geography_and_eras(self):
        source, catalog, paths = self.compile()
        self.assertEqual({('auction_markets', 500), ('bill_of_exchange_networks', 600),
                          ('brokerage_houses', 700), ('canal_tolls_finance', 600)},
                         {(e['nodeId'], e['bonusBasisPoints']) for e in catalog['effects']})
        self.assertIn('"river_transport_bureaus", "timber", 638810, 20, 1000, 100, 2, 90, 200, 10', source)
        self.assertIn('new ExchangeSite("london", "greater_london", "european_correspondents")', source)
        self.assertNotIn('unlock(', source)
        self.assertEqual(3, len(paths))
        self.assertEqual(source, self.compile()[0])

    def test_missing_contract_preserves_framework_neutrality(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, catalog, paths = self.compile(Path(tmp))
        self.assertIn('\tskip', source)
        self.assertEqual(({}, []), (catalog, paths))

    def test_rejects_fake_banks_missing_materials_duplicate_projects_and_free_bills(self):
        changes = [lambda d: d.update(commissionShareBasisPoints=True),
                   lambda d: d.update(remittanceFeeBasisPoints=0),
                   lambda d: d.update(bankPrerequisite='invented'),
                   lambda d: d['bankNetworks'][0]['settlementIds'].append('yangzhou'),
                   lambda d: d['bankNetworks'][0]['settlementIds'].append('london'),
                   lambda d: d['canalWorks'][0].update(settlementId='london'),
                   lambda d: d['canalWorks'][0].update(good='fake_materials'),
                   lambda d: d['canalWorks'][0].update(financingCost=0),
                   lambda d: d['canalWorks'][0].update(principalCost=True),
                   lambda d: d['canalWorks'][0].update(laborCostPerDay=0),
                   lambda d: d['canalWorks'][0].update(laborUnits=0),
                   lambda d: d['canalWorks'][0].update(firstDate='1450-01-01'),
                   lambda d: d['canalWorks'].append(d['canalWorks'][0])]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'scenario/progression').mkdir(parents=True)
                (root / self.data['designSource']).write_bytes((PROJECT / self.data['designSource']).read_bytes())
                data = copy.deepcopy(self.data); change(data)
                (root / 'scenario/progression/trade-finance.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError): self.compile(root)

    def test_rejects_removed_typed_unlock_and_missing_banking_infrastructure(self):
        world = copy.deepcopy(self.world)
        next(n for n in world['technologies'] if n['id'] == 'auction_markets')['unlocks'] = []
        with self.assertRaisesRegex(ValueError, 'typed'): self.compile(world=world)
        authored = copy.deepcopy(self.authored)
        authored['london'][1]['services'].remove('banking')
        with self.assertRaisesRegex(ValueError, 'bank'): self.compile(authored=authored)
        authored = copy.deepcopy(self.authored)
        authored['yangzhou'][1]['roles'].remove('canal_node')
        with self.assertRaisesRegex(ValueError, 'canal geography'): self.compile(authored=authored)


class FinanceReleaseEvidenceTests(unittest.TestCase):
    def test_source_design_or_incomplete_failed_stale_evidence_cannot_bind(self):
        from trade_finance import verified_bindings
        self.assertEqual(set(), verified_bindings(PROJECT))
        self.assertEqual(set(), verified_bindings(PROJECT, {}, b'', 'a' * 40))

    def test_only_verified_current_execution_with_every_production_case_binds(self):
        from trade_finance import verified_bindings, REQUIRED_TESTS
        from unittest.mock import patch
        report = {'tests': [{'id': 'wurst/TradeFinanceTests.wurst:' + name, 'status': 'pass'}
                            for name in REQUIRED_TESTS]}
        report['productionCoverage'] = {'tests': {
            'wurst/TradeFinanceTests.wurst:' + name: ['finance_registration', 'finance_quote', 'finance_remit', 'finance_canal', 'finance_advance']
            for name in REQUIRED_TESTS}}
        # This isolates test coverage selection; it is not release execution evidence.
        with patch('integration_evidence.verify_execution_coverage') as verify:
            bound = verified_bindings(PROJECT, report, b'fixture', 'a' * 40)
            self.assertEqual(4, len(bound))
            verify.assert_called_once_with(report, b'fixture', PROJECT, 'a' * 40)
            covered = report.pop('productionCoverage')
            self.assertEqual(set(), verified_bindings(PROJECT, report, b'fixture', 'a' * 40))
            report['productionCoverage'] = covered
            report['tests'].pop()
            self.assertEqual(set(), verified_bindings(PROJECT, report, b'fixture', 'a' * 40))
        with patch('integration_evidence.verify_execution_coverage', side_effect=ValueError('stale')):
            self.assertEqual(set(), verified_bindings(PROJECT, report, b'fixture', 'a' * 40))

    def test_production_probe_declarations_are_real_and_unique(self):
        from integration_evidence import load_contract, instrument
        contract = load_contract(PROJECT)
        for name, probe in contract['probes'].items():
            if name.startswith('finance_'):
                self.assertIn('print("WCM_PROBE:' + name + '")',
                              instrument((PROJECT / probe['path']).read_text(), {name: probe}))
