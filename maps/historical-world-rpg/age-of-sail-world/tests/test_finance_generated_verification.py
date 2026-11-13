"""Execute the staged finance-output verifier with real v1 catalogue data.

Supporting world/settlement/market inputs are the existing synthetic registration
fixtures. These tests execute Python generation and verification, not Wurst,
full scenario packaging, military save migration, or native game acceptance.
"""
import copy
import json
import unittest

import test_finance_site_registration as fixtures

finance = fixtures.finance


class FinanceGeneratedVerificationTests(unittest.TestCase):
    def setUp(self):
        # Compose the existing fixture without inheriting/rerunning its tests.
        self.f = fixtures.FinanceSiteRegistrationTests(
            'test_each_legacy_exchange_uses_owned_registration_with_customs_disabled')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.generated, self.catalogue, _ = self.f.generate()
        self.market_source = '\n'.join('\t' + row for row in self.f.records) + '\n'
        self.source = 'package FinanceVerificationFixture\n' + self.market_source + self.generated

    def verify(self, source=None, catalogue=None):
        return finance.verify_generated(
            self.f.root, self.f.world, self.f.settlements, self.f.authored,
            self.source if source is None else source,
            self.catalogue if catalogue is None else catalogue)

    def test_authentic_block_matches_scenario_without_mutating_inputs(self):
        before = copy.deepcopy((self.f.world, self.f.settlements, self.f.authored,
                                self.source, self.catalogue))
        self.assertIsNone(self.verify())
        self.assertIsNone(self.verify())
        self.assertEqual(before, (self.f.world, self.f.settlements, self.f.authored,
                                  self.source, self.catalogue))
        self.assertIsNone(self.verify(source=self.source + '\n// Other generated sections follow.\n'))

    def test_changed_finance_lines_fail_with_original_catalogue(self):
        changes = [
            ('ledger.commissionShare = 5000', 'ledger.commissionShare = 5001'),
            ('ledger.remittanceFee = 200', 'ledger.remittanceFee = 0'),
            (', false)', ', true)'),
            ('ledger.registerSite(', 'ledger.disconnectedSite('),
        ]
        for old, new in changes:
            with self.subTest(change=old):
                self.assertIn(old, self.generated)
                changed = self.source.replace(old, new, 1)
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(source=changed)

    def test_missing_or_duplicate_generated_block_is_rejected(self):
        for source in (self.market_source, self.source + self.generated):
            with self.subTest(duplicate=source.count(self.generated)):
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(source=source)

    def test_fabricated_or_incomplete_catalogue_is_rejected(self):
        changes = [
            lambda c: c.update(commissionShareBasisPoints=1),
            lambda c: c['exchangeIds'].append('invented_site'),
            lambda c: c['effects'][0].update(bonusBasisPoints=9000),
            lambda c: c.update(consumers=[{'runtimeConsumer': 'invented'}]),
            lambda c: c.pop('canalWorks'),
        ]
        for change in changes:
            catalogue = copy.deepcopy(self.catalogue)
            change(catalogue)
            with self.subTest(catalogue=catalogue):
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(catalogue=catalogue)

    def test_paired_source_and_catalogue_edit_still_requires_authored_inputs(self):
        catalogue = copy.deepcopy(self.catalogue)
        catalogue['commissionShareBasisPoints'] = 7000
        source = self.source.replace('ledger.commissionShare = 5000',
                                     'ledger.commissionShare = 7000')
        with self.assertRaisesRegex(ValueError, 'differs from scenario'):
            self.verify(source, catalogue)

    def test_changed_scenario_invalidates_previously_generated_output(self):
        self.f.data['remittanceFeeBasisPoints'] = 201
        self.f.path.write_text(json.dumps(self.f.data))
        with self.assertRaisesRegex(ValueError, 'differs from scenario'):
            self.verify()
        generated, catalogue, _ = self.f.generate()
        self.assertIsNone(self.verify(self.market_source + generated, catalogue))

    def test_missing_required_market_registration_is_rejected(self):
        bank = self.f.data['bankNetworks'][0]['settlementIds'][0]
        rows = [row for row in self.market_source.splitlines()
                if f'runtime.registerMarketProfile({json.dumps(bank)},' not in row]
        self.assertLess(len(rows), len(self.market_source.splitlines()))
        with self.assertRaisesRegex(ValueError, 'bank lacks'):
            self.verify('\n'.join(rows) + '\n' + self.generated)

    def test_absent_catalogue_accepts_only_the_neutral_stub(self):
        self.f.path.unlink()
        generated, catalogue, _ = finance.configuration(
            self.f.root, self.f.world, self.f.settlements, self.f.authored, self.f.records)
        self.assertEqual({}, catalogue)
        self.assertIn('\tskip\n', generated)
        self.assertIsNone(self.verify(self.market_source + generated, catalogue))
        with self.assertRaisesRegex(ValueError, 'differs from scenario'):
            self.verify()
        with self.assertRaisesRegex(ValueError, 'differs from scenario'):
            self.verify(self.market_source + generated * 2, catalogue)

    def test_verification_cannot_enable_the_v2_catalogue(self):
        self.f.data['schemaVersion'] = 2
        self.f.path.write_text(json.dumps(self.f.data))
        with self.assertRaisesRegex(ValueError, 'invalid schema'):
            self.verify()

    def test_matching_output_is_not_release_execution_evidence(self):
        self.assertEqual(set(), finance.verified_bindings(self.f.root))
        self.verify()
        self.assertEqual(set(), finance.verified_bindings(self.f.root))


if __name__ == '__main__':
    unittest.main()
