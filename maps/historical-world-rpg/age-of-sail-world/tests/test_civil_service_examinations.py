"""Exact generation and synthetic evidence rejection; never release evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
import administrative_governance as admin
import integration_evidence as evidence
import release_blocker_audit as audit
import wurst_execution as execution
from package_wurst_map import generate, load_config, verify_generated, PackagingError

PAIR = ('modifier', 'progression_civil_service_examinations')
FINDING = 'RESEARCH-UNBOUND-CIVIL-SERVICE-EXAMINATIONS-MODIFIER-PROGRESSION-CIVIL-SERVICE-EXAMINATIONS'
PREFIX = 'wurst/CivicGovernanceTests.wurst:'


class ExaminationsGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.generated = Path(cls.temp.name)
        cls.config = load_config(PROJECT / 'package.json')
        generate(cls.config, cls.generated)
        cls.source = (cls.generated / 'ScenarioData.wurst').read_text()
        cls.runtime = json.loads((cls.generated / 'scenario-runtime.json').read_text())
        cls.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())

    def test_exact_generated_registration_metadata_and_historical_prerequisites(self):
        admin.verify_registration(PROJECT, self.world, self.source, self.runtime['civicGovernance'])
        effects = self.runtime['civicGovernance']['effects']
        self.assertEqual([admin.EXAMINATIONS_EFFECT], [e for e in effects if e['nodeId'] == 'civil_service_examinations'])
        self.assertNotIn(PAIR, {(e['kind'], e['contentId']) for e in self.runtime['researchIntegrationBlockers']})
        node = next(n for n in self.world['technologies'] if n['id'] == 'civil_service_examinations')
        self.assertEqual(['provincial_audits', 'fleet_victualling'], node['prerequisiteIds'])
        self.assertEqual(1650, node['timeCost']['preferredYear'])
        self.assertIn('ledger.archiveUpkeepBasisPoints = 25', self.source)
        self.assertIn('ledger.minimumAdministration = 40', self.source)
        verify_generated(self.config, self.generated)

    def test_changed_duplicated_missing_or_substituted_executable_and_metadata_reject(self):
        call = '\tresearch.register(new CivicEffect("modifier", "progression_civil_service_examinations", "records_tax_collection_efficiency", 500))'
        for replacement in ('', call + '\n' + call, call.replace('500', '499'),
                            call.replace('modifier', 'policy'), call.replace('records_tax', 'archive_tax')):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                admin.verify_registration(PROJECT, self.world, self.source.replace(call, replacement), self.runtime['civicGovernance'])
        catalog = copy.deepcopy(self.runtime['civicGovernance'])
        # Select by identity rather than trusting effect order.
        next(e for e in catalog['effects'] if e['nodeId'] == 'civil_service_examinations')['bonusBasisPoints'] = 499
        with self.assertRaises(ValueError):
            admin.verify_registration(PROJECT, self.world, self.source, catalog)
        # Rehashing generated files cannot legitimize disconnected code/metadata.
        import hashlib
        data_path = self.generated / 'ScenarioData.wurst'
        # The production provenance filename is supplied by the packager.
        from package_wurst_map import PROVENANCE
        provenance_path = self.generated / PROVENANCE
        original = data_path.read_bytes()
        provenance = provenance_path.read_bytes()
        try:
            data_path.write_text(self.source.replace(call, call.replace('500', '499')))
            resealed = json.loads(provenance)
            resealed['outputs']['ScenarioData.wurst'] = hashlib.sha256(data_path.read_bytes()).hexdigest()
            provenance_path.write_text(json.dumps(resealed))
            with self.assertRaises(PackagingError):
                verify_generated(self.config, self.generated)
        finally:
            data_path.write_bytes(original)
            provenance_path.write_bytes(provenance)


class ExaminationsEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.revision = 'a' * 40
        cls.contract = evidence.load_contract(PROJECT)
        cls.sources = evidence.execution_sources(PROJECT)
        cls.expected = execution.discover(PROJECT, sources=cls.sources)
        cls.inputs = {}
        for relative, source in cls.sources.items():
            probes = {k: v for k, v in cls.contract['probes'].items() if v['path'] == relative}
            cls.inputs[relative] = evidence.digest(evidence.instrument(source.read_text(), probes).encode()
                                                  if probes else source.read_bytes())
        for name in ('wurst.build', 'wurst_run.args'):
            cls.inputs[name] = evidence.digest((PROJECT / name).read_bytes())

    def transcript(self, omitted=None, failed=None):
        lines = ['Running tests']
        for row in self.expected:
            path, name = row['id'].split(':')
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            system = None
            if name == admin.EXAMINATIONS_COMPARISON:
                system = 'civil_service_examinations'
            elif name == 'administrativeRegisteredArchivesThenAdoptionAndMunicipalPolicyProduceConservedTaxDifferences':
                system = 'administrative_contracts'
            if system:
                lines.extend('WCM_PROBE:' + p for p in self.contract['systems'][system]
                             if p != omitted or system != 'civil_service_examinations')
            lines.append('FAILED assertion: synthetic failure' if row['id'] == failed else '\tOK!')
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
        return admin.verified_bindings(PROJECT, report, log, self.revision)

    def test_complete_same_revision_protocol_recognizes_exact_consumer_and_audit_identity(self):
        report, log = self.transcript()
        self.assertIn(PAIR, self.bindings(report, log))
        before = {r['id'] for r in audit._audit_research_bindings()}
        after = {r['id'] for r in audit._audit_research_bindings(execution=report, execution_log=log, revision=self.revision)}
        self.assertIn(FINDING, before - after)
        self.assertFalse(after - before)
        self.assertIn(FINDING, {r['id'] for r in audit._audit_research_bindings()})

    def test_missing_stale_focused_incomplete_or_tampered_execution_fails_closed(self):
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
        invalid['inputs']['wurst/CivicGovernance.wurst'] = '0' * 64
        invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
        self.assertEqual(set(), self.bindings(invalid, log))

    def test_each_actual_comparison_probe_including_collection_is_required(self):
        for probe in admin.EXAMINATIONS_PROBES:
            with self.subTest(probe=probe):
                report, log = self.transcript(omitted=probe)
                self.assertNotIn(PAIR, self.bindings(report, log))
                report['productionCoverage']['tests'][PREFIX + admin.EXAMINATIONS_COMPARISON].append(probe)
                self.assertEqual(set(), self.bindings(report, log))

    def test_archive_comparison_cannot_substitute_for_examinations(self):
        report, log = self.transcript()
        coverage = evidence.verify_execution_coverage(report, log, PROJECT, self.revision)
        coverage['civil_service_examinations'] = coverage['administrative_contracts']
        with patch.object(evidence, 'verify_execution_coverage', return_value=coverage):
            self.assertNotIn(PAIR, self.bindings(report, log))

    def test_every_negative_parity_migration_and_rollback_test_is_required(self):
        for name in {PREFIX + n for n in admin.REQUIRED_TESTS | admin.EXAMINATIONS_REQUIRED_TESTS} | {admin.EXAMINATIONS_ROLLBACK}:
            with self.subTest(name=name):
                report, log = self.transcript(failed=name)
                self.assertNotIn(PAIR, self.bindings(report, log))

    def test_changed_authored_identity_metric_bonus_bill_or_threshold_cannot_close(self):
        report, log = self.transcript()
        world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        lines, effects, urban, sources = admin.configuration(PROJECT, world)
        for field, value in [('nodeId', 'other'), ('metric', 'archive_tax_collection_efficiency'),
                             ('bonusBasisPoints', 499), ('kind', 'policy'), ('contentId', 'other')]:
            altered = copy.deepcopy(effects)
            target = altered[2]['unlock'] if field in {'kind', 'contentId'} else altered[2]
            target[field] = value
            with self.subTest(field=field), patch.object(admin, 'configuration', return_value=(lines, altered, urban, sources)):
                self.assertNotIn(PAIR, self.bindings(report, log))
        for field in ('archiveUpkeepBasisPoints = 25', 'minimumAdministration = 40'):
            altered = [line.replace(field, field[:-2] + '99') for line in lines]
            with self.subTest(rule=field), patch.object(admin, 'configuration', return_value=(altered, effects, urban, sources)):
                self.assertNotIn(PAIR, self.bindings(report, log))


if __name__ == '__main__':
    unittest.main()
