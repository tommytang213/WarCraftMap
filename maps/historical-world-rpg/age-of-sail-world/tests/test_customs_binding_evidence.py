"""Protocol negative controls; synthetic transcripts are never release evidence."""
import copy
import unittest
from test_auction_binding_evidence import AuctionBindingEvidenceTests, PROJECT
import trade_finance as finance
import integration_evidence as evidence
import wurst_execution as execution


class CustomsBindingEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AuctionBindingEvidenceTests.setUpClass()
        cls.fixture = AuctionBindingEvidenceTests()

    def transcript(self, omit_identity=None, omit_probe=None, fail=None):
        report, old_log = self.fixture.transcript(fail_test=fail)
        lines = []
        for line in old_log.decode().splitlines():
            lines.append(line)
            for identity, name in finance.CUSTOMS_COMPARISONS.items():
                if line.startswith('Running ') and line.endswith(' - ' + name + '..'):
                    probes = finance.CUSTOMS_PROBES - ({omit_probe} if identity == omit_identity else set())
                    lines.extend('WCM_PROBE:' + probe for probe in sorted(probes))
        log = ('\n'.join(lines) + '\n').encode()
        rows, errors = execution.parse_results(log.decode(), self.fixture.expected)
        report.update(tests=rows, errors=errors, status='fail' if errors else 'pass',
                      logSha256=evidence.digest(log),
                      productionCoverage={'contractSha256': evidence.digest(evidence.canonical(self.fixture.contract)),
                                          'tests': evidence.observed_probes(log.decode(), rows, self.fixture.contract)})
        return report, log

    def bindings(self, report=None, log=None):
        return finance.verified_bindings(PROJECT,
                                         report, log, self.fixture.revision)

    def test_exact_independent_paid_building_and_credit_comparisons_bind_only_with_real_probes(self):
        report, log = self.transcript()
        self.assertTrue(set(finance.CUSTOMS_COMPARISONS) <= self.bindings(report, log))
        for identity in finance.CUSTOMS_COMPARISONS:
            for probe in finance.CUSTOMS_PROBES:
                with self.subTest(identity=identity, probe=probe):
                    report, log = self.transcript(identity, probe)
                    bound = self.bindings(report, log)
                    self.assertNotIn(identity, bound)
                    self.assertIn(next(x for x in finance.CUSTOMS_COMPARISONS if x != identity), bound)
                    self.assertIn(finance.AUCTION_BINDING, bound)

    def test_missing_failed_stale_or_forged_complete_evidence_cannot_close_either_identity(self):
        self.assertEqual(set(), self.bindings())
        report, log = self.transcript()
        for name in finance.CUSTOMS_TESTS | set(finance.CUSTOMS_COMPARISONS.values()):
            invalid, failed_log = self.transcript(fail=name)
            self.assertEqual(set(), self.bindings(invalid, failed_log))
        for field, value in [('sourceRevision', 'b' * 40), ('sourceIdentity', {}),
                             ('compiler', {'sha256': '0' * 64}), ('inputs', {}),
                             ('expected', report['expected'][:-1]), ('productionCoverage', {})]:
            invalid = copy.deepcopy(report)
            invalid[field] = value
            self.assertEqual(set(), self.bindings(invalid, log))
        self.assertEqual(set(), self.bindings(report, log + b'tampered'))


if __name__ == '__main__':
    unittest.main()
