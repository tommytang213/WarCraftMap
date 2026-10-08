"""Gate mutations against the real help mappings, with synthetic gate receipts.

These protocol fixtures are not execution evidence. The pinned Wurst run emits
release receipts from InstalledCommandHelpTests through the installed callback.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
import requirement_traceability as trace
import wurst_execution as execution


class InstalledHelpTraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / 'campaign'
        (self.project / 'docs').mkdir(parents=True)
        (self.project / 'wurst').mkdir()
        for name in ('CommandRouter', 'Bootstrap', 'InstalledCommandHelpTests', 'CommandRouterTests'):
            relative = f'wurst/{name}.wurst'
            (self.project / relative).write_bytes(trace.source_path(PROJECT, relative).read_bytes())
        self.mappings = trace.load(PROJECT / 'scenario/traceability/mappings.json')
        ledger = trace.load(PROJECT / 'scenario/traceability/requirements.json')
        parents = {key.split('.')[0] for key in self.mappings['requirements']}
        self.ledger = {'documents': ['docs/DESIGN_LOCK.md'], 'requiredCatalogues': [], 'dependencies': [],
                       'requirements': [row for row in ledger['requirements'] if row['id'] in parents]}
        (self.project / 'docs/DESIGN_LOCK.md').write_text('# Commands\n\n' + ''.join(
            f"- <!-- req:{row['id']} --> {row['text']}\n" for row in self.ledger['requirements']))
        self.evidence, self.transcript = self.receipts()

    def receipts(self, adapters=True):
        expected = execution.discover(self.project)
        lines = ['Running tests']
        for test in expected:
            relative, symbol = test['id'].split(':')
            lines.append(f"Running /compile/{relative}:{test['line']} - {symbol}..")
            if adapters:
                for mapping in self.mappings['requirements'].values():
                    for case in mapping['tests'].values():
                        if case['id'] == test['id']:
                            lines.append('TRACEABILITY ' + json.dumps(case['receipt']))
            lines.append('\tOK!')
        lines += [f'Tests succeeded: {len(expected)}/{len(expected)}', 'Finished running tests']
        log = ('\n'.join(lines) + '\n').encode()
        tests, errors = execution.parse_results(log.decode(), expected)
        inputs = execution.input_hashes(self.project)
        return {'format': execution.FORMAT, 'status': 'pass', 'sourceRevision': 'a' * 40,
                'returnCode': 0, 'executionStatus': 'completed', 'expected': expected,
                'tests': tests, 'errors': errors, 'inputs': inputs,
                'inputSetSha256': execution.sha(execution.canonical(inputs)),
                'logSha256': execution.sha(log), 'compiler': {'sha256': execution.PINNED_COMPILER_SHA256},
                'discovered': len(expected), 'succeeded': len(expected)}, log

    def report(self):
        return trace.audit(self.project, self.ledger, self.mappings, [], [],
                           evidence=self.evidence, transcript=self.transcript, revision='a' * 40)

    def test_all_six_obligations_have_explicit_installed_receipts_and_read_only_policy(self):
        self.assertEqual(6, len(self.mappings['requirements']))
        report = self.report()
        self.assertEqual([], report['executionErrors'])
        for row in report['requirements']:
            self.assertEqual(['artifact-missing'], row['blockerClasses'], row['id'])
            self.assertEqual('read-only', row['mapping']['persistence']['mode'])
            self.assertEqual({'success', 'failure', 'stale', 'replay'}, set(row['mapping']['tests']))
        self.assertFalse(report['candidateReady'])

    def test_removed_registration_or_disconnected_callback_blocks_despite_handler_passes(self):
        path = self.project / 'wurst/CommandRouter.wurst'
        original = path.read_text()
        for removed in ('natives.registerChat(chatListener,Player(i),"/",false)',
                        'TriggerAddAction(chatListener,function routeChat)',
                        'active.dispatch(chatNatives.eventPlayer(),chatNatives.eventText())',
                        'TriggerRegisterPlayerChatEvent(listener,sender,prefix,exact)',
                        'installCommandRegistry(registry,new WarcraftCommandChatNatives())'):
            with self.subTest(removed=removed):
                path.write_text(original.replace(removed, 'skip'))
                # Rehash the mutant and retain passing handler tests and even
                # claimed receipts. Source reachability must still fail closed.
                self.evidence, self.transcript = self.receipts()
                self.assertTrue(all(row['status'] == 'pass' for row in self.evidence['tests']))
                self.assertTrue(any('CommandRouterTests' in row['id'] for row in self.evidence['tests']))
                report = self.report()
                self.assertEqual([], report['executionErrors'])
                for row in report['requirements']:
                    self.assertIn('unreachable', row['blockerClasses'], row['id'])
                self.assertFalse(report['candidateReady'])

    def test_handler_success_without_installed_receipts_cannot_close_help(self):
        self.evidence, self.transcript = self.receipts(adapters=False)
        report = self.report()
        for row in report['requirements']:
            self.assertIn('integration-missing', row['blockerClasses'])
            self.assertIn('static-only', row['blockerClasses'])

    def test_another_overload_cannot_supply_the_native_installation_path(self):
        ref = copy.deepcopy(self.mappings['requirements']['REQ-0203.01']['entry']['path'][1])
        self.assertTrue(trace.reference_ok(self.project, ref))
        ref['signature'] = 'public function installCommandRegistry(CommandRegistry registry,CommandChatNatives natives)'
        self.assertFalse(trace.reference_ok(self.project, ref))

    def test_compiled_callback_must_be_connected_not_a_diagnostic_marker(self):
        mapping = self.mappings['requirements']['REQ-0203.01']
        script = '''function main()
TriggerRegisterPlayerChatEvent(listener, sender, "/", false)
TriggerAddAction(listener, CommandRouter_routeChat)
DestroyTrigger(obsolete)
CommandRouter_CommandRegistry_register(registry, "help")
end
'''
        maps = [{'id': 'region', 'bootstrap': False}]
        self.assertTrue(trace.artifact_ok(mapping, maps, {'region': {'script': script}}))
        for replacement in ('', 'print("TriggerAddAction(listener, CommandRouter_routeChat)")',
                            'TriggerAddAction(listener, unrelatedCallback)'):
            mutant = script.replace('TriggerAddAction(listener, CommandRouter_routeChat)', replacement)
            self.assertFalse(trace.artifact_ok(mapping, maps, {'region': {'script': mutant}}))


if __name__ == '__main__':
    unittest.main()
