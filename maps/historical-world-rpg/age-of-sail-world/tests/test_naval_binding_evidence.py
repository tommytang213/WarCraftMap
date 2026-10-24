"""Synthetic protocol regressions; these logs are never commissioning evidence."""
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
import naval_commissioning as verifier
import naval_services_catalog as naval
import release_blocker_audit as audit

PREFIX = 'wurst/NavalServicesTests.wurst:'
COMPARISON = PREFIX + verifier.COMPARISON
BINDING = ('unit', 'ship_of_the_line')
FINDING = 'RESEARCH-UNBOUND-BATTLEFLEET-DOCTRINE-UNIT-SHIP-OF-THE-LINE'


class NavalBindingEvidenceTests(unittest.TestCase):
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

    def transcript(self, omit_probe=None, fail_test=None, omitted_test=None, comparison=True):
        expected = [row for row in self.expected if row['id'] != omitted_test]
        lines = ['Running tests']
        for row in expected:
            path, name = row['id'].rsplit(':', 1)
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            probes = verifier.PROBES - {omit_probe} if row['id'] == COMPARISON and comparison else set()
            # A sibling test exercising every probe cannot replace the comparison.
            if row['id'] == PREFIX + 'navalProductionConsumerTraceExercisesAllFourRegisteredBenefitsOnOneRevision':
                probes = verifier.PROBES
            lines.extend('WCM_PROBE:' + probe for probe in sorted(probes))
            lines.append('FAILED assertion: synthetic failure' if row['id'] == fail_test else '\tOK!')
        lines += [f'Tests succeeded: {len(expected)}/{len(expected)}', 'Finished running tests']
        log = ('\n'.join(lines) + '\n').encode()
        rows, errors = execution.parse_results(log.decode(), expected)
        return dict(format=execution.FORMAT, status='fail' if errors else 'pass',
                    executionStatus='completed', sourceRevision=self.revision,
                    sourceIdentity=self.identity, expected=expected, tests=rows,
                    errors=errors, returnCode=0, inputs=copy.deepcopy(self.inputs),
                    inputSetSha256=evidence.digest(evidence.canonical(self.inputs)),
                    logSha256=evidence.digest(log), discovered=len(rows), succeeded=len(rows),
                    compiler={'sha256': execution.PINNED_COMPILER_SHA256},
                    productionCoverage={'contractSha256': evidence.digest(evidence.canonical(self.contract)),
                                        'tests': evidence.observed_probes(log.decode(), rows, self.contract)}), log

    def bindings(self, report=None, log=None):
        return naval.verified_bindings(PROJECT, report, log, self.revision)

    def test_only_exact_doctrine_finding_disappears(self):
        report, log = self.transcript()
        self.assertEqual({BINDING}, self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({FINDING}, before - after)
        self.assertFalse(after - before)
        for sibling in ('CAREENING-STATIONS', 'CARRONADE-BATTERIES', 'CARVEL-HULL-CONSTRUCTION'):
            self.assertTrue(any(sibling in name for name in after))

    def test_missing_stale_focused_failed_and_tampered_evidence_rejects(self):
        report, log = self.transcript()
        self.assertEqual(set(), self.bindings())
        for field, value in [('status', 'fail'), ('executionStatus', 'not_run'),
                             ('sourceRevision', 'b' * 40), ('sourceIdentity', {}),
                             ('compiler', {'sha256': '0' * 64}), ('logSha256', '0' * 64),
                             ('inputSetSha256', '0' * 64), ('productionCoverage', {}),
                             ('expected', report['expected'][:-1]), ('returnCode', 1)]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(report)
                invalid[field] = value
                self.assertEqual(set(), self.bindings(invalid, log))
        self.assertEqual(set(), self.bindings(report, log + b'tampered\n'))
        report, log = self.transcript(omitted_test=self.expected[0]['id'])
        self.assertEqual(set(), self.bindings(report, log))
        for name in verifier.REQUIRED_TESTS:
            with self.subTest(test=name):
                report, log = self.transcript(fail_test=PREFIX + name)
                self.assertEqual(set(), self.bindings(report, log))

    def test_payment_work_completion_and_persistence_must_execute_in_comparison(self):
        self.assertEqual(verifier.PROBES, set(self.contract['systems']['naval_commissioning']))
        for probe in verifier.PROBES:
            with self.subTest(probe=probe):
                report, log = self.transcript(omit_probe=probe)
                self.assertEqual(set(), self.bindings(report, log))
                report['productionCoverage']['tests'][COMPARISON].append(probe)
                self.assertEqual(set(), self.bindings(report, log))
        report, log = self.transcript(comparison=False)
        self.assertEqual(set(), self.bindings(report, log))

    def test_current_production_inputs_and_source_digest_are_required(self):
        report, log = self.transcript()
        for relative in ('wurst/NavalServices.wurst', 'wurst/NavalCampaignRuntime.wurst',
                         'wurst/MilitarySettlementRuntime.wurst', 'wurst/NavalServicesTests.wurst'):
            invalid = copy.deepcopy(report)
            invalid['inputs'][relative] = '0' * 64
            invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
            self.assertEqual(set(), self.bindings(invalid, log))
        original = Path.read_text
        source = self.sources['wurst/NavalCampaignRuntime.wurst']
        def disconnected(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text.replace('s.manpower -= crew', 'skip') if path == source else text
        with patch.object(Path, 'read_text', disconnected):
            self.assertEqual(set(), self.bindings(report, log))

    def test_altered_typed_entitlement_recipient_and_roster_mapping_reject(self):
        report, log = self.transcript()
        original = Path.read_text
        design = PROJECT / 'scenario/progression/gameplay-effect-design.json'
        mutations = [lambda e: e['unlock'].update(kind='policy'),
                     lambda e: e['unlock'].update(contentId='other_ship'),
                     lambda e: e.update(nodeId='rated_warships'),
                     lambda e: e.update(metric='merchant_unlock_recruitment'),
                     lambda e: e.update(bonusBasisPoints=1),
                     lambda e: e.update(bonusBasisPoints=0.0),
                     lambda e: e.update(recipient='all_ships'),
                     lambda e: e.update(activation='passive_research')]
        for mutation in mutations:
            data = json.loads(original(design))
            mutation(next(e for e in data['effects'] if e['nodeId'] == 'battlefleet_doctrine'))
            def changed(path, *args, **kwargs):
                return json.dumps(data) if path == design else original(path, *args, **kwargs)
            with self.subTest(mutation=mutation), patch.object(Path, 'read_text', changed):
                self.assertEqual(set(), self.bindings(report, log))
        services = PROJECT / 'scenario/naval/services.json'
        data = json.loads(original(services))
        data['blueprint'] = 'british_ship_of_line'
        def remapped(path, *args, **kwargs):
            return json.dumps(data) if path == services else original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', remapped):
            self.assertEqual(set(), self.bindings(report, log))
        world_path = PROJECT / 'scenario/world/world.json'
        world = json.loads(original(world_path))
        next(n for n in world['technologies'] if n['id'] == 'battlefleet_doctrine')['unlocks'] = []
        def unearned(path, *args, **kwargs):
            return json.dumps(world) if path == world_path else original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', unearned):
            self.assertEqual(set(), self.bindings(report, log))

    def test_generated_consumer_derives_scenario_and_roster_bills(self):
        data, _ = naval.build(PROJECT)
        consumer, = data['consumers']
        self.assertEqual('battlefleet_doctrine', consumer['nodeId'])
        self.assertEqual('ship_of_the_line_generic', consumer['rosterId'])
        self.assertEqual(BINDING, (consumer['kind'], consumer['contentId']))
        self.assertEqual((1540, 700, 78, 40, 20, 180, 98), tuple(consumer[k] for k in
                         ('currency', 'manpower', 'provisions', 'timber', 'iron', 'constructionDays', 'upkeep')))
        changed = copy.deepcopy(data)
        changed['rosterBlueprint'].update(cost=1600, supply=80, upkeep=100)
        changed['crewStrength'] = 710
        changed['rules'].update(buildWood=45, buildIron=25)
        changed['constructionDays'] = 190
        derived, = naval.commissioning_consumers(changed)
        self.assertEqual((1600, 710, 80, 45, 25, 190, 100), tuple(derived[k] for k in
                         ('currency', 'manpower', 'provisions', 'timber', 'iron', 'constructionDays', 'upkeep')))
        self.assertEqual(data['rosterBlueprint']['availability'], consumer['availability'])
        self.assertTrue(consumer['boardRequired'])
        self.assertIn('public_credit', consumer['requiredResearch'])
        # None of the other registered effects is a closure candidate.
        self.assertEqual(1, len(data['consumers']))


if __name__ == '__main__':
    unittest.main()
