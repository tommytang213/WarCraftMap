"""Synthetic protocol regressions; these logs are never naval execution evidence."""
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
import naval_repair as repair
import naval_carvel as carvel
import naval_services_catalog as naval
import release_blocker_audit as audit

PREFIX = 'wurst/NavalServicesTests.wurst:'
COMPARISON = PREFIX + verifier.COMPARISON
BINDING = ('unit', 'ship_of_the_line')
FINDING = 'RESEARCH-UNBOUND-BATTLEFLEET-DOCTRINE-UNIT-SHIP-OF-THE-LINE'


class NavalEvidenceProtocol(unittest.TestCase):
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
                   repairs=False, omit_repair_probe=None, repair_comparison=True,
                   carvels=False, omit_carvel_probe=None, carvel_comparison=True):
        expected = [row for row in self.expected if row['id'] != omitted_test]
        lines = ['Running tests']
        for row in expected:
            path, name = row['id'].rsplit(':', 1)
            lines.append(f'Running /synthetic/{path}:{row["line"]} - {name}..')
            probes = verifier.PROBES - {omit_probe} if row['id'] == COMPARISON and comparison else set()
            if repairs and repair_comparison and row['id'] == PREFIX + repair.COMPARISON:
                probes = repair.PROBES - {omit_repair_probe}
            if carvels and carvel_comparison and row['id'] == PREFIX + carvel.COMPARISON:
                probes = carvel.PROBES - {omit_carvel_probe}
            # A sibling test exercising every probe cannot replace the comparison.
            if row['id'] == PREFIX + 'navalProductionConsumerTraceExercisesAllFourRegisteredBenefitsOnOneRevision':
                probes = verifier.PROBES | repair.PROBES | carvel.PROBES
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


class NavalBindingEvidenceTests(NavalEvidenceProtocol):
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
        consumer, = [c for c in data['consumers'] if c['executionSystem'] == 'naval_commissioning']
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
        # Repair has its own candidate and isolated execution gate.
        self.assertEqual({'naval_commissioning', 'naval_repair', 'naval_carvel'},
                         {c['executionSystem'] for c in data['consumers']})


