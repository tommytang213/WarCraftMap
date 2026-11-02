"""Current-protocol negative controls; synthetic transcripts are not release evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
import settled_trade_services as services
import integration_evidence as evidence
import release_blocker_audit as audit
import test_auction_binding_evidence as auction_tests


class SettledTradeEvidenceTests(unittest.TestCase):
    setUpClass = classmethod(auction_tests.AuctionBindingEvidenceTests.setUpClass.__func__)
    test_missing_failed_stale_tampered_focused_or_disconnected_evidence_rejects = auction_tests.AuctionBindingEvidenceTests.test_missing_failed_stale_tampered_focused_or_disconnected_evidence_rejects
    def transcript(self, omit_probe=None, fail_test=None, omit_test=None):
        # Reuse the full protocol fixture, adding only the observed probes for
        # these separate comparisons. This never supplies production evidence.
        original = self.expected
        # Parent emits the same discovery and pinned source identity.
        report, log = auction_tests.AuctionBindingEvidenceTests.transcript(self, fail_test=fail_test, omit_test=omit_test)
        text = log.decode()
        for identity, (case, probes) in services.CASES.items():
            row = next(r for r in original if r['id'] == services.PREFIX + case)
            marker = f'Running /synthetic/wurst/SettledTradeServicesTests.wurst:{row["line"]} - {case}..\n'
            observed = probes - ({omit_probe} if omit_probe else set())
            text = text.replace(marker, marker + ''.join('WCM_PROBE:' + p + '\n' for p in sorted(observed)))
        log = text.encode()
        import wurst_execution as execution
        rows, errors = execution.parse_results(text, self.expected)
        report.update(tests=rows, logSha256=evidence.digest(log), errors=errors,
                      status='fail' if errors else 'pass')
        report['productionCoverage']['tests'] = evidence.observed_probes(text, rows, self.contract)
        return report, log

    def bindings(self, report=None, log=None):
        return services.verified_bindings(PROJECT, report, log, self.revision)

    # Replace the parent's domain-specific assertions; retain its full negative
    # protocol test for stale/tampered/focused/disconnected evidence.
    def test_current_protocol_requires_each_sources_own_buy_sell_comparison(self):
        report, log = self.transcript()
        self.assertEqual({services.COURT, services.STATISTICS}, self.bindings(report, log))
        for identity, (case, required) in services.CASES.items():
            for probe in required:
                with self.subTest(identity=identity, probe=probe):
                    r, transcript = self.transcript(omit_probe=probe)
                    self.assertNotIn(identity, self.bindings(r, transcript))
            r, transcript = self.transcript(omit_test=case)
            self.assertNotIn(identity, self.bindings(r, transcript))
        before = {r['id'] for r in audit._audit_research_bindings()}
        after = {r['id'] for r in audit._audit_research_bindings(execution=report, execution_log=log, revision=self.revision)}
        expected = {'RESEARCH-UNBOUND-COMMERCIAL-COURTS-INSTITUTION-POLICY-PROGRESSION-COMMERCIAL-COURTS-INSTITUTION',
                    'RESEARCH-UNBOUND-COMMERCIAL-STATISTICS-MODIFIER-PROGRESSION-COMMERCIAL-STATISTICS'}
        self.assertTrue(expected <= before - after)

    def test_common_lifecycle_cases_remain_required(self):
        for case in services.COMMON:
            for kwargs in ({'fail_test': case}, {'omit_test': case}):
                with self.subTest(case=case, kwargs=kwargs):
                    r, log = self.transcript(**kwargs)
                    self.assertEqual(set(), self.bindings(r, log))

    def test_each_comparison_closes_only_its_own_finding(self):
        for identity, (case, _) in services.CASES.items():
            report, log = self.transcript(omit_test=case)
            self.assertNotIn(identity, self.bindings(report, log))
        report, log = self.transcript()
        # Sibling finance and corporate courts alone cannot close these sources.
        report['tests'] = [r for r in report['tests'] if not r['id'].startswith(services.PREFIX)]
        self.assertEqual(set(), self.bindings(report, log))


class SettledTradeMetadataTests(unittest.TestCase):
    def test_wrong_identity_rate_kind_or_metric_cannot_close_either_source(self):
        self.assertEqual({services.COURT, services.STATISTICS}, services.exact_contracts(PROJECT))
        original = Path.read_text
        for filename, identity in (('institution-courts-effects.json', services.COURT),
                                   ('gameplay-effect-design.json', services.STATISTICS)):
            for change in ('rate', 'kind', 'identity', 'metric', 'duplicate'):
                def changed(path, *args, **kwargs):
                    text = original(path, *args, **kwargs)
                    if path.name == filename:
                        data = json.loads(text)
                        row = next(e for e in data['effects'] if e['unlock']['contentId'] == identity[1])
                        if change == 'rate': row['bonusBasisPoints'] += 1
                        elif change == 'kind': row['unlock']['kind'] = 'ability'
                        elif change == 'identity': row['unlock']['contentId'] = 'sibling'
                        elif change == 'metric': row['metric'] = 'unrelated_fee'
                        else: data['effects'].append(copy.deepcopy(row))
                        return json.dumps(data)
                    return text
                with self.subTest(filename=filename, change=change), patch.object(Path, 'read_text', changed):
                    self.assertNotIn(identity, services.exact_contracts(PROJECT))

    def test_exact_identities_rates_and_adoption_requirements(self):
        from test_chartered_companies import CharteredCompaniesTests
        fixture = CharteredCompaniesTests(); fixture.setUp()
        from central_banking import configuration
        source, contract, _ = configuration(PROJECT, fixture.world, fixture.settlements,
            fixture.authored, fixture.trade, policy='institution-courts',
            metrics={'institution_processing_cost_reduction': 'policy'}, function='configureGeneratedInstitutionCourts')
        self.assertIn('"policy", "progression_commercial_courts_institution", "institution_processing_cost_reduction", 400', source)
        adoption, _ = services.adoption_configuration(PROJECT, fixture.world, contract)
        self.assertIn('courtMinimumUrbanization = 14', adoption)
        bad = copy.deepcopy(fixture.world)
        next(n for n in bad['institutions'] if n['id'] == 'commercial_courts_institution')['prerequisiteIds'] = []
        with self.assertRaises(ValueError): services.adoption_configuration(PROJECT, bad, contract)
        from trade_finance import configuration as finance
        from test_trade_finance import TradeFinanceCompilationTests
        finance_fixture = TradeFinanceCompilationTests()
        finance_fixture.setUp()
        source, data, _ = finance(PROJECT, finance_fixture.world, finance_fixture.settlements,
                                  finance_fixture.authored, finance_fixture.trade)
        effect, = [e for e in data['effects'] if e['nodeId'] == 'commercial_statistics']
        self.assertEqual(({'kind':'modifier', 'contentId':'progression_commercial_statistics'}, 500), (effect['unlock'], effect['bonusBasisPoints']))
        self.assertIn('"market_slippage_reduction", 500,', source)
