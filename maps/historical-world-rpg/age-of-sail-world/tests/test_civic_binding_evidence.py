"""Synthetic transcripts exercise audit rejection, never establish game execution."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
import civic_governance as civic
import integration_evidence as evidence
import release_blocker_audit as audit
import wurst_execution as execution


class CivicBindingEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.revision = 'a' * 40
        cls.contract = evidence.load_contract(PROJECT)
        cls.sources = evidence.execution_sources(PROJECT)
        cls.expected = execution.discover(PROJECT, sources=cls.sources)
        inputs = {}
        for relative, source in cls.sources.items():
            probes = {key: value for key, value in cls.contract['probes'].items()
                      if value['path'] == relative}
            inputs[relative] = evidence.digest(evidence.instrument(source.read_text(), probes).encode()
                                               if probes else source.read_bytes())
        for name in ('wurst.build', 'wurst_run.args'):
            inputs[name] = evidence.digest((PROJECT / name).read_bytes())
        cls.inputs = inputs

    def transcript(self, omit_probe=None, omit_from=None, fail_test=None):
        lines = ['Running tests']
        for row in self.expected:
            path, name = row['id'].split(':')
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            for _, (system, comparative, _) in civic.COMPARATIVE_PATHS.items():
                if name == comparative:
                    lines.extend('WCM_PROBE:' + probe for probe in self.contract['systems'][system]
                                 if probe != omit_probe or name != omit_from)
            lines.append('FAILED assertion: synthetic failure' if row['id'] == fail_test else '\tOK!')
        lines += [f'Tests succeeded: {len(self.expected)}/{len(self.expected)}', 'Finished running tests']
        log = ('\n'.join(lines) + '\n').encode()
        rows, errors = execution.parse_results(log.decode(), self.expected)
        return dict(format=execution.FORMAT, status='fail' if errors else 'pass',
                    executionStatus='completed', sourceRevision=self.revision,
                    sourceIdentity=evidence.source_identity(PROJECT, self.revision),
                    expected=self.expected, tests=rows, errors=errors, returnCode=0,
                    inputs=self.inputs, inputSetSha256=evidence.digest(evidence.canonical(self.inputs)),
                    logSha256=evidence.digest(log), discovered=len(rows), succeeded=len(rows),
                    compiler={'sha256': execution.PINNED_COMPILER_SHA256},
                    productionCoverage={'contractSha256': evidence.digest(evidence.canonical(self.contract)),
                                        'tests': evidence.observed_probes(log.decode(), rows, self.contract)}), log

    def bindings(self, report=None, log=None):
        return civic.verified_bindings(PROJECT, report, log, self.revision)

    def test_verified_protocol_removes_only_the_three_supplied_findings(self):
        report, log = self.transcript()
        self.assertEqual(set(civic.CLOSURE_EFFECTS), self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({
            'RESEARCH-UNBOUND-ABOLITIONIST-PUBLIC-SPHERE-POLICY-PROGRESSION-ABOLITIONIST-PUBLIC-SPHERE',
            'RESEARCH-UNBOUND-ANATOMY-AND-MEDICINE-ABILITY-EPIDEMIC-CONTROL',
            'RESEARCH-UNBOUND-CADASTRAL-SURVEY-MODIFIER-PROGRESSION-CADASTRAL-SURVEY',
        }, before - after)
        self.assertFalse(after - before)

    def test_missing_failed_stale_tampered_and_focused_execution_fail_closed(self):
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
        invalid = copy.deepcopy(report)
        invalid['inputs']['wurst/CivicCampaignRuntime.wurst'] = '0' * 64
        invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
        self.assertEqual(set(), self.bindings(invalid, log))
        # Rehashed source identities cannot hide disconnected interpreter inputs.
        source = self.sources['wurst/CivicCampaignRuntime.wurst']
        original = Path.read_text
        def changed(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text.replace('supplies.stock -= units', 'skip') if path == source else text
        with patch.object(Path, 'read_text', changed):
            self.assertEqual(set(), self.bindings(report, log))

    def test_each_consumer_requires_all_actual_calls_in_its_matched_control(self):
        for pair, (_, name, probes) in civic.COMPARATIVE_PATHS.items():
            for probe in probes:
                with self.subTest(pair=pair, disconnected=probe):
                    report, log = self.transcript(omit_probe=probe, omit_from=name)
                    self.assertEqual(set(civic.CLOSURE_EFFECTS) - {pair}, self.bindings(report, log))
                    # Declaring the missing call cannot repair the raw transcript.
                    key = 'wurst/CivicGovernanceTests.wurst:' + name
                    report['productionCoverage']['tests'][key].append(probe)
                    self.assertEqual(set(), self.bindings(report, log))

    def test_failed_negative_or_rollback_test_cannot_close_either_finding(self):
        names = {'wurst/CivicGovernanceTests.wurst:' + name
                 for name in civic.REQUIRED_TESTS | civic.SURVEY_REQUIRED_TESTS}
        for name in names | {civic.ROLLBACK_TEST, civic.SURVEY_ROLLBACK_TEST}:
            with self.subTest(failed=name):
                report, log = self.transcript(fail_test=name)
                self.assertEqual(set(), self.bindings(report, log))

    def test_weakened_contract_or_changed_design_cannot_expand_recognition(self):
        report, log = self.transcript()
        with patch.object(civic, 'configuration', return_value=('', {'effects': []}, [])):
            self.assertEqual(set(), self.bindings(report, log))
        # Even a future coverage contract that omits an outcome cannot silently
        # weaken the verifier's fixed minimum observed-call requirements.
        report['productionCoverage']['tests'] = {}
        coverage = {system: ['wurst/CivicGovernanceTests.wurst:' + name]
                    for system, name, _ in civic.COMPARATIVE_PATHS.values()}
        with patch.object(evidence, 'verify_execution_coverage', return_value=coverage):
            self.assertEqual(set(), self.bindings(report, log))


if __name__ == '__main__':
    unittest.main()
