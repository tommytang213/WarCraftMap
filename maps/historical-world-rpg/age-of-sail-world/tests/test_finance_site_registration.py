"""Execute legacy catalogue generation through the owned-site registration path.

Uses the scenario's real v1 finance JSON with synthetic supporting geography,
research and market fixtures. This is Python generator execution, not Wurst,
whole-scenario compilation, military save restoration or native acceptance.
"""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT.parent / '_shared/tooling/trade_finance.py'
spec = importlib.util.spec_from_file_location('finance_site_registration_generator', SOURCE)
finance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finance)


class FinanceSiteRegistrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'scenario/progression/trade-finance.json'
        self.path.parent.mkdir(parents=True)
        self.data = json.loads((PROJECT / 'scenario/progression/trade-finance.json').read_text())
        self.world = {'technologies': [], 'institutions': []}
        self.effects = []
        for index, metric in enumerate(sorted(finance.METRICS)):
            unlock = {'kind': 'modifier', 'contentId': 'fixture_effect_' + str(index)}
            node = {'id': 'fixture_node_' + str(index), 'unlocks': [unlock],
                    'timeCost': {'preferredYear': 1450}}
            self.world['technologies'].append(node)
            self.effects.append({'nodeId': node['id'], 'unlock': unlock,
                                 'metric': metric, 'bonusBasisPoints': 500})
        prerequisites = {self.data['bankPrerequisite']}
        prerequisites.update(work['prerequisite'] for work in self.data['canalWorks'])
        for node in sorted(prerequisites):
            self.world['technologies'].append({'id': node, 'unlocks': [],
                                              'timeCost': {'preferredYear': 1450}})
        self.authored = {}
        for network in self.data['bankNetworks']:
            for sid in network['settlementIds']:
                self.add_site(sid, ['trade_center'], ['market', 'warehouse', 'banking'])
        for work in self.data['canalWorks']:
            self.add_site(work['settlementId'], ['trade_center', 'canal_node'])
        self.add_site('fixture_capital', ['capital'])
        self.expected_ids = list(self.authored)
        self.add_site('fixture_port_only', ['port'])
        self.add_site('fixture_major_port_only', ['major_port'])
        self.add_site('fixture_no_warehouse', ['trade_center'], ['market'])
        self.add_site('fixture_no_profile', ['trade_center'])
        self.add_site('fixture_unplaced', ['trade_center'])
        self.settlements = [{'id': sid} for sid in self.authored if sid != 'fixture_unplaced']
        goods = {work['good'] for work in self.data['canalWorks']}
        self.records = [f'runtime.registerMarketProfile({json.dumps(sid)},{json.dumps(good)},90,1000)'
                        for sid in self.authored if sid != 'fixture_no_profile'
                        for good in sorted(goods)]
        design = self.root / self.data['designSource']
        design.parent.mkdir(parents=True, exist_ok=True)
        design.write_text(json.dumps({'effects': self.effects}))

    def add_site(self, sid, roles, services=None):
        self.authored[sid] = ('fixture', {'provinceId': 'fixture_' + sid,
                                        'roles': roles,
                                        'services': services or ['market', 'warehouse']})

    def generate(self):
        self.path.write_text(json.dumps(self.data))
        return finance.configuration(self.root, self.world, self.settlements,
                                     self.authored, self.records)

    def calls(self, source):
        return [line for line in source.splitlines() if 'ledger.registerSite(' in line]

    def test_each_legacy_exchange_uses_owned_registration_with_customs_disabled(self):
        source, catalogue, _ = self.generate()
        banks = {sid: network['id'] for network in self.data['bankNetworks']
                 for sid in network['settlementIds']}
        expected = [f'\tledger.registerSite({json.dumps(sid)}, '
                    f'{json.dumps(self.authored[sid][1]["provinceId"])}, '
                    f'{json.dumps(banks.get(sid, ""))}, false)' for sid in self.expected_ids]
        self.assertEqual(expected, self.calls(source))
        self.assertEqual(self.expected_ids, catalogue['exchangeIds'])
        self.assertNotIn('new ExchangeSite(', source)
        self.assertNotIn('ledger.siteCount', source)

    def test_old_facility_geography_placement_and_market_filters_are_preserved(self):
        source, catalogue, _ = self.generate()
        for sid in ('fixture_port_only', 'fixture_major_port_only', 'fixture_no_warehouse',
                    'fixture_no_profile', 'fixture_unplaced'):
            with self.subTest(site=sid):
                self.assertNotIn(sid, catalogue['exchangeIds'])
                self.assertNotIn(json.dumps(sid), source)
        self.assertIn('fixture_capital', catalogue['exchangeIds'])

    def test_output_does_not_enable_customs_catalogue_effects_or_save_formats(self):
        source, catalogue, _ = self.generate()
        self.assertEqual(1, catalogue['schemaVersion'])
        self.assertNotIn('customsHouse', catalogue)
        self.assertNotIn('consumers', catalogue)
        self.assertNotIn('ledger.customs', source)
        self.assertNotIn('|J,', source)
        self.assertNotIn('|H,', source)
        self.assertNotIn('|O,', source)
        self.assertEqual(4, source.count('effects.register(new FinanceEffect('))
        self.assertTrue(all(call.endswith(', false)') for call in self.calls(source)))

    def test_determinism_no_input_mutation_and_existing_contracts(self):
        before = copy.deepcopy((self.data, self.world, self.settlements, self.authored, self.records))
        source, catalogue, inputs = self.generate()
        self.assertEqual((source, catalogue, inputs), self.generate())
        self.assertEqual(before, (self.data, self.world, self.settlements, self.authored, self.records))
        self.assertEqual(self.effects, catalogue['effects'])
        self.assertEqual(self.data['canalWorks'], catalogue['canalWorks'])
        self.assertEqual(len(self.data['canalWorks']), source.count('ledger.register(new CanalWork('))
        for name, field in (('commissionShareBasisPoints', 'commissionShare'),
                            ('remittanceFeeBasisPoints', 'remittanceFee')):
            self.assertIn(f'\tledger.{field} = {self.data[name]}', source)
        self.assertEqual([self.path, self.root / self.data['designSource'], SOURCE], inputs)

    def test_registration_keeps_json_escaping(self):
        province = 'fixture "quoted" \\ province'
        self.authored['fixture_capital'][1]['provinceId'] = province
        source, _, _ = self.generate()
        self.assertIn(f'ledger.registerSite("fixture_capital", {json.dumps(province)}, "", false)', source)

    def test_exact_capacity_and_overflow_rejection(self):
        for index in range(1024 - len(self.expected_ids)):
            sid = 'fixture_extra_' + str(index)
            self.add_site(sid, ['trade_center'])
            self.settlements.append({'id': sid})
            self.records.append(f'runtime.registerMarketProfile("{sid}","timber",90,1000)')
        source, catalogue, _ = self.generate()
        self.assertEqual(1024, len(self.calls(source)))
        self.assertEqual(1024, len(catalogue['exchangeIds']))
        self.add_site('fixture_overflow', ['trade_center'])
        self.settlements.append({'id': 'fixture_overflow'})
        self.records.append('runtime.registerMarketProfile("fixture_overflow","timber",90,1000)')
        with self.assertRaisesRegex(ValueError, 'capacity exceeded'):
            self.generate()

    def test_v2_remains_rejected_and_absent_catalogue_remains_inert(self):
        self.data['schemaVersion'] = 2
        with self.assertRaisesRegex(ValueError, 'invalid schema'):
            self.generate()
        self.path.unlink()
        source, catalogue, inputs = finance.configuration(
            self.root, self.world, self.settlements, self.authored, self.records)
        self.assertIn('\tskip\n', source)
        self.assertEqual(({}, []), (catalogue, inputs))

    def test_bank_validation_and_release_evidence_gate_are_unchanged(self):
        sid = self.data['bankNetworks'][0]['settlementIds'][0]
        self.authored[sid][1]['services'].remove('banking')
        with self.assertRaisesRegex(ValueError, 'bank lacks'):
            self.generate()
        for kwargs in ({}, {'execution': {}}, {'execution': {}, 'execution_log': b'fixture'},
                       {'revision': 'a' * 40}):
            self.assertEqual(set(), finance.verified_bindings(self.root, **kwargs))


if __name__ == '__main__':
    unittest.main()