class NavalRepairBindingEvidenceTests(NavalEvidenceProtocol):
    def repair_transcript(self, **kwargs):
        return self.transcript(comparison=False, repairs=True, **kwargs)

    def test_only_exact_careening_finding_disappears_and_doctrine_remains_independent(self):
        report, log = self.repair_transcript()
        binding = ('modifier', 'progression_careening_stations')
        self.assertEqual({binding}, self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({'RESEARCH-UNBOUND-CAREENING-STATIONS-MODIFIER-PROGRESSION-CAREENING-STATIONS'},
                         before - after)
        self.assertFalse(after - before)
        self.assertIn(FINDING, after)
        for sibling in ('CARRONADE-BATTERIES', 'CARVEL-HULL-CONSTRUCTION'):
            self.assertTrue(any(sibling in name for name in after))
        report, log = self.transcript(repairs=True)
        self.assertEqual({BINDING, binding}, self.bindings(report, log))

    def test_commissioning_and_sibling_naval_traces_cannot_replace_repair_comparison(self):
        report, log = self.transcript()
        self.assertEqual({BINDING}, self.bindings(report, log))
        report, log = self.repair_transcript(repair_comparison=False)
        self.assertEqual(set(), self.bindings(report, log))
        # Even every repair probe in the commissioning test cannot substitute.
        report, log = self.transcript(repairs=True, repair_comparison=False)
        text = log.decode().replace('WCM_PROBE:naval_complete', 'WCM_PROBE:naval_complete\n' + '\n'.join(
            'WCM_PROBE:' + probe for probe in sorted(repair.PROBES)))
        tampered = text.encode()
        report['logSha256'] = evidence.digest(tampered)
        report['productionCoverage']['tests'] = evidence.observed_probes(text, report['tests'], self.contract)
        self.assertEqual({BINDING}, self.bindings(report, tampered))

    def test_complete_current_pinned_success_is_required(self):
        report, log = self.repair_transcript()
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
        for name in repair.REQUIRED_TESTS:
            with self.subTest(test=name):
                report, log = self.repair_transcript(fail_test=PREFIX + name)
                self.assertEqual(set(), self.bindings(report, log))
                report, log = self.repair_transcript(omitted_test=PREFIX + name)
                self.assertEqual(set(), self.bindings(report, log))

    def test_successful_payment_repair_and_restore_probes_must_execute_in_comparison(self):
        self.assertEqual(repair.PROBES, set(self.contract['systems']['naval_repair']))
        for probe in repair.PROBES:
            with self.subTest(probe=probe):
                report, log = self.repair_transcript(omit_repair_probe=probe)
                self.assertEqual(set(), self.bindings(report, log))
                report['productionCoverage']['tests'][PREFIX + repair.COMPARISON].append(probe)
                self.assertEqual(set(), self.bindings(report, log))

    def test_current_production_payment_repair_restore_and_test_inputs_are_required(self):
        report, log = self.repair_transcript()
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
            return text.replace('charge(p, money)', 'skip') if path == source else text
        with patch.object(Path, 'read_text', disconnected):
            self.assertEqual(set(), self.bindings(report, log))

    def test_exact_careening_metadata_rate_and_bills(self):
        data, _ = naval.build(PROJECT)
        consumer, = naval.repair_consumers(data)
        self.assertEqual(('careening_stations', 'modifier', 'progression_careening_stations',
                          'hull_repair_throughput', 1500, 'repair', 'naval_repair'),
                         tuple(consumer[k] for k in ('nodeId', 'kind', 'contentId', 'metric',
                                                    'bonusBasisPoints', 'action', 'executionSystem')))
        self.assertEqual((2, 1, 1, 1, 100, 10000), tuple(consumer[k] for k in
                         ('currency', 'timber', 'provisions', 'localSupply', 'baseOutput', 'maximumIntegrity')))
        self.assertEqual(['dockyard_logistics'], consumer['dockPrerequisites'])
        self.assertEqual('actual_missing_hull', consumer['outputBound'])
        self.assertEqual('per_funded_day', consumer['billing'])
        self.assertTrue(consumer['ordinaryMaintenanceIndependent'])
        self.assertTrue(consumer['operationalDockRequired'])
        self.assertTrue(consumer['ownedDocksideRecipientRequired'])
        changed = copy.deepcopy(data)
        changed['rules'].update(repairCost=3, repairWood=2, repairOutput=90)
        derived, = naval.repair_consumers(changed)
        self.assertEqual((3, 2, 90), tuple(derived[k] for k in ('currency', 'timber', 'baseOutput')))
        mutations = [lambda e: e.update(nodeId='other'),
                     lambda e: e['unlock'].update(kind='policy'),
                     lambda e: e['unlock'].update(contentId='other'),
                     lambda e: e.update(metric='voyage_hull_weather_resilience'),
                     lambda e: e.update(bonusBasisPoints=1499),
                     lambda e: e.update(bonusBasisPoints=1500.0),
                     lambda e: e.update(recipient='all_ships'),
                     lambda e: e.update(activation='commissioning_unlock')]
        for mutation in mutations:
            changed = copy.deepcopy(data)
            mutation(next(e for e in changed['effects'] if e['nodeId'] == 'careening_stations'))
            self.assertEqual([], naval.repair_consumers(changed))
        changed = copy.deepcopy(data)
        changed['effects'].append(copy.deepcopy(next(e for e in changed['effects']
                                                   if e['nodeId'] == 'careening_stations')))
        self.assertEqual([], naval.repair_consumers(changed))

    def test_changed_design_or_recipe_rejects_stale_repair_evidence(self):
        report, log = self.repair_transcript()
        original = Path.read_text
        original_bytes = Path.read_bytes
        for filename, change in (
                ('scenario/progression/gameplay-effect-design.json', lambda d: next(
                    e for e in d['effects'] if e['nodeId'] == 'careening_stations').update(bonusBasisPoints=2000)),
                ('scenario/naval/services.json', lambda d: d['rules'].update(repairCost=3))):
            path = PROJECT / filename
            data = json.loads(original(path))
            change(data)
            def changed(p, *args, **kwargs):
                return json.dumps(data) if p == path else original(p, *args, **kwargs)
            def changed_bytes(p):
                return json.dumps(data).encode() if p == path else original_bytes(p)
            with self.subTest(filename=filename), patch.object(Path, 'read_text', changed), \
                    patch.object(Path, 'read_bytes', changed_bytes):
                self.assertEqual(set(), self.bindings(report, log))


class NavalCarvelBindingEvidenceTests(NavalEvidenceProtocol):
    def carvel_transcript(self, **kwargs):
        return self.transcript(comparison=False, carvels=True, **kwargs)

    def test_only_exact_carvel_finding_disappears_and_prior_naval_recognition_survives(self):
        report, log = self.carvel_transcript()
        binding = ('modifier', 'progression_carvel_hull_construction')
        self.assertEqual({binding}, self.bindings(report, log))
        before = {row['id'] for row in audit._audit_research_bindings()}
        after = {row['id'] for row in audit._audit_research_bindings(
            execution=report, execution_log=log, revision=self.revision)}
        self.assertEqual({'RESEARCH-UNBOUND-CARVEL-HULL-CONSTRUCTION-MODIFIER-PROGRESSION-CARVEL-HULL-CONSTRUCTION'},
                         before - after)
        self.assertFalse(after - before)
        self.assertTrue(any('CARRONADE-BATTERIES' in name for name in after))
        report, log = self.transcript(repairs=True, carvels=True)
        self.assertEqual({BINDING, ('modifier', 'progression_careening_stations'), binding},
                         self.bindings(report, log))

    def test_commissioning_repair_and_sibling_traces_cannot_replace_carvel_comparison(self):
        report, log = self.transcript(repairs=True, carvels=True, carvel_comparison=False)
        self.assertEqual({BINDING, ('modifier', 'progression_careening_stations')},
                         self.bindings(report, log))
        report, log = self.carvel_transcript(carvel_comparison=False)
        self.assertEqual(set(), self.bindings(report, log))

    def test_weather_hull_commit_and_persistence_must_execute_in_isolated_comparison(self):
        self.assertEqual(carvel.PROBES, set(self.contract['systems']['naval_carvel']))
        for probe in carvel.PROBES:
            with self.subTest(probe=probe):
                report, log = self.carvel_transcript(omit_carvel_probe=probe)
                self.assertEqual(set(), self.bindings(report, log))
                report['productionCoverage']['tests'][PREFIX + carvel.COMPARISON].append(probe)
                self.assertEqual(set(), self.bindings(report, log))

    def test_complete_current_pinned_success_is_required(self):
        self.assertEqual(set(), self.bindings())
        report, log = self.carvel_transcript()
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
        for name in carvel.REQUIRED_TESTS:
            with self.subTest(test=name):
                report, log = self.carvel_transcript(fail_test=PREFIX + name)
                self.assertEqual(set(), self.bindings(report, log))
                report, log = self.carvel_transcript(omitted_test=PREFIX + name)
                self.assertEqual(set(), self.bindings(report, log))

    def test_current_production_and_source_inputs_are_required(self):
        report, log = self.carvel_transcript()
        for relative in ('wurst/NavalServices.wurst', 'wurst/NavalCampaignRuntime.wurst',
                         'wurst/MilitarySettlementRuntime.wurst', 'wurst/NavalServicesTests.wurst',
                         'wurst/VoyageCommands.wurst', 'wurst/VoyageNavigation.wurst'):
            invalid = copy.deepcopy(report)
            invalid['inputs'][relative] = '0' * 64
            invalid['inputSetSha256'] = evidence.digest(evidence.canonical(invalid['inputs']))
            self.assertEqual(set(), self.bindings(invalid, log))
        original = Path.read_text
        source = self.sources['wurst/NavalCampaignRuntime.wurst']
        def disconnected(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text.replace('voyageWeather(f, profile, at)', 'skip') if path == source else text
        with patch.object(Path, 'read_text', disconnected):
            self.assertEqual(set(), self.bindings(report, log))

    def test_exact_carvel_metadata_rate_profiles_service_boundary_and_paid_recipe(self):
        data, _ = naval.build(PROJECT)
        consumer, = naval.carvel_consumers(data)
        self.assertEqual(('carvel_hull_construction', 'modifier', 'progression_carvel_hull_construction',
                          'voyage_hull_weather_resilience', 800, 'voyage', 'naval_carvel', '1460-01-01'),
                         tuple(consumer[k] for k in ('nodeId', 'kind', 'contentId', 'metric',
                                                    'bonusBasisPoints', 'action', 'executionSystem', 'firstDate')))
        self.assertEqual(dict(currency=200, timber=20, iron=2, days=30), consumer['refit'])
        self.assertEqual(dict(exposure=100, period=5, exposedDays=2), consumer['weather'])
        self.assertEqual(data['carvelBuiltProfiles'], consumer['builtProfiles'])
        self.assertEqual(['armed_sailing_warship', 'ocean_merchantman'], consumer['refitProfiles'])
        for key in ('currentOwnerResearchRequired', 'fundedMaintenanceRequired',
                    'completedCompatibleHullRequired', 'provisionsIndependent',
                    'navigationIndependent', 'combatIndependent'):
            self.assertIs(True, consumer[key])
        self.assertEqual('actual_voyage_hull_weather_loss', consumer['outputBound'])
        changed = copy.deepcopy(data)
        changed['rules'].update(stormLoss=50, carvelCost=250, carvelWood=21, carvelIron=3, carvelDays=31)
        derived, = naval.carvel_consumers(changed)
        self.assertEqual(dict(currency=250, timber=21, iron=3, days=31), derived['refit'])
        self.assertEqual(50, derived['weather']['exposure'])
        mutations = [lambda e: e.update(nodeId='other'),
                     lambda e: e['unlock'].update(kind='policy'),
                     lambda e: e['unlock'].update(contentId='other'),
                     lambda e: e.update(metric='hull_repair_throughput'),
                     lambda e: e.update(bonusBasisPoints=799),
                     lambda e: e.update(bonusBasisPoints=800.0),
                     lambda e: e.update(recipient='all_ships'),
                     lambda e: e.update(activation='commissioning_unlock')]
        for mutation in mutations:
            changed = copy.deepcopy(data)
            mutation(next(e for e in changed['effects'] if e['nodeId'] == 'carvel_hull_construction'))
            self.assertEqual([], naval.carvel_consumers(changed))
        changed = copy.deepcopy(data)
        changed['effects'].append(copy.deepcopy(next(e for e in changed['effects']
                                                   if e['nodeId'] == 'carvel_hull_construction')))
        self.assertEqual([], naval.carvel_consumers(changed))

    def test_changed_design_profiles_boundary_recipe_or_exposure_reject_stale_evidence(self):
        report, log = self.carvel_transcript()
        original, original_bytes = Path.read_text, Path.read_bytes
        mutations = [('scenario/progression/gameplay-effect-design.json', lambda d: next(
            e for e in d['effects'] if e['nodeId'] == 'carvel_hull_construction').update(bonusBasisPoints=900)),
            ('scenario/naval/services.json', lambda d: d.update(carvelFirstDate='1450-01-01')),
            ('scenario/naval/services.json', lambda d: d['carvelBuiltProfiles'].remove('ship_of_the_line_generic')),
            ('scenario/naval/services.json', lambda d: d['rules'].update(carvelCost=201)),
            ('scenario/naval/services.json', lambda d: d['rules'].update(stormLoss=101))]
        for filename, change in mutations:
            path = PROJECT / filename
            data = json.loads(original(path))
            change(data)
            def changed(p, *args, **kwargs):
                return json.dumps(data) if p == path else original(p, *args, **kwargs)
            def changed_bytes(p):
                return json.dumps(data).encode() if p == path else original_bytes(p)
            with self.subTest(filename=filename), patch.object(Path, 'read_text', changed), \
                    patch.object(Path, 'read_bytes', changed_bytes):
                self.assertEqual(set(), self.bindings(report, log))


if __name__ == '__main__':
    unittest.main()
