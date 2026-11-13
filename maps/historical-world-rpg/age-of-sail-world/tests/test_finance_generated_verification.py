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

    def test_catalogue_numeric_type_substitutions_are_rejected(self):
        # JSON numeric identity matters: Python considers True == 1 and 1.0 == 1.
        self.assertIsNone(self.verify())
        for value in (True, 1.0, False, 0.0):
            with self.subTest(value=value, kind=type(value).__name__):
                changed = copy.deepcopy(self.catalogue)
                changed['schemaVersion'] = value
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(catalogue=changed)
        for value in (True, 5000.0):
            with self.subTest(value=value, kind=type(value).__name__):
                changed = copy.deepcopy(self.catalogue)
                changed['commissionShareBasisPoints'] = value
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(catalogue=changed)

    def test_noninteger_authored_schema_never_generates_finance(self):
        for value in (True, 1.0, '1'):
            with self.subTest(value=value, kind=type(value).__name__):
                self.f.data['schemaVersion'] = value
                self.f.path.write_text(json.dumps(self.f.data))
                with self.assertRaisesRegex(ValueError, 'invalid schema'):
                    self.f.generate()

    def test_appended_finance_overrides_do_not_hide_behind_expected_prefix(self):
        for separator in ('', '\n', '// Boundary comment.\n',
                          '/* Boundary\ncomment. */\n'):
            with self.subTest(separator=separator):
                source = self.source + separator + '\tledger.commissionShare = 0\n'
                self.assertEqual(1, source.count(self.generated))
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(source=source)

    def test_packager_logistics_continuation_is_allowed_once(self):
        # package_wurst_map.generate appends this call to finance_wurst, then
        # appends the separate logistics function. No Wurst execution is claimed.
        for separator in ('', '\n', '// Composer boundary.\n', '/* boundary */\n'):
            with self.subTest(separator=separator):
                source = (self.source + separator
                          + '\tconfigureGeneratedLogistics(ledger, effects)\n'
                          + '\npublic function configureGeneratedLogistics(FinanceLedger ledger, FinanceResearchEffects effects)\n'
                          + '\tskip\n')
                self.assertIsNone(self.verify(source=source))

    def test_logistics_continuation_cannot_hide_extra_finance_statements(self):
        call = '\tconfigureGeneratedLogistics(ledger, effects)\n'
        for tail in (call * 2, call + '\tledger.remittanceFee = 0\n',
                     '\tledger.remittanceFee = 0\n' + call,
                     '\tconfigureGeneratedLogistics(ledger, inventedEffects)\n',
                     call + '// Still the same function.\n\tledger.commissionShare = 0\n'):
            with self.subTest(tail=tail):
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(source=self.source + tail)

    def test_commented_out_finance_recipe_cannot_satisfy_the_gate(self):
        for terminator in ('*/\n', ''):
            with self.subTest(terminated=bool(terminator)):
                source = self.market_source + '/* disabled finance\n' + self.generated + terminator
                self.assertEqual(1, source.count(self.generated))
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(source=source)

    def test_different_duplicate_finance_definition_is_rejected(self):
        for declaration in ('public function configureGeneratedFinance',
                            'function configureGeneratedFinance'):
            with self.subTest(declaration=declaration):
                source = (self.source + '\n' + declaration
                          + '(FinanceLedger ledger, FinanceResearchEffects effects)\n\tskip\n')
                self.assertEqual(1, source.count(self.generated))
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(source=source)

    def test_comment_like_literals_do_not_mask_the_finance_declaration(self):
        for literal in ('"/* not a comment */ // still a string"',
                        '"escaped \\" quote and /* marker"', "'/*xx'", "'//xx'"):
            with self.subTest(literal=literal):
                # Canonical generated code uses quoted IDs and can contain
                # comment-like characters without starting a source comment.
                kind = 'int' if literal.startswith("'") else 'string'
                prefix = kind + ' unrelated = ' + literal + '\n'
                self.assertIsNone(self.verify(source=prefix + self.source))
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(source=prefix + self.source + '\tledger.remittanceFee = 0\n')

    def test_next_top_level_function_is_not_part_of_finance_body(self):
        tail = ('\n/* next generated section */\n'
                'public function unrelated(FinanceLedger ledger)\n'
                '\tledger.remittanceFee = 0\n')
        self.assertIsNone(self.verify(source=self.source + tail))

    def test_commented_bank_registration_is_not_executable_finance_authority(self):
        sid = self.f.data['bankNetworks'][0]['settlementIds'][0]
        line = next(line for line in self.market_source.splitlines()
                    if f'runtime.registerMarketProfile({json.dumps(sid)},' in line)
        for commented in ('//' + line, '/*' + line + '*/',
                          '/* blocked market\n' + line + '\n*/'):
            with self.subTest(comment=commented[:20]):
                tampered = self.source.replace(line, commented, 1)
                self.assertIn('runtime.registerMarketProfile(', tampered)
                with self.assertRaisesRegex(ValueError, 'bank lacks'):
                    self.verify(source=tampered)

    def test_commented_canal_material_registration_is_not_accepted(self):
        work = self.f.data['canalWorks'][0]
        line = next(line for line in self.market_source.splitlines()
                    if f'runtime.registerMarketProfile({json.dumps(work["settlementId"])},'
                       f'{json.dumps(work["good"])},' in line)
        with self.assertRaisesRegex(ValueError, 'canal geography'):
            self.verify(self.source.replace(line, '/*' + line + '*/', 1))

    def test_quoted_example_cannot_replace_live_market_registration(self):
        sid = self.f.data['bankNetworks'][0]['settlementIds'][0]
        line = next(line for line in self.market_source.splitlines()
                    if f'runtime.registerMarketProfile({json.dumps(sid)},' in line)
        quoted = 'string documentation = ' + json.dumps(line.strip())
        with self.assertRaisesRegex(ValueError, 'bank lacks'):
            self.verify(self.source.replace(line, quoted, 1))

    def test_comment_markers_in_quoted_metadata_do_not_hide_real_markets(self):
        for literal in ('"https://example.com/*literal*/"',
                        '"not // a real comment"', "'/*'", "'//'", 
                        '"escaped \\" // still text"'):
            with self.subTest(literal=literal):
                source = 'string note = ' + literal + '\n' + self.source
                self.assertIsNone(self.verify(source=source))
                # Preserve the original complete generated finance function.
                self.assertEqual(self.generated, finance.configuration(
                    self.f.root, self.f.world, self.f.settlements,
                    self.f.authored, self.f.records)[0])

    def test_active_market_after_block_comment_still_qualifies(self):
        lines = self.market_source.splitlines()
        first = lines[0]
        amended = ('/* documentation\n'
                   'runtime.registerMarketProfile("london","timber",90,1000)\n'
                   '*/\n' + first + '\n' + '\n'.join(lines[1:]) + '\n')
        # The positive live call is present outside the comment; no duplicate
        # phantom registration should be required by the finance generator.
        self.assertIsNone(self.verify(source=amended + self.generated))

    def test_indented_duplicate_finance_definition_after_unrelated_function_is_rejected(self):
        # Wurst permits leading whitespace. The audit must not treat a second
        # indented declaration as ordinary text after another function.
        for prefix in ('\tpublic ', '    ', '\t'):
            with self.subTest(prefix=repr(prefix)):
                declaration = (prefix + 'function configureGeneratedFinance'
                               + '(FinanceLedger ledger, FinanceResearchEffects effects)')
                source = (self.source + '\npublic function unrelated()\n\tskip\n'
                          + declaration + '\n\tskip\n')
                with self.assertRaisesRegex(ValueError, 'differs from scenario'):
                    self.verify(source=source)

    def test_matching_output_is_not_release_execution_evidence(self):
        self.assertEqual(set(), finance.verified_bindings(self.f.root))
        self.verify()
        self.assertEqual(set(), finance.verified_bindings(self.f.root))


if __name__ == '__main__':
    unittest.main()
