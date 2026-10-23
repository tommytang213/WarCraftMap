"""Synthetic verifier controls, never gameplay or release execution evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
import integration_evidence as evidence
import release_blocker_audit as audit
import trade_finance as finance
import wurst_execution as execution


class AuctionBindingEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.revision = 'a' * 40
        cls.contract = evidence.load_contract(PROJECT)
        cls.sources = evidence.execution_sources(PROJECT)
        cls.expected = execution.discover(PROJECT, sources=cls.sources)
        cls.identity = evidence.source_identity(PROJECT, cls.revision)
        cls.inputs = {}
        for relative, source in cls.sources.items():
            probes = {key: value for key, value in cls.contract['probes'].items()
                      if value['path'] == relative}
            cls.inputs[relative] = evidence.digest(evidence.instrument(source.read_text(), probes).encode()
                                                   if probes else source.read_bytes())
        for name in ('wurst.build', 'wurst_run.args'):
            cls.inputs[name] = evidence.digest((PROJECT / name).read_bytes())

    def transcript(self, omit_probe=None, fail_test=None, omit_test=None):
        lines = ['Running tests']
        for row in self.expected:
            path, name = row['id'].split(':')
            if name == omit_test:
                continue
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            probes = set()
            if path == 'wurst/TradeFinanceTests.wurst':
                if name == 'registeredAuctionAndBrokerageResearchReduceExistingSettlementCostsPrecisely':
                    probes = {'finance_registration', 'finance_quote'}
                elif name == 'registeredBillsResearchReducesOnlyPaidBankFeesAndConservesPrincipal':
                    probes = {'finance_registration', 'finance_remit'}
                elif name == 'registeredCanalFinancePaysMaterialsPrincipalReducedFeeAndDailyLaborBeforeDurableOutput':
                    probes = {'finance_registration', 'finance_canal', 'finance_advance'}
                elif name == 'auctionOnlyRegisteredPurchaseAndSaleMatchControlsAndConserveAuthority':
                    probes = finance.AUCTION_PROBES - {omit_probe}
            lines.extend('WCM_PROBE:' + probe for probe in sorted(probes))
            lines.append('FAILED assertion: synthetic failure' if name == fail_test else '\tOK!')
        lines += [f'Tests succeeded: {len(self.expected)}/{len(self.expected)}', 'Finished running tests']
        log = ('\n'.join(lines) + '\n').encode()
        rows, errors = execution.parse_results(log.decode(), self.expected)
        return dict(format=execution.FORMAT, status='fail' if errors else 'pass',
                    executionStatus='completed', sourceRevision=self.revision,
                    sourceIdentity=self.identity, expected=self.expected, tests=rows,
                    errors=errors, returnCode=0, inputs=copy.deepcopy(self.inputs),
                    inputSetSha256=evidence.digest(evidence.canonical(self.inputs)),
                    logSha256=evidence.digest(log), discovered=len(rows), succeeded=len(rows),
                    compiler={'sha256': execution.PINNED_COMPILER_SHA256},
                    productionCoverage={'contractSha256': evidence.digest(evidence.canonical(self.contract)),
                                        'tests': evidence.observed_probes(log.decode(), rows, self.contract)}), log

    def bindings(self, report=None, log=None):
        return finance.verified_bindings(PROJECT, report, log, self.revision)

    def test_accepted_current_protocol_removes_exact_auction_finding_with_sibling_gates_intact(self):
        report, log = self.transcript()
        self.assertIn(finance.AUCTION_BINDING, self.bindings(report, log))
        baseline, baseline_log = self.transcript(omit_probe='finance_sell_settle')
        self.assertEqual({finance.AUCTION_BINDING}, self.bindings(report, log) - self.bindings(baseline, baseline_log))
        before = {row['id'] for row in audit._audit_research_bindings(
            execution=baseline, execution_log=baseline_log, revision=self.revision)}
        after = {row['id'] for row in audit._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({'RESEARCH-UNBOUND-AUCTION-MARKETS-MODIFIER-PROGRESSION-AUCTION-MARKETS'}, before - after)
        self.assertFalse(after - before)

    def test_missing_failed_stale_tampered_focused_or_disconnected_evidence_rejects(self):
        report, log = self.transcript()
        self.assertEqual(set(), self.bindings())
        for field, value in [('status', 'fail'), ('executionStatus', 'not_run'),
                             ('sourceRevision', 'b' * 40), ('sourceIdentity', {}),
                             ('compiler', {'sha256': '0' * 64}), ('logSha256', '0' * 64),
                             ('inputSetSha256', '0' * 64), ('productionCoverage', {}),
                             ('expected', report['expected'][:-1])]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(report)
                invalid[field] = value
                self.assertEqual(set(), self.bindings(invalid, log))
        self.assertEqual(set(), self.bindings(report, log + b'tampered\n'))
        for relative in ('wurst/FinanceCampaignRuntime.wurst', 'wurst/PlayableTrade.wurst'):
            invalid = copy.deepcopy(report)
            invalid['inputs'][relative] = '0' * 64
            invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
            self.assertEqual(set(), self.bindings(invalid, log))
        # Caller claims cannot repair a disconnected production input.
        source = self.sources['wurst/PlayableTrade.wurst']
        original = Path.read_text
        def changed(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text.replace('destination.money-=charge', 'skip') if path == source else text
        with patch.object(Path, 'read_text', changed):
            self.assertEqual(set(), self.bindings(report, log))

    def test_every_auction_call_and_all_original_finance_cases_remain_required(self):
        for probe in finance.AUCTION_PROBES:
            with self.subTest(probe=probe):
                report, log = self.transcript(omit_probe=probe)
                self.assertNotIn(finance.AUCTION_BINDING, self.bindings(report, log))
                self.assertEqual(3, len(self.bindings(report, log)))
                key = 'wurst/TradeFinanceTests.wurst:auctionOnlyRegisteredPurchaseAndSaleMatchControlsAndConserveAuthority'
                report['productionCoverage']['tests'].setdefault(key, []).append(probe)
                self.assertEqual(set(), self.bindings(report, log))
        for name in finance.REQUIRED_TESTS | finance.AUCTION_TESTS:
            with self.subTest(failed=name):
                report, log = self.transcript(fail_test=name)
                self.assertEqual(set(), self.bindings(report, log))
            with self.subTest(missing=name):
                report, log = self.transcript(omit_test=name)
                self.assertEqual(set(), self.bindings(report, log))


if __name__ == '__main__':
    unittest.main()
