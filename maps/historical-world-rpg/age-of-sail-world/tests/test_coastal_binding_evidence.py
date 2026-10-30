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
import navigation_efficiency as navigation
import release_blocker_audit as audit

PREFIX = 'wurst/CoastalNavigationTests.wurst:'
COMPARISON = PREFIX + navigation.COASTAL_COMPARISON


class CoastalBindingEvidenceTests(unittest.TestCase):
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
                lines.extend('WCM_PROBE:' + probe for probe in sorted(navigation.COASTAL_PROBES - {omit_probe}))
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
        return navigation.verified_bindings(PROJECT, report, log, self.revision)

    def test_only_exact_finding_closes_with_complete_current_execution(self):
        report, log = self.transcript()
        self.assertEqual({navigation.COASTAL_UNLOCK}, self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({'RESEARCH-UNBOUND-COASTAL-TRIANGULATION-MODIFIER-PROGRESSION-COASTAL-TRIANGULATION'}, before - after)
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
        for name in navigation.COASTAL_TESTS:
            report, log = self.transcript(fail_test=PREFIX + name)
            self.assertEqual(set(), self.bindings(report, log))

    def test_resolution_and_commit_must_execute_in_isolated_comparison(self):
        self.assertEqual(navigation.COASTAL_PROBES, set(self.contract['systems']['coastal_navigation']))
        for probe in navigation.COASTAL_PROBES:
            report, log = self.transcript(omit_probe=probe)
            self.assertEqual(set(), self.bindings(report, log))
            report['productionCoverage']['tests'][COMPARISON].append(probe)
            self.assertEqual(set(), self.bindings(report, log))

    def test_wrong_identity_rate_and_kit_cost_reject_even_when_protocol_passes(self):
        report, log = self.transcript()
        path = PROJECT / 'scenario/naval/navigation-efficiency.json'
        original = Path.read_text
        mutations = [lambda s: s.update(id='celestial_navigation'),
                     lambda s: s['entitlement'].update(kind='policy'),
                     lambda s: s['entitlement'].update(contentId='progression_pilot_books'),
                     lambda s: s.update(reductionBasisPoints=799),
                     lambda s: s.update(reductionBasisPoints=801),
                     lambda s: s.update(reductionBasisPoints=800.0),
                     lambda s: s.update(qualification='astronomical_observation'),
                     lambda s: s.update(equipmentSiteId='channel_weather_survey')]
        for mutate in mutations:
            data = json.loads(original(path)); mutate(data['sources'][1])
            def changed(p, *a, **kw): return json.dumps(data) if p == path else original(p, *a, **kw)
            with patch.object(Path, 'read_text', changed):
                self.assertEqual(set(), self.bindings(report, log))
        path = PROJECT / 'scenario/progression/science-exploration.json'
        for field, value in [('equipmentCost', 119), ('equipmentUnits', 1), ('equipmentDays', 6), ('good', 'grain'), ('prerequisite', 'coastal_triangulation')]:
            data = json.loads(original(path)); data['sites'][3][field] = value
            def changed(p, *a, **kw): return json.dumps(data) if p == path else original(p, *a, **kw)
            with patch.object(Path, 'read_text', changed):
                self.assertEqual(set(), self.bindings(report, log))

    def test_disconnected_source_or_rehashed_wrong_production_input_rejects(self):
        report, log = self.transcript()
        for relative in ('wurst/VoyageNavigation.wurst', 'wurst/MilitarySettlementRuntime.wurst', 'wurst/CoastalNavigationTests.wurst'):
            invalid = copy.deepcopy(report); invalid['inputs'][relative] = '0' * 64
            invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
            self.assertEqual(set(), self.bindings(invalid, log))
        original = Path.read_text
        source = self.sources['wurst/VoyageNavigation.wurst']
        def changed(path, *a, **kw):
            text = original(path, *a, **kw)
            return text.replace('commitSource(state, source, amount)', 'skip') if path == source else text
        with patch.object(Path, 'read_text', changed):
            self.assertEqual(set(), self.bindings(report, log))
