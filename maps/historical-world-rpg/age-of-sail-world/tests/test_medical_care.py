"""Local-care generation and synthetic evidence rejection; never release evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
import medical_care as medical
import civic_governance as civic
import integration_evidence as evidence
import wurst_execution as execution
import release_blocker_audit as release

PREFIX = 'wurst/MedicalCareTests.wurst:'


class MedicalCareContracts(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.contract = json.loads((PROJECT / 'scenario/progression/medical-care.json').read_text())

    def test_exact_consumers_and_authored_prerequisites_availability(self):
        lines, effects, metadata, sources = medical.configuration(PROJECT, self.world)
        self.assertEqual([500, 500], [e['bonusBasisPoints'] for e in effects])
        self.assertEqual([1650, 1750], [e['preferredYear'] for e in metadata['consumers']])
        self.assertEqual([['military_field_hospitals', 'fleet_victualling'], ['obstetric_training']],
                         [e['prerequisiteIds'] for e in metadata['consumers']])
        self.assertEqual(5, len(sources))
        self.assertIn('\tledger.carePreparationDays = 90', lines)
        self.assertIn('\tledger.recordsDailyMoney = 1', lines)
        source, catalog, _ = civic.configuration(PROJECT, self.world, [], {'hawaii_royal_center': ('pacific', {})}, [])
        medical.verify_registration(PROJECT, self.world, source, catalog)
        self.assertEqual(set(), medical.verified_bindings(PROJECT))

    def test_generation_rejects_changed_unlock_prerequisites_years_or_rules(self):
        for node_id in ('civic_pest_hospitals', 'clinical_case_records'):
            for field, value in [('unlocks', []), ('prerequisiteIds', []), ('timeCost', {'preferredYear': 1450})]:
                world = copy.deepcopy(self.world)
                next(n for n in world['technologies'] if n['id'] == node_id)[field] = value
                with self.assertRaisesRegex(ValueError, 'exact typed'):
                    medical.configuration(PROJECT, world)
        for mutate in (lambda d: d['rules'].update(recordsDailyMoney=0),
                       lambda d: d['rules'].update(careUpkeepBasisPoints=True),
                       lambda d: d['effects'].append(d['effects'][0]),
                       lambda d: d['effects'][1].update(bonusBasisPoints=501),
                       lambda d: d.update(recordsGood='grain')):
            invalid = copy.deepcopy(self.contract)
            mutate(invalid)
            original = Path.read_text
            def read(path, *args, **kwargs):
                return json.dumps(invalid) if path.name == 'medical-care.json' else original(path, *args, **kwargs)
            with patch.object(Path, 'read_text', read), self.assertRaises(ValueError):
                medical.configuration(PROJECT, self.world)

    def test_campaign_without_medical_contract_accepts_absence_but_rejects_unauthored_care(self):
        project = PROJECT.parent / 'conformance-campaign'
        world = json.loads((project / 'scenario/world/world.json').read_text())
        source, catalog, _ = civic.configuration(project, world, [], {}, [])
        self.assertEqual({}, catalog)
        medical.verify_registration(project, world, source, catalog)
        medical.verify_registration(project, world, source, {'medicalCare': {}})
        for metadata in (None, {'consumers': []}, {'consumers': ['unauthored']}):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                medical.verify_registration(project, world, source, {'medicalCare': metadata})
        for effect in self.contract['effects']:
            with self.subTest(effect=effect['nodeId']):
                with self.assertRaises(ValueError):
                    medical.verify_registration(project, world, source, {'effects': [effect]})
                registration = (f'\tresearch.register(new CivicEffect("modifier", '
                                f'"{effect["unlock"]["contentId"]}", '
                                f'"{effect["metric"]}", 500))\n')
                with self.assertRaises(ValueError):
                    medical.verify_registration(project, world, source + registration, catalog)
        with self.assertRaises(ValueError):
            medical.verify_registration(project, world, source + '\tledger.recordsDailyMoney = 1\n', catalog)

    def test_resealed_generated_metadata_or_registration_cannot_substitute_consumers(self):
        source, catalog, _ = civic.configuration(PROJECT, self.world, [], {'hawaii_royal_center': ('pacific', {})}, [])
        for damaged in (source.replace('ledger.recordsDailyMoney = 1', 'ledger.recordsDailyMoney = 0'),
                        source.replace('"isolation_care_losses_avoided", 500', '"isolation_care_losses_avoided", 600'),
                        source + '\tledger.carePreparationDays = 90\n'):
            with self.assertRaises(ValueError):
                medical.verify_registration(PROJECT, self.world, damaged, catalog)
        for mutate in (lambda d: d.pop('medicalCare'),
                       lambda d: d['medicalCare']['consumers'].pop(),
                       lambda d: d['medicalCare']['consumers'][0].update(contentId='progression_clinical_case_records')):
            invalid = copy.deepcopy(catalog)
            mutate(invalid)
            with self.assertRaises(ValueError):
                medical.verify_registration(PROJECT, self.world, source, invalid)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(([], [], {}, []), medical.configuration(Path(tmp), {}))


class MedicalCareEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.revision = 'a' * 40
        cls.contract = evidence.load_contract(PROJECT)
        cls.sources = evidence.execution_sources(PROJECT)
        cls.expected = execution.discover(PROJECT, sources=cls.sources)
        cls.identity = evidence.source_identity(PROJECT, cls.revision)
        cls.inputs = {}
        for relative, source in cls.sources.items():
            probes = {k: v for k, v in cls.contract['probes'].items() if v['path'] == relative}
            cls.inputs[relative] = evidence.digest(evidence.instrument(source.read_text(), probes).encode()
                                                  if probes else source.read_bytes())
        for name in ('wurst.build', 'wurst_run.args'):
            cls.inputs[name] = evidence.digest((PROJECT / name).read_bytes())

    def transcript(self, pairs=None, omit_probe=None, failed=None, omitted=None, disconnected=False):
        pairs = set(medical.IDENTITIES) if pairs is None else pairs
        expected = [row for row in self.expected if row['id'] != omitted]
        lines = ['Running tests']
        for row in expected:
            path, name = row['id'].rsplit(':', 1)
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            probes = set()
            for pair in pairs:
                system, comparison, probe = medical.COMPARISONS[pair]
                if row['id'] == PREFIX + comparison and not disconnected:
                    probes |= medical.COMMON_PROBES | {probe}
                if disconnected and name == 'medicalFractionalCompositionDeduplicatesDaysAndSources':
                    probes |= medical.COMMON_PROBES | {probe}
            lines.extend('WCM_PROBE:' + p for p in sorted(probes - {omit_probe}))
            lines.append('FAILED assertion: synthetic failure' if row['id'] == failed else '\tOK!')
        lines += [f'Tests succeeded: {len(expected)}/{len(expected)}', 'Finished running tests']
        log = ('\n'.join(lines) + '\n').encode()
        rows, errors = execution.parse_results(log.decode(), expected)
        report = dict(format=execution.FORMAT, status='fail' if errors else 'pass',
                      executionStatus='completed', sourceRevision=self.revision,
                      sourceIdentity=self.identity, expected=expected, tests=rows,
                      errors=errors, returnCode=0, inputs=copy.deepcopy(self.inputs),
                      inputSetSha256=evidence.digest(evidence.canonical(self.inputs)),
                      logSha256=evidence.digest(log), discovered=len(rows), succeeded=len(rows),
                      compiler={'sha256': execution.PINNED_COMPILER_SHA256},
                      productionCoverage={'contractSha256': evidence.digest(evidence.canonical(self.contract)),
                                          'tests': evidence.observed_probes(log.decode(), rows, self.contract)})
        return report, log

    def bindings(self, report=None, log=None):
        return medical.verified_bindings(PROJECT, report, log, self.revision)

    def test_each_identity_requires_its_own_comparison(self):
        for pair in medical.IDENTITIES:
            report, log = self.transcript(pairs={pair})
            self.assertEqual({pair}, self.bindings(report, log))
        report, log = self.transcript()
        self.assertEqual(set(medical.IDENTITIES), self.bindings(report, log))
        before = {r['id'] for r in release._audit_research_bindings()}
        after = {r['id'] for r in release._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({
            'RESEARCH-UNBOUND-CIVIC-PEST-HOSPITALS-MODIFIER-PROGRESSION-CIVIC-PEST-HOSPITALS',
            'RESEARCH-UNBOUND-CLINICAL-CASE-RECORDS-MODIFIER-PROGRESSION-CLINICAL-CASE-RECORDS'}, before - after)
        self.assertFalse(after - before)

    def test_absent_focused_stale_tampered_and_failed_evidence_rejects(self):
        self.assertEqual(set(), self.bindings())
        report, log = self.transcript()
        for field, value in [('status', 'fail'), ('executionStatus', 'not_run'), ('sourceRevision', 'b' * 40),
                             ('sourceIdentity', {}), ('compiler', {'sha256': '0' * 64}),
                             ('logSha256', '0' * 64), ('productionCoverage', {}),
                             ('expected', report['expected'][:-1]), ('returnCode', 1)]:
            invalid = copy.deepcopy(report)
            invalid[field] = value
            self.assertEqual(set(), self.bindings(invalid, log), field)
        self.assertEqual(set(), self.bindings(report, log + b'tampered\n'))
        report, log = self.transcript(omitted=self.expected[0]['id'])
        self.assertEqual(set(), self.bindings(report, log))
        for name in medical.REQUIRED_TESTS | {v[1] for v in medical.COMPARISONS.values()}:
            report, log = self.transcript(failed=PREFIX + name)
            self.assertEqual(set(), self.bindings(report, log), name)
        report, log = self.transcript(failed=medical.ROLLBACK)
        self.assertEqual(set(), self.bindings(report, log))

    def test_unrelated_traces_and_missing_payment_disease_or_persistence_probes_reject(self):
        for probe in medical.COMMON_PROBES:
            report, log = self.transcript(omit_probe=probe)
            self.assertEqual(set(), self.bindings(report, log), probe)
        for pair, (system, name, probe) in medical.COMPARISONS.items():
            self.assertEqual(medical.COMMON_PROBES | {probe}, set(self.contract['systems'][system]))
            report, log = self.transcript(omit_probe=probe)
            self.assertEqual(set(medical.IDENTITIES) - {pair}, self.bindings(report, log))
        report, log = self.transcript(disconnected=True)
        self.assertEqual(set(), self.bindings(report, log))


if __name__ == '__main__':
    unittest.main()
