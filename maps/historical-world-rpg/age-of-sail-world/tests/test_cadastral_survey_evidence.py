"""Verifier decision-unit tests; mocked coverage is NOT pinned game execution.

The full synthetic transcript/revision/input rejection protocol remains covered
by test_civic_binding_evidence. These tests isolate the exact survey contract
and ensure survey-specific prerequisites cannot weaken or replace sibling gates.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
import civic_governance as civic
import integration_evidence as evidence

SURVEY = ('modifier', 'progression_cadastral_survey')
PREFIX = 'wurst/CivicGovernanceTests.wurst:'


class CadastralSurveyDecisionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        (self.project / 'scenario/world').mkdir(parents=True)
        (self.project / 'scenario/world/world.json').write_text('{}')
        names = civic.REQUIRED_TESTS | civic.SURVEY_REQUIRED_TESTS
        self.report = {
            'tests': [{'id': PREFIX + name, 'status': 'pass'} for name in names]
                     + [{'id': name, 'status': 'pass'}
                        for name in (civic.ROLLBACK_TEST, civic.SURVEY_ROLLBACK_TEST)],
            'productionCoverage': {'tests': {
                PREFIX + name: sorted(probes)
                for _, name, probes in civic.COMPARATIVE_PATHS.values()}},
        }
        self.coverage = {system: [PREFIX + name]
                         for system, name, _ in civic.COMPARATIVE_PATHS.values()}
        self.effects = [{'nodeId': node, 'metric': metric, 'bonusBasisPoints': bonus,
                         'unlock': {'kind': pair[0], 'contentId': pair[1]}}
                        for pair, (node, metric, bonus) in civic.CLOSURE_EFFECTS.items()]

    def bindings(self):
        with patch.object(evidence, 'verify_execution_coverage', return_value=self.coverage), \
             patch.object(civic, 'configuration', return_value=('', {'effects': self.effects}, [])):
            return civic.verified_bindings(self.project, self.report, b'unit-only', 'a' * 40)

    def test_exact_contract_and_own_comparative_calls_are_required(self):
        self.assertEqual(set(civic.CLOSURE_EFFECTS), self.bindings())
        _, name, probes = civic.COMPARATIVE_PATHS[SURVEY]
        for probe in probes:
            with self.subTest(probe=probe):
                self.report['productionCoverage']['tests'][PREFIX + name].remove(probe)
                self.assertEqual(set(civic.CLOSURE_EFFECTS) - {SURVEY}, self.bindings())
                self.report['productionCoverage']['tests'][PREFIX + name].append(probe)

    def test_sibling_only_or_unrelated_test_coverage_cannot_close_survey(self):
        self.coverage['cadastral_survey'] = self.coverage['civic_policy']
        self.assertEqual(set(civic.CLOSURE_EFFECTS) - {SURVEY}, self.bindings())
        self.coverage.pop('cadastral_survey')
        self.assertEqual(set(civic.CLOSURE_EFFECTS) - {SURVEY}, self.bindings())

    def test_survey_specific_required_tests_do_not_replace_sibling_gates(self):
        for name in civic.SURVEY_REQUIRED_TESTS - civic.REQUIRED_TESTS:
            with self.subTest(name=name):
                saved = self.report['tests']
                self.report['tests'] = [row for row in saved if row['id'] != PREFIX + name]
                self.assertEqual(set(civic.CLOSURE_EFFECTS) - {SURVEY}, self.bindings())
                self.report['tests'] = saved
        for name in civic.REQUIRED_TESTS:
            with self.subTest(existing_required=name):
                saved = self.report['tests']
                self.report['tests'] = [row for row in saved if row['id'] != PREFIX + name]
                self.assertEqual(set(), self.bindings())
                self.report['tests'] = saved
        self.report['tests'] = [row for row in self.report['tests']
                                if row['id'] != civic.SURVEY_ROLLBACK_TEST]
        self.assertEqual(set(civic.CLOSURE_EFFECTS) - {SURVEY}, self.bindings())

    def test_altered_exact_identity_metric_or_amount_cannot_close_survey(self):
        original = copy.deepcopy(self.effects)
        for field, value in [('nodeId', 'other'), ('metric', 'civic_reform_diffusion'),
                             ('bonusBasisPoints', 499), ('kind', 'policy'),
                             ('contentId', 'other')]:
            with self.subTest(field=field):
                self.effects = copy.deepcopy(original)
                survey = next(row for row in self.effects if row['nodeId'] == 'cadastral_survey')
                if field in {'kind', 'contentId'}:
                    survey['unlock'][field] = value
                else:
                    survey[field] = value
                self.assertEqual(set(civic.CLOSURE_EFFECTS) - {SURVEY}, self.bindings())

    def test_rejected_execution_cannot_be_repaired_by_declared_probe_metadata(self):
        for error in (ValueError('stale execution'), OSError('missing transcript'),
                      KeyError('missing input')):
            with self.subTest(error=type(error).__name__), \
                 patch.object(evidence, 'verify_execution_coverage', side_effect=error):
                self.assertEqual(set(), civic.verified_bindings(
                    self.project, self.report, b'unit-only', 'a' * 40))


if __name__ == '__main__':
    unittest.main()
