"""Synthetic protocol rejection tests; these transcripts are never release evidence."""
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
COMPARISON = PREFIX + science.COMPARATIVE_COMPARISON
CHEMICAL = PREFIX + 'chemicalRegisteredResearchCommitsExactScientificWorkAgainstIdenticalControl'
CALCULUS = ('modifier', 'progression_calculus_methods')
CLASSIFICATION = ('modifier', 'progression_chemical_classification')
BAROMETRIC = ('modifier', 'progression_barometric_measurement')
SIBLING = PREFIX + science.BAROMETRIC_COMPARISON


LINGUISTICS = ('modifier', 'progression_comparative_linguistics')
class ComparativeBindingEvidenceTests(unittest.TestCase):
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

    def transcript(self, omit_probe=None, fail_test=None, omitted_test=None, chemical_probes=True, calculus_probes=True, sibling_probes=True):
        expected = [row for row in self.expected if row['id'] != omitted_test]
        lines = ['Running tests']
        for row in expected:
            path, name = row['id'].rsplit(':', 1)
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            probes = set()
            if row['id'] == SIBLING and sibling_probes:
                probes = science.BAROMETRIC_PROBES
            if row['id'] == COMPARISON and calculus_probes:
                probes = science.COMPARATIVE_PROBES - {omit_probe}
            if row['id'] == CHEMICAL and chemical_probes:
                probes = {'science_registration', 'science_action', 'science_advance',
                          'science_pay', 'science_complete', 'dispatch'}
            lines.extend('WCM_PROBE:' + probe for probe in sorted(probes))
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

    def test_exact_comparative_finding_requires_its_own_complete_execution(self):
        report, log = self.transcript(chemical_probes=False, sibling_probes=False)
        self.assertEqual({LINGUISTICS}, self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({'RESEARCH-UNBOUND-COMPARATIVE-LINGUISTICS-MODIFIER-PROGRESSION-COMPARATIVE-LINGUISTICS'}, before - after)
        self.assertFalse(after - before)
        report, log = self.transcript(calculus_probes=False)
        self.assertEqual({BAROMETRIC, CLASSIFICATION}, self.bindings(report, log))

    def test_each_production_call_must_be_observed_in_this_comparison(self):
        self.assertEqual(science.COMPARATIVE_PROBES, set(self.contract['systems']['comparative_scholarship']))
        for probe in science.COMPARATIVE_PROBES:
            with self.subTest(probe=probe):
                report, log = self.transcript(omit_probe=probe)
                self.assertNotIn(LINGUISTICS, self.bindings(report, log))
                report['productionCoverage']['tests'][COMPARISON].append(probe)
                self.assertEqual(set(), self.bindings(report, log))
        for name in science.COMPARATIVE_TESTS:
            report, log = self.transcript(fail_test=PREFIX + name)
            self.assertEqual(set(), self.bindings(report, log))

    def test_focused_stale_failed_tampered_or_disconnected_evidence_cannot_close(self):
        self.assertEqual(set(), self.bindings())
        report, log = self.transcript()
        for field, value in [('status', 'fail'), ('executionStatus', 'not_run'),
                             ('sourceRevision', 'b' * 40), ('sourceIdentity', {}),
                             ('compiler', {'sha256': '0' * 64}), ('logSha256', '0' * 64),
                             ('inputSetSha256', '0' * 64), ('productionCoverage', {}),
                             ('expected', report['expected'][:-1])]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(report); invalid[field] = value
                self.assertEqual(set(), self.bindings(invalid, log))
        self.assertEqual(set(), self.bindings(report, log + b'tampered'))
        report, log = self.transcript(omitted_test=self.expected[0]['id'])
        self.assertEqual(set(), self.bindings(report, log))
        report, log = self.transcript()
        for relative in ('wurst/ScienceExploration.wurst', 'wurst/ScienceCampaignRuntime.wurst',
                         'wurst/ScienceExplorationTests.wurst', 'wurst/ScenarioData.wurst'):
            if relative not in report['inputs']:
                continue
            invalid = copy.deepcopy(report)
            invalid['inputs'][relative] = '0' * 64
            invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
            self.assertEqual(set(), self.bindings(invalid, log))
        original = Path.read_text
        source = self.sources['wurst/ScienceExploration.wurst']
        def disconnected(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text.replace('s.commitWork(d.dailyWork, rate)', 'skip') if path == source else text
        with patch.object(Path, 'read_text', disconnected):
            self.assertEqual(set(), self.bindings(report, log))

    def test_exact_typed_identity_coefficient_and_multilingual_scope_are_required(self):
        report, log = self.transcript(chemical_probes=False, sibling_probes=False)
        path = PROJECT / 'scenario/progression/comparative-linguistics.json'
        original = Path.read_text
        mutations = [lambda d: d['unlock'].update(kind='policy'),
                     lambda d: d['unlock'].update(contentId='progression_calculus_methods'),
                     lambda d: d.update(nodeId='calculus_methods'),
                     lambda d: d.update(metric='research_generation_efficiency'),
                     lambda d: d.update(bonusBasisPoints=399),
                     lambda d: d.update(bonusBasisPoints=401),
                     lambda d: d.update(bonusBasisPoints=400.0),
                     lambda d: d.update(bonusBasisPoints=True),
                     lambda d: d.update(siteId='channel_weather_survey'),
                     lambda d: d['targets'][0].update(id='printed_observation_tables'),
                     lambda d: d['targets'][0].update(sourceLanguages=['latin']),
                     lambda d: d['targets'][0].update(corpusIds=['linnaeus_systema_naturae']),
                     lambda d: d['corpora'][1].update(language='latin'),
                     lambda d: d.update(corpora=[])]
        for mutation in mutations:
            data = json.loads(original(path)); mutation(data)
            def changed(candidate, *args, **kwargs):
                return json.dumps(data) if candidate == path else original(candidate, *args, **kwargs)
            with self.subTest(mutation=mutation), patch.object(Path, 'read_text', changed):
                self.assertEqual(set(), self.bindings(report, log))
        world_path = PROJECT / 'scenario/world/world.json'
        data = json.loads(original(world_path))
        next(n for n in data['technologies'] if n['id'] == 'comparative_linguistics')['unlocks'] = []
        def changed(candidate, *args, **kwargs):
            return json.dumps(data) if candidate == world_path else original(candidate, *args, **kwargs)
        with patch.object(Path, 'read_text', changed):
            self.assertEqual(set(), self.bindings(report, log))


if __name__ == '__main__':
    unittest.main()
