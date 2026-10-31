"""Generated contracts and synthetic evidence rejection; no release evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
import local_revenue as revenue
import integration_evidence as evidence
import release_blocker_audit as audit
import wurst_execution as execution
from package_wurst_map import generate, load_config, verify_generated, PackagingError, PROVENANCE

PREFIX = 'wurst/LocalRevenueTests.wurst:'


class LocalRevenueGenerationTests(unittest.TestCase):
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

    def test_exact_identities_requirements_network_and_metadata(self):
        revenue.verify_registration(PROJECT, self.world, self.source, self.runtime['civicGovernance'])
        verify_generated(self.config, self.generated)
        blocked = {(e['kind'], e['contentId']) for e in self.runtime['researchIntegrationBlockers']}
        self.assertFalse(set(revenue.COMPARISONS) & blocked)
        council = next(n for n in self.world['institutions'] if n['id'] == 'colonial_councils')
        self.assertEqual(['chancery_archives'], council['prerequisiteIds'])
        for line in ('councilMinimumUrbanization = 16', 'councilTransitionDays = 90',
                     'councilEnactmentBasisPoints = 100', 'councilUpkeepBasisPoints = 50'):
            self.assertIn('ledger.' + line, self.source)
        self.assertEqual([('lisbon', 'goa'), ('goa', 'malacca')],
                         [(x['originId'], x['recipientId']) for x in self.runtime['civicGovernance']['councilConnections']])
        _, effects, _, _ = revenue.configuration(PROJECT, self.world)
        self.assertEqual([(x[2], x[3], x[4]) for x in revenue.COMPARISONS.values()],
                         [(e['nodeId'], e['metric'], e['bonusBasisPoints']) for e in effects])

    def test_changed_missing_duplicate_resealed_or_substituted_generation_rejects(self):
        lines, effects, _, _ = revenue.configuration(PROJECT, self.world)
        calls = [f'\tresearch.register(new CivicEffect({json.dumps(e["unlock"]["kind"])}, '
                 f'{json.dumps(e["unlock"]["contentId"])}, {json.dumps(e["metric"])}, '
                 f'{e["bonusBasisPoints"]}))' for e in effects]
        for call in lines + calls:
            for replacement in ('', call + '\n' + call, call.replace('500', '499').replace('400', '399') + ' // altered'):
                with self.subTest(call=call), self.assertRaises(ValueError):
                    revenue.verify_registration(PROJECT, self.world, self.source.replace(call, replacement),
                                                self.runtime['civicGovernance'])
        for key in ('effects', 'councilConnections'):
            broken = copy.deepcopy(self.runtime['civicGovernance'])
            broken[key] = []
            with self.assertRaises(ValueError):
                revenue.verify_registration(PROJECT, self.world, self.source, broken)
        source_path = self.generated / 'ScenarioData.wurst'
        provenance_path = self.generated / PROVENANCE
        original = source_path.read_bytes()
        original_provenance = provenance_path.read_bytes()
        try:
            source_path.write_text(self.source.replace('ledger.councilMinimumUrbanization = 16',
                                                      'ledger.councilMinimumUrbanization = 15'))
            provenance = json.loads(original_provenance)
            provenance['outputs']['ScenarioData.wurst'] = hashlib.sha256(source_path.read_bytes()).hexdigest()
            provenance_path.write_text(json.dumps(provenance))
            with self.assertRaises(PackagingError):
                verify_generated(self.config, self.generated)
        finally:
            source_path.write_bytes(original)
            provenance_path.write_bytes(original_provenance)

    def test_invalid_connections_and_lost_catalogue_requirements_fail_before_generation(self):
        # Patch reads of this one scenario file; all geography remains real data.
        source = PROJECT / 'scenario/progression/local-revenue-contracts.json'
        data = json.loads(source.read_text())
        read = Path.read_text
        mutations = [lambda d: d['connections'].append(d['connections'][0]),
                     lambda d: d['connections'][0].update(recipientId='unknown'),
                     lambda d: d['connections'][0].update(recipientId='london'),
                     lambda d: d['connections'][0].update(evidenceIds=['invented']),
                     lambda d: d['effects'][0]['unlock'].update(kind='policy'),
                     lambda d: d['rules'].update(councilUpkeepBasisPoints=0)]
        for mutate in mutations:
            broken = copy.deepcopy(data)
            mutate(broken)
            def altered(path, *args, **kwargs):
                return json.dumps(broken) if path == source else read(path, *args, **kwargs)
            with patch.object(Path, 'read_text', altered), self.assertRaises(ValueError):
                revenue.configuration(PROJECT, self.world)
        broken_world = copy.deepcopy(self.world)
        next(n for n in broken_world['institutions'] if n['id'] == 'colonial_councils')['prerequisiteIds'] = []
        with self.assertRaisesRegex(ValueError, 'catalogue'):
            revenue.configuration(PROJECT, broken_world)


class LocalRevenueEvidenceTests(unittest.TestCase):
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
        comparisons = {test: system for system, test, _, _, _ in revenue.COMPARISONS.values()}
        for row in self.expected:
            path, name = row['id'].split(':')
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            if name in comparisons:
                system = comparisons[name]
                lines.extend('WCM_PROBE:' + p for p in self.contract['systems'][system]
                             if omitted != (system, p))
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
        return revenue.verified_bindings(PROJECT, report, log, self.revision)

    def test_only_own_verified_evidence_removes_each_exact_finding(self):
        report, log = self.transcript()
        self.assertEqual(set(revenue.COMPARISONS), self.bindings(report, log))
        before = {r['id'] for r in audit._audit_research_bindings()}
        after = {r['id'] for r in audit._audit_research_bindings(execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({
            'RESEARCH-UNBOUND-CODIFIED-LAW-MODIFIER-PROGRESSION-CODIFIED-LAW',
            'RESEARCH-UNBOUND-COLONIAL-COUNCILS-POLICY-PROGRESSION-COLONIAL-COUNCILS',
        }, before - after)
        self.assertFalse(after - before)

    def test_stale_focused_failed_tampered_missing_and_changed_inputs_fail_closed(self):
        report, log = self.transcript()
        self.assertEqual(set(), self.bindings())
        for key, value in [('status', 'fail'), ('executionStatus', 'not_run'),
                           ('sourceRevision', 'b' * 40), ('sourceIdentity', {}),
                           ('compiler', {'sha256': '0' * 64}), ('logSha256', '0' * 64),
                           ('inputSetSha256', '0' * 64), ('productionCoverage', {}),
                           ('expected', report['expected'][:-1])]:
            invalid = copy.deepcopy(report)
            invalid[key] = value
            with self.subTest(key=key):
                self.assertEqual(set(), self.bindings(invalid, log))
        self.assertEqual(set(), self.bindings(report, log + b'tampered\n'))
        invalid = copy.deepcopy(report)
        invalid['inputs']['wurst/CivicGovernance.wurst'] = '0' * 64
        invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
        self.assertEqual(set(), self.bindings(invalid, log))
        for name in {PREFIX + n for n in revenue.REQUIRED_TESTS} | {revenue.ROLLBACK}:
            with self.subTest(failed=name):
                invalid, bad_log = self.transcript(failed=name)
                self.assertEqual(set(), self.bindings(invalid, bad_log))

    def test_each_identity_needs_its_own_calls_and_comparison(self):
        for pair, (system, test, _, _, _) in revenue.COMPARISONS.items():
            probes = revenue.COUNCIL_PROBES if system == 'colonial_councils' else revenue.PROBES
            for probe in probes:
                report, log = self.transcript(omitted=(system, probe))
                with self.subTest(system=system, probe=probe):
                    self.assertEqual(set(revenue.COMPARISONS) - {pair}, self.bindings(report, log))
                    report['productionCoverage']['tests'][PREFIX + test].append(probe)
                    self.assertEqual(set(), self.bindings(report, log))
            report, log = self.transcript()
            coverage = evidence.verify_execution_coverage(report, log, PROJECT, self.revision)
            coverage[system] = ['wurst/CivicGovernanceTests.wurst:examinationsRegisteredResearchMatchedControlCollectsFundedLocalRevenue']
            with patch.object(evidence, 'verify_execution_coverage', return_value=coverage):
                self.assertEqual(set(revenue.COMPARISONS) - {pair}, self.bindings(report, log))

    def test_changed_typed_contract_or_policy_bills_cannot_close(self):
        report, log = self.transcript()
        world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        lines, effects, connections, sources = revenue.configuration(PROJECT, world)
        for i, pair in enumerate(revenue.COMPARISONS):
            for field, value in [('nodeId', 'other'), ('metric', 'archive_tax_collection_efficiency'),
                                 ('bonusBasisPoints', 499), ('kind', 'ability'), ('contentId', 'other')]:
                altered = copy.deepcopy(effects)
                target = altered[i]['unlock'] if field in {'kind', 'contentId'} else altered[i]
                target[field] = value
                with self.subTest(pair=pair, field=field), patch.object(revenue, 'configuration', return_value=(lines, altered, connections, sources)):
                    self.assertNotIn(pair, self.bindings(report, log))
        for line in lines[:5]:
            altered = [x for x in lines if x != line]
            with patch.object(revenue, 'configuration', return_value=(altered, effects, connections, sources)):
                self.assertEqual(set(), self.bindings(report, log))


if __name__ == '__main__':
    unittest.main()
