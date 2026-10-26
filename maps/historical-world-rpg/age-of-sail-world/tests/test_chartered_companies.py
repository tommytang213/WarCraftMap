"""Compilation and fail-closed evidence guards; mutations run in real Wurst."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
from central_banking import configuration
from naval_services_catalog import build
from chartered_companies import verified_bindings, REQUIRED_TESTS


class CharteredCompaniesTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.authored = {s['id']: ('region', s) for p in (PROJECT / 'scenario/settlements').glob('*-1450.json')
                         for s in json.loads(p.read_text())['settlements']}
        self.settlements = [{'id': sid} for sid in self.authored]
        self.trade = [f'runtime.registerMarketProfile("{sid}","timber",90,1000)' for sid in self.authored]

    def compile(self, root=PROJECT, **changes):
        return configuration(root, changes.get('world', self.world), self.settlements,
                             changes.get('authored', self.authored), self.trade,
                             policy='commercial-courts', metrics={'commercial_transaction_fee_reduction': 'policy'},
                             function='configureGeneratedCourts')

    def test_courts_have_exact_optional_paid_local_contract(self):
        source, data, paths = self.compile()
        self.assertEqual(source, self.compile()[0])
        self.assertEqual(4, len(data['sites']))
        self.assertIn('"policy", "commercial_courts", "commercial_transaction_fee_reduction", 500', source)
        self.assertIn('ledger.enactmentBasisPoints = 100', source)
        self.assertIn('ledger.upkeepBasisPoints = 50', source)
        self.assertIn('ledger.transitionDays = 90', source)
        self.assertEqual([3341, 3341, 3341, 2673], [s['annualTax'] for s in data['sites']])
        self.assertNotIn('unlock(', source)
        self.assertNotIn('TradeFinance', source)

    def test_indiaman_uses_resolved_roster_and_its_own_unit_identity(self):
        data, source = build()
        row, = data['recruitmentBlueprints']
        self.assertEqual('armed_indiaman', row['id'])
        self.assertEqual((850, 42, 55), (row['cost'], row['upkeep'], row['supply']))
        self.assertIn('"unit", "armed_indiaman", "merchant_unlock_recruitment", 0', source)
        self.assertIn('|joint_stock_enterprise|galleon_design|public_credit|', source)
        self.assertIn('850, 42, 55, 160, 500', source)
        self.assertIn('recruitment.boardRequired = false', source)
        self.assertEqual('ship_of_the_line_generic', data['blueprint'])
        node = next(n for n in self.world['technologies'] if n['id'] == 'chartered_companies')
        self.assertEqual(['joint_stock_enterprise', 'galleon_design'], node['prerequisiteIds'])
        self.assertEqual((1600, 205), (node['timeCost']['preferredYear'], node['timeCost']['baseCost']))

    def test_missing_policy_unlock_or_infrastructure_rejects(self):
        bad = copy.deepcopy(self.world)
        next(n for n in bad['technologies'] if n['id'] == 'chartered_companies')['unlocks'] = []
        with self.assertRaises(ValueError):
            self.compile(world=bad)
        for service in ('banking', 'market', 'warehouse'):
            bad = copy.deepcopy(self.authored)
            bad['london'][1]['services'].remove(service)
            with self.assertRaises(ValueError):
                self.compile(authored=bad)

    def test_wrong_naval_identity_duplicate_and_missing_recruitment_fail_closed(self):
        for change in (lambda d: d['blueprints'][0].update(contentId='ship_of_the_line'),
                       lambda d: d['blueprints'].append(d['blueprints'][0]),
                       lambda d: d.update(blueprints=[])):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name in ('naval', 'world', 'progression', 'settlements'):
                    shutil.copytree(PROJECT / 'scenario' / name, root / 'scenario' / name)
                path = root / 'scenario/naval/recruitment.json'
                data = json.loads(path.read_text()); change(data); path.write_text(json.dumps(data))
                with self.assertRaises((KeyError, ValueError)):
                    build(root)

    def test_focused_or_missing_evidence_never_closes_blockers(self):
        self.assertEqual(set(), verified_bindings(PROJECT))
        prefix = 'wurst/CharteredCompaniesTests.wurst:'
        execution = {'tests': [{'id': prefix + name, 'status': 'pass'} for name in REQUIRED_TESTS]}
        comparative = prefix + 'charteredRegisteredResearchCourtsAndPaidIndiamanRemainIndependent'
        coverage = {system: [comparative] for system in ('commercial_courts', 'merchant_construction')}
        with patch('integration_evidence.verify_execution_coverage', return_value=coverage):
            self.assertEqual({('policy', 'commercial_courts'), ('unit', 'armed_indiaman')},
                             verified_bindings(PROJECT, execution, b'current', 'a' * 40))
            for system in coverage:
                missing = dict(coverage); missing[system] = []
                with patch('integration_evidence.verify_execution_coverage', return_value=missing):
                    self.assertEqual(set(), verified_bindings(PROJECT, execution, b'current', 'a' * 40))
            execution['tests'].pop()
            self.assertEqual(set(), verified_bindings(PROJECT, execution, b'current', 'a' * 40))

    def test_shared_actions_do_not_name_scenario_identities(self):
        source = '\n'.join((PROJECT.parent / '_shared/wurst' / name).read_text()
                           for name in ('CommercialCourts.wurst', 'NavalServices.wurst', 'NavalCampaignRuntime.wurst'))
        for name in ('chartered_companies', 'armed_indiaman', '"commercial_courts"', '"london"', '"england"'):
            self.assertNotIn(name, source)
