"""Compiler/evidence guards. Real operations execute in BankingOperationsTests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from central_banking import configuration, verified_bindings, REQUIRED_TESTS


class CentralBankingTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.data = json.loads((PROJECT / 'scenario/progression/central-banking.json').read_text())
        self.authored = {}
        for f in (PROJECT / 'scenario/settlements').glob('*-1450.json'):
            self.authored.update({r['id']: ('region', r) for r in json.loads(f.read_text())['settlements']})
        self.settlements = [{'id': sid} for sid in self.authored]
        self.trade = [f'runtime.registerMarketProfile("{sid}","timber",90,1000)' for sid in self.authored]

    def compile(self, project=PROJECT, **kwargs):
        return configuration(project, kwargs.get('world', self.world), self.settlements,
                             kwargs.get('authored', self.authored), self.trade)

    def test_real_bank_contracts_and_separate_typed_identities(self):
        source, data, paths = self.compile()
        self.assertEqual({('central_banking', 'modifier', 600), ('central_bank_institution', 'policy', 500)},
                         {(e['nodeId'], e['unlock']['kind'], e['bonusBasisPoints']) for e in data['effects']})
        self.assertIn('new BankingSite("london",', source)
        self.assertIn('ledger.transitionDays = 90', source)
        self.assertIn('ledger.enactmentBasisPoints = 100', source)
        self.assertIn('ledger.upkeepBasisPoints = 50', source)
        self.assertEqual(4, len(data['sites']))
        self.assertEqual(5, len(paths))
        self.assertEqual(source, self.compile()[0])
        self.assertNotIn('unlock(', source)
        self.assertNotIn('remittance', source)
        self.assertNotIn('TradeFinance', source)
        nodes = {n['id']: n for n in self.world['technologies'] + self.world['institutions']}
        self.assertEqual(['auction_markets', 'standing_army_system'], nodes['central_banking']['prerequisiteIds'])
        self.assertEqual(['merchant_correspondence'], nodes['central_bank_institution']['prerequisiteIds'])
        self.assertEqual(1695, nodes['central_banking']['timeCost']['preferredYear'])
        self.assertEqual(292, nodes['central_banking']['timeCost']['baseCost'])
        self.assertEqual(283, nodes['central_bank_institution']['timeCost']['baseCost'])
        catalog = json.loads((PROJECT / 'scenario/progression/catalog.json').read_text())
        institution = next(n for n in catalog['institutions'] if n['id'] == 'central_bank_institution')
        self.assertEqual(19, institution['adoptionRequirements']['minimumUrbanization'])

    def test_missing_contract_preserves_framework_neutrality(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, data, paths = self.compile(Path(tmp))
        self.assertIn('\tskip', source)
        self.assertEqual(({}, []), (data, paths))

    def test_fake_banks_removed_unlocks_free_bills_and_duplicate_sites_reject(self):
        for key, value in [('transitionDays', 0), ('countingBasisPoints', True),
                           ('reconciliationBasisPoints', 0), ('upkeepBasisPoints', -1),
                           ('enactmentBasisPoints', 10001)]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'scenario/progression').mkdir(parents=True)
                for k in ('designSource', 'taxSource'):
                    (root / self.data[k]).write_bytes((PROJECT / self.data[k]).read_bytes())
                data = copy.deepcopy(self.data)
                data['rules'][key] = value
                (root / 'scenario/progression/central-banking.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError): self.compile(root)
        authored = copy.deepcopy(self.authored)
        authored['london'][1]['services'].remove('banking')
        with self.assertRaisesRegex(ValueError, 'infrastructure'): self.compile(authored=authored)
        world = copy.deepcopy(self.world)
        next(n for n in world['institutions'] if n['id'] == 'central_bank_institution')['unlocks'] = []
        with self.assertRaisesRegex(ValueError, 'typed'): self.compile(world=world)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'scenario/progression').mkdir(parents=True)
            for k in ('designSource', 'taxSource'):
                (root / self.data[k]).write_bytes((PROJECT / self.data[k]).read_bytes())
            data = copy.deepcopy(self.data)
            data['siteIds'].append('london')
            (root / 'scenario/progression/central-banking.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'duplicate'): self.compile(root)

    def test_evidence_fails_closed_without_complete_current_production_execution(self):
        self.assertEqual(set(), verified_bindings(PROJECT))
        self.assertEqual(set(), verified_bindings(PROJECT, {}, b'', 'a' * 40))
        prefix = 'wurst/BankingOperationsTests.wurst:'
        report = {'tests': [{'id': prefix + n, 'status': 'pass'} for n in sorted(REQUIRED_TESTS)],
                  'productionCoverage': {'tests': {prefix + n: ['banking_registration', 'banking_policy', 'banking_quote', 'banking_commit', 'banking_advance'] for n in REQUIRED_TESTS}}}
        with patch('integration_evidence.verify_execution_coverage'):
            self.assertEqual({('modifier', 'progression_central_banking'), ('policy', 'progression_central_bank_institution')},
                             verified_bindings(PROJECT, report, b'fixture', 'a' * 40))
            missing = copy.deepcopy(report)
            missing['tests'].pop()
            self.assertEqual(set(), verified_bindings(PROJECT, missing, b'fixture', 'a' * 40))
            report['productionCoverage'] = {}
            self.assertEqual(set(), verified_bindings(PROJECT, report, b'fixture', 'a' * 40))

    def test_probes_target_real_unique_production_entries(self):
        from integration_evidence import load_contract, instrument
        for name, spec in load_contract(PROJECT)['probes'].items():
            if name.startswith('banking_'):
                self.assertIn('print("WCM_PROBE:' + name + '")',
                              instrument((PROJECT / spec['path']).read_text(), {name: spec}))
