"""Synthetic protocol regressions; these logs are never combat execution evidence."""
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
import naval_carronade as verifier
import naval_services_catalog as naval
import release_blocker_audit as audit

PREFIX = 'wurst/NavalServicesTests.wurst:'
COMPARISON = PREFIX + verifier.COMPARISON
BINDING = ('modifier', 'progression_carronade_batteries')
FINDING = 'RESEARCH-UNBOUND-CARRONADE-BATTERIES-MODIFIER-PROGRESSION-CARRONADE-BATTERIES'


class CarronadeBindingEvidenceTests(unittest.TestCase):
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

    def transcript(self, omit_probe=None, fail_test=None, omitted_test=None, comparison=True,
                   include_commissioning=False, include_repairs=False):
        comparative = COMPARISON
        expected = [row for row in self.expected if row['id'] != omitted_test]
        lines = ['Running tests']
        for row in expected:
            path, name = row['id'].rsplit(':', 1)
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            probes = verifier.PROBES - {omit_probe} if row['id'] == comparative and comparison else set()
            if include_commissioning:
                import naval_commissioning
                if row['id'] == PREFIX + naval_commissioning.COMPARISON:
                    probes = naval_commissioning.PROBES
            if include_repairs:
                import naval_repair
                if row['id'] == PREFIX + naval_repair.COMPARISON:
                    probes = naval_repair.PROBES
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

    def test_only_exact_carronade_finding_disappears(self):
        report, log = self.transcript()
        self.assertEqual({BINDING}, self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({FINDING}, before - after)
        self.assertFalse(after - before)
        for sibling in ('CAREENING-STATIONS', 'BATTLEFLEET-DOCTRINE', 'CARVEL-HULL-CONSTRUCTION'):
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

    def test_research_mounting_and_both_damage_paths_must_execute_in_comparison(self):
        self.assertEqual(verifier.PROBES, set(self.contract['systems']['naval_carronade']))
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
                         'wurst/MilitarySettlementRuntime.wurst', 'wurst/MilitaryCombatEvents.wurst',
                         'wurst/CombatEffects.wurst', 'wurst/NavalServicesTests.wurst'):
            invalid = copy.deepcopy(report)
            invalid['inputs'][relative] = '0' * 64
            invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
            self.assertEqual(set(), self.bindings(invalid, log))
        original = Path.read_text
        source = self.sources['wurst/NavalCampaignRuntime.wurst']
        def disconnected(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text.replace('f.hull.installCarronades()', 'skip') if path == source else text
        with patch.object(Path, 'read_text', disconnected):
            self.assertEqual(set(), self.bindings(report, log))

    def test_commissioning_remains_independent_when_both_comparisons_execute(self):
        report, log = self.transcript(include_commissioning=True)
        self.assertEqual({BINDING, ('unit', 'ship_of_the_line')}, self.bindings(report, log))
        report, log = self.transcript(include_commissioning=True, comparison=False)
        self.assertEqual({('unit', 'ship_of_the_line')}, self.bindings(report, log))

    def test_integrated_naval_consumers_require_their_own_comparisons(self):
        for carronades in (False, True):
            for commissioning in (False, True):
                for repairs in (False, True):
                    with self.subTest(carronades=carronades, commissioning=commissioning, repairs=repairs):
                        report, log = self.transcript(comparison=carronades,
                                                      include_commissioning=commissioning,
                                                      include_repairs=repairs)
                        expected = set()
                        if carronades:
                            expected.add(BINDING)
                        if commissioning:
                            expected.add(('unit', 'ship_of_the_line'))
                        if repairs:
                            expected.add(('modifier', 'progression_careening_stations'))
                        self.assertEqual(expected, self.bindings(report, log))

    def test_missing_contract_fields_reject(self):
        data, _ = naval.build(PROJECT)
        for field in ('nodeId', 'unlock', 'metric', 'bonusBasisPoints', 'family', 'activation', 'recipient'):
            changed = copy.deepcopy(data)
            del next(e for e in changed['effects'] if e['nodeId'] == 'carronade_batteries')[field]
            with self.subTest(field=field):
                self.assertEqual([], naval.carronade_consumers(changed))

    def test_exact_generated_metadata_and_ambiguous_contracts_fail_closed(self):
        data, _ = naval.build(PROJECT)
        consumer, = data['combatConsumers']
        self.assertEqual(BINDING, (consumer['kind'], consumer['contentId']))
        self.assertEqual(('carronade_batteries', 'close_range_naval_gunfire_damage', 1000,
                          200, 2, 10, 7, 300, '1780-01-01'), tuple(consumer[k] for k in
                         ('nodeId', 'metric', 'bonusBasisPoints', 'currency', 'timber', 'iron',
                          'mountingDays', 'maximumRange', 'firstDate')))
        self.assertEqual(data['carronadeMountProfiles'], consumer['profiles'])
        self.assertTrue(consumer['currentControllerResearch'])
        self.assertTrue(consumer['fundedMaintenance'])
        for key, value in [('nodeId', 'careening_stations'), ('family', 'land'),
                           ('metric', 'hull_repair_throughput'), ('bonusBasisPoints', 999),
                           ('bonusBasisPoints', 1000.0), ('bonusBasisPoints', True),
                           ('recipient', 'all_ships'), ('activation', 'commissioning_unlock'),
                           ('unlock', {'kind': 'policy', 'contentId': BINDING[1]}),
                           ('unlock', {'kind': 'modifier', 'contentId': 'other'})]:
            changed = copy.deepcopy(data)
            next(e for e in changed['effects'] if e['nodeId'] == 'carronade_batteries')[key] = value
            with self.subTest(field=key, value=value):
                self.assertEqual([], naval.carronade_consumers(changed))
        changed = copy.deepcopy(data)
        changed['effects'].append(copy.deepcopy(next(e for e in changed['effects'] if e['nodeId'] == 'carronade_batteries')))
        self.assertEqual([], naval.carronade_consumers(changed))
        changed['effects'] = [e for e in changed['effects'] if e['nodeId'] != 'carronade_batteries']
        self.assertEqual([], naval.carronade_consumers(changed))

    def test_altered_authored_effect_or_unearned_world_entitlement_rejects(self):
        report, log = self.transcript()
        original = Path.read_text
        design = PROJECT / 'scenario/progression/gameplay-effect-design.json'
        for field, value in [('bonusBasisPoints', 900), ('family', 'land'),
                             ('activation', 'commissioning_unlock'), ('recipient', 'all_ships')]:
            authored = json.loads(original(design))
            next(e for e in authored['effects'] if e['nodeId'] == 'carronade_batteries')[field] = value
            def changed(path, *args, **kwargs):
                return json.dumps(authored) if path == design else original(path, *args, **kwargs)
            with self.subTest(field=field), patch.object(Path, 'read_text', changed):
                self.assertEqual(set(), self.bindings(report, log))
        world_path = PROJECT / 'scenario/world/world.json'
        world = json.loads(original(world_path))
        next(n for n in world['technologies'] if n['id'] == 'carronade_batteries')['unlocks'] = []
        def unearned(path, *args, **kwargs):
            return json.dumps(world) if path == world_path else original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', unearned):
            self.assertEqual(set(), self.bindings(report, log))


if __name__ == '__main__':
    unittest.main()
