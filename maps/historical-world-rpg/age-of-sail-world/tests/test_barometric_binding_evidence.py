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
COMPARISON = PREFIX + science.BAROMETRIC_COMPARISON
CHEMICAL = PREFIX + 'chemicalRegisteredResearchCommitsExactScientificWorkAgainstIdenticalControl'
BAROMETRIC = ('modifier', 'progression_barometric_measurement')
CLASSIFICATION = ('modifier', 'progression_chemical_classification')


class BarometricBindingEvidenceTests(unittest.TestCase):
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

    def transcript(self, omit_probe=None, fail_test=None, omitted_test=None, chemical_probes=True):
        expected = [row for row in self.expected if row['id'] != omitted_test]
        lines = ['Running tests']
        for row in expected:
            path, name = row['id'].rsplit(':', 1)
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            probes = set()
            if row['id'] == COMPARISON:
                probes = science.BAROMETRIC_PROBES - {omit_probe}
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

    def test_only_barometric_and_retained_classification_are_recognized(self):
        report, log = self.transcript()
        self.assertEqual({BAROMETRIC, CLASSIFICATION}, self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({
            'RESEARCH-UNBOUND-BAROMETRIC-MEASUREMENT-MODIFIER-PROGRESSION-BAROMETRIC-MEASUREMENT',
            'RESEARCH-UNBOUND-CHEMICAL-CLASSIFICATION-MODIFIER-PROGRESSION-CHEMICAL-CLASSIFICATION',
        }, before - after)
        self.assertFalse(after - before)

    def test_missing_focused_failed_stale_or_tampered_execution_rejects(self):
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
        # A successful, rehashed focused transcript still cannot close findings.
        report, log = self.transcript(omitted_test=self.expected[0]['id'])
        self.assertEqual(set(), self.bindings(report, log))
        for name in science.BAROMETRIC_TESTS:
            report, log = self.transcript(fail_test=PREFIX + name)
            self.assertEqual(set(), self.bindings(report, log))

    def test_weather_payment_supply_and_commit_must_execute_in_the_comparison(self):
        self.assertEqual(science.BAROMETRIC_PROBES, set(self.contract['systems']['barometric_voyage']))
        for probe in science.BAROMETRIC_PROBES:
            with self.subTest(probe=probe):
                report, log = self.transcript(omit_probe=probe)
                self.assertEqual({CLASSIFICATION}, self.bindings(report, log))
                # Metadata cannot supply a call missing from the raw transcript.
                report['productionCoverage']['tests'][COMPARISON].append(probe)
                self.assertEqual(set(), self.bindings(report, log))
        # The consumers have independent requirements in both directions.
        report, log = self.transcript(chemical_probes=False)
        self.assertEqual({BAROMETRIC}, self.bindings(report, log))

    def test_current_production_input_hashes_cannot_be_disconnected(self):
        report, log = self.transcript()
        for relative in ('wurst/ScienceExploration.wurst', 'wurst/ScienceCampaignRuntime.wurst',
                         'wurst/ScienceExplorationTests.wurst'):
            with self.subTest(source=relative):
                invalid = copy.deepcopy(report)
                invalid['inputs'][relative] = '0' * 64
                invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
                self.assertEqual(set(), self.bindings(invalid, log))
        original = Path.read_text
        source = self.sources['wurst/ScienceCampaignRuntime.wurst']
        def disconnected(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text.replace('actor.supply -= provisions', 'skip') if path == source else text
        with patch.object(Path, 'read_text', disconnected):
            self.assertEqual(set(), self.bindings(report, log))

    def test_exact_authored_typed_entitlement_metric_and_coefficient_are_required(self):
        report, log = self.transcript()
        design = PROJECT / 'scenario/progression/gameplay-effect-design.json'
        original = Path.read_text
        mutations = [lambda e: e['unlock'].update(kind='policy'),
                     lambda e: e['unlock'].update(contentId='progression_botanical_collecting'),
                     lambda e: e.update(nodeId='botanical_collecting'),
                     lambda e: e.update(metric='unknown_route_attrition_reduction'),
                     lambda e: e.update(bonusBasisPoints=999),
                     lambda e: e.update(bonusBasisPoints=1000.0),
                     lambda e: e.update(recipient='all_ships'),
                     lambda e: e.update(activation='commissioning_unlock')]
        for mutation in mutations:
            data = json.loads(original(design))
            effect = next(e for e in data['effects'] if e['nodeId'] == 'barometric_measurement')
            mutation(effect)
            def changed(path, *args, **kwargs):
                return json.dumps(data) if path == design else original(path, *args, **kwargs)
            with self.subTest(mutation=mutation), patch.object(Path, 'read_text', changed):
                self.assertEqual({CLASSIFICATION}, self.bindings(report, log))
        world_path = PROJECT / 'scenario/world/world.json'
        world = json.loads(original(world_path))
        node = next(n for n in world['technologies'] if n['id'] == 'barometric_measurement')
        node['unlocks'] = [{'kind': 'policy', 'contentId': 'progression_barometric_measurement'}]
        def unearned(path, *args, **kwargs):
            return json.dumps(world) if path == world_path else original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', unearned):
            self.assertEqual({CLASSIFICATION}, self.bindings(report, log))


if __name__ == '__main__':
    unittest.main()
