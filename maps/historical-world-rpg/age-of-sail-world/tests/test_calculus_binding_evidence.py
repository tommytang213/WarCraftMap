"""Synthetic protocol rejection tests; only pinned production runs can be release evidence."""
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
import science_exploration as science
import release_blocker_audit as audit

PREFIX = 'wurst/ScienceExplorationTests.wurst:'
COMPARISON = PREFIX + science.CALCULUS_COMPARISON
CALCULUS = ('modifier', 'progression_calculus_methods')
FINDING = 'RESEARCH-UNBOUND-CALCULUS-METHODS-MODIFIER-PROGRESSION-CALCULUS-METHODS'


class CalculusBindingEvidenceTests(unittest.TestCase):
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

    def transcript(self, *, omit_probe=None, omitted_test=None, fail_test=None, comparison=COMPARISON):
        expected = [row for row in self.expected if row['id'] != omitted_test]
        lines = ['Running tests']
        for row in expected:
            path, name = row['id'].rsplit(':', 1)
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            if row['id'] == comparison:
                lines.extend('WCM_PROBE:' + probe for probe in sorted(science.CALCULUS_PROBES - {omit_probe}))
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
        return science.verified_bindings(PROJECT, report, log, self.revision)

    def test_exact_calculus_finding_closes_only_with_complete_comparison(self):
        report, log = self.transcript()
        self.assertEqual({CALCULUS}, self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({FINDING}, before - after)
        self.assertFalse(after - before)

    def test_missing_production_probe_or_sibling_comparison_rejects(self):
        self.assertEqual(science.CALCULUS_PROBES, set(self.contract['systems']['calculus_scholarly_work']))
        for probe in science.CALCULUS_PROBES:
            with self.subTest(probe=probe):
                report, log = self.transcript(omit_probe=probe)
                self.assertNotIn(CALCULUS, self.bindings(report, log))
                report['productionCoverage']['tests'][COMPARISON].append(probe)
                self.assertNotIn(CALCULUS, self.bindings(report, log))
        sibling = PREFIX + 'chemicalRegisteredResearchCommitsExactScientificWorkAgainstIdenticalControl'
        report, log = self.transcript(comparison=sibling)
        self.assertNotIn(CALCULUS, self.bindings(report, log))
        report, log = self.transcript(omitted_test=COMPARISON)
        self.assertNotIn(CALCULUS, self.bindings(report, log))

    def test_focused_failed_stale_and_tampered_execution_rejects(self):
        report, log = self.transcript()
        self.assertNotIn(CALCULUS, self.bindings())
        for field, value in [('status', 'fail'), ('executionStatus', 'not_run'),
                             ('sourceRevision', 'b' * 40), ('sourceIdentity', {}),
                             ('compiler', {'sha256': '0' * 64}), ('logSha256', '0' * 64),
                             ('inputSetSha256', '0' * 64), ('productionCoverage', {}),
                             ('expected', report['expected'][:-1])]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(report)
                invalid[field] = value
                self.assertNotIn(CALCULUS, self.bindings(invalid, log))
        self.assertNotIn(CALCULUS, self.bindings(report, log + b'tampered\n'))
        report, log = self.transcript(omitted_test=self.expected[0]['id'])
        self.assertNotIn(CALCULUS, self.bindings(report, log))
        for name in science.CALCULUS_TESTS:
            report, log = self.transcript(fail_test=PREFIX + name)
            self.assertNotIn(CALCULUS, self.bindings(report, log))

    def test_authored_identity_rate_scope_and_real_sources_are_required(self):
        report, log = self.transcript()
        design = PROJECT / 'scenario/progression/gameplay-effect-design.json'
        original = Path.read_text
        changes = [lambda e: e['unlock'].update(kind='policy'),
                   lambda e: e['unlock'].update(contentId='progression_chemical_classification'),
                   lambda e: e.update(nodeId='chemical_classification'),
                   lambda e: e.update(metric='storm_attrition_reduction'),
                   lambda e: e.update(bonusBasisPoints=499),
                   lambda e: e.update(bonusBasisPoints=500.0),
                   lambda e: e.update(recipient='all_technology'),
                   lambda e: e.update(activation='commissioning_unlock')]
        for change in changes:
            data = json.loads(original(design))
            effect = next(e for e in data['effects'] if e['nodeId'] == 'calculus_methods')
            change(effect)
            def altered(path, *args, **kwargs):
                return json.dumps(data) if path == design else original(path, *args, **kwargs)
            with self.subTest(change=change), patch.object(Path, 'read_text', altered):
                self.assertNotIn(CALCULUS, self.bindings(report, log))
        world_path = PROJECT / 'scenario/world/world.json'
        world = json.loads(original(world_path))
        next(n for n in world['technologies'] if n['id'] == 'calculus_methods')['unlocks'] = []
        def unearned(path, *args, **kwargs):
            return json.dumps(world) if path == world_path else original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', unearned):
            self.assertNotIn(CALCULUS, self.bindings(report, log))
        for relative in ('wurst/ScienceExploration.wurst', 'wurst/ScienceCampaignRuntime.wurst',
                         'wurst/ScienceExplorationTests.wurst'):
            invalid = copy.deepcopy(report)
            invalid['inputs'][relative] = '0' * 64
            invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
            self.assertNotIn(CALCULUS, self.bindings(invalid, log))


if __name__ == '__main__':
    unittest.main()
