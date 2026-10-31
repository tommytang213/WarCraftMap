"""Synthetic protocol regressions; these transcripts are never release evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
import integration_evidence as evidence
import wurst_execution as execution
import industry_catalog as industry
import release_blocker_audit as audit

PREFIX = 'wurst/IndustryTests.wurst:'
COMPARISON = PREFIX + industry.COKE_COMPARISON


class CokeBindingEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.revision = 'a' * 40
        cls.contract = evidence.load_contract(PROJECT)
        cls.sources = evidence.execution_sources(PROJECT)
        cls.expected = execution.discover(PROJECT, sources=cls.sources)
        cls.identity = evidence.source_identity(PROJECT, cls.revision)
        cls.inputs = {}
        for relative, source in cls.sources.items():
            probes = {key: value for key, value in cls.contract['probes'].items() if value['path'] == relative}
            cls.inputs[relative] = evidence.digest(evidence.instrument(source.read_text(), probes).encode()
                                                  if probes else source.read_bytes())
        for name in ('wurst.build', 'wurst_run.args'):
            cls.inputs[name] = evidence.digest((PROJECT / name).read_bytes())

    def transcript(self, omit_probe=None, fail_test=None, omitted_test=None):
        expected = [row for row in self.expected if row['id'] != omitted_test]
        lines = ['Running tests']
        for row in expected:
            path, name = row['id'].rsplit(':', 1)
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            if row['id'] == COMPARISON:
                lines.extend('WCM_PROBE:' + probe for probe in sorted(industry.COKE_PROBES - {omit_probe}))
            if row['id'] == PREFIX + 'cokeUpstreamPaidExtractionPreparationAndTransportConserveResourcesWithoutLiquidityGrants':
                lines.extend('WCM_PROBE:' + probe for probe in ('industry_material', 'industry_pay', 'industry_labor', 'industry_output'))
            lines.append('FAILED assertion: synthetic failure' if row['id'] == fail_test else '\tOK!')
        lines += [f'Tests succeeded: {len(expected)}/{len(expected)}', 'Finished running tests']
        log = ('\n'.join(lines) + '\n').encode()
        rows, errors = execution.parse_results(log.decode(), expected)
        return dict(format=execution.FORMAT, status='fail' if errors else 'pass',
                    executionStatus='completed', sourceRevision=self.revision,
                    sourceIdentity=self.identity, expected=expected, tests=rows,
                    errors=errors, returnCode=0, inputs=self.inputs,
                    inputSetSha256=evidence.digest(evidence.canonical(self.inputs)),
                    logSha256=evidence.digest(log), discovered=len(rows), succeeded=len(rows),
                    compiler={'sha256': execution.PINNED_COMPILER_SHA256},
                    productionCoverage={'contractSha256': evidence.digest(evidence.canonical(self.contract)),
                                        'tests': evidence.observed_probes(log.decode(), rows, self.contract)}), log

    def bindings(self, report=None, log=None):
        return industry.verified_coke_bindings(PROJECT, report, log, self.revision)

    def test_only_exact_finding_closes_with_complete_current_execution(self):
        report, log = self.transcript()
        self.assertEqual({industry.COKE_IDENTITY}, self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({'RESEARCH-UNBOUND-COKE-SMELTED-IRON-MODIFIER-PROGRESSION-COKE-SMELTED-IRON'}, before - after)
        self.assertFalse(after - before)

    def test_missing_focused_failed_stale_or_tampered_execution_rejects(self):
        report, log = self.transcript()
        self.assertEqual(set(), self.bindings())
        for field, value in [('status', 'fail'), ('executionStatus', 'not_run'),
                             ('sourceRevision', 'b' * 40), ('sourceIdentity', {}),
                             ('compiler', {'sha256': '0' * 64}), ('logSha256', '0' * 64),
                             ('inputSetSha256', '0' * 64), ('productionCoverage', {}),
                             ('expected', report['expected'][:-1])]:
            invalid = copy.deepcopy(report); invalid[field] = value
            with self.subTest(field=field): self.assertEqual(set(), self.bindings(invalid, log))
        self.assertEqual(set(), self.bindings(report, log + b'tampered\n'))
        report, log = self.transcript(omitted_test=self.expected[0]['id'])
        self.assertEqual(set(), self.bindings(report, log))
        for name in industry.COKE_TESTS:
            report, log = self.transcript(fail_test=PREFIX + name)
            self.assertEqual(set(), self.bindings(report, log))

    def test_resolution_and_commit_must_execute_in_isolated_comparison(self):
        self.assertEqual(industry.COKE_PROBES, set(self.contract['systems']['mineral_fuel_industry']))
        for probe in industry.COKE_PROBES:
            report, log = self.transcript(omit_probe=probe)
            self.assertEqual(set(), self.bindings(report, log))
            report['productionCoverage']['tests'][COMPARISON].append(probe)
            self.assertEqual(set(), self.bindings(report, log))

    def test_sibling_industry_evidence_cannot_close_coke(self):
        report, log = self.transcript(omit_probe='industry_yield')
        self.assertEqual(set(), self.bindings(report, log))
        with patch.object(audit.runtime_acceptance, 'verify_execution_coverage', return_value={
                'industry': ['wurst/IndustryTests.wurst:industryRegisteredResearchAndPaidActionsProduceExactYieldAndFasterBarrelsAgainstControl']}):
            self.assertNotIn(industry.COKE_IDENTITY, audit._verified_industry_bindings({}, b'', self.revision))

    def test_wrong_identity_rate_fuel_or_bill_cannot_close_even_with_protocol_coverage(self):
        report, log = self.transcript()
        for mutate in (lambda c: c['effects'][-1].update(bonusBasisPoints=599),
                       lambda c: c['effects'][-1].update(requiredFuel='timber'),
                       lambda c: c['effects'][-1]['unlock'].update(kind='policy'),
                       lambda c: c['rules']['recipes'][2].update(fuelUnits=49),
                       lambda c: c['rules']['setup'].update(money=119)):
            catalog = copy.deepcopy(industry.build()['catalog']); mutate(catalog)
            with patch.object(industry, 'build', return_value={'catalog': catalog}):
                self.assertEqual(set(), self.bindings(report, log))

    def test_generated_contract_exact_identity_and_no_fuel_or_cash_grants(self):
        payload = industry.build()
        coke = [c for c in payload['catalog']['consumers'] if c['nodeId'] == 'coke_smelted_iron']
        self.assertEqual(1, len(coke))
        self.assertEqual(['mineral_iron_refining'], coke[0]['recipeIds'])
        self.assertEqual('coke', coke[0]['requiredFuel'])
        self.assertEqual(600, coke[0]['bonusBasisPoints'])
        self.assertEqual({'bristol'}, {s['settlementId'] for s in payload['catalog']['sites'] if s['outputGood'] in ('coal', 'coke')})
        for line in payload['wurst'].splitlines():
            if 'runtime.registerMarketProfile(' in line:
                self.assertIn(', 0, 0, ', line)


if __name__ == '__main__': unittest.main()
