"""Pinned local execution, typecheck and diagnostic package for issue #476.

Pass a worktree-local offline Grill wrapper. Sources are assembled under _build;
--smoke selects only navigation tests in that disposable assembly.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import shutil
import importlib.util
import re
from collections import Counter

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from package_wurst_map import load_config, generate, _assemble, _run, _find_archive, _inspect
from wurst_execution import execute_tests, source_revision, toolchain_environment, verify_evidence
from integration_evidence import source_identity
from warcraft_campaign import MpqReader

NAVIGATION_SUITES = {
    'QuestNavigationTests.wurst', 'AuthoredQuestTests.wurst', 'VisitKnowledgeTests.wurst',
    'MapDiscoveryScreenTests.wurst', 'RpgInteractionTests.wurst', 'CampaignStartupTests.wurst',
    'CampaignLoadTransactionTests.wurst', 'ManagementCommandTests.wurst',
    'ManagementScreenPauseControllerTests.wurst', 'InstalledCommandHelpTests.wurst',
    'CommandMapTransportTests.wurst', 'RemoteRegionAuthorityTests.wurst',
    'PlayableCampaignRuntimeTests.wurst', 'CampaignAutosaveLifecycleTests.wurst',
}


def selected(group, name):
    if group == 'all':
        return True
    if group == 'rpg':
        return name == 'WarcraftRpgRuntimeTests.wurst'
    if group == 'navigation':
        return name in NAVIGATION_SUITES
    return name not in NAVIGATION_SUITES and name != 'WarcraftRpgRuntimeTests.wurst'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grill', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--inspect-existing', action='store_true')
    parser.add_argument('--package', action='store_true')
    parser.add_argument('--build-dir', type=Path, default=PROJECT / '_build/issue476-all')
    parser.add_argument('--group', choices=['all', 'navigation', 'rpg', 'remaining'], default='all')
    args = parser.parse_args()
    grill = str(args.grill.resolve())
    config = load_config(PROJECT / 'package.json')
    root = args.build_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    revision = source_revision(PROJECT)
    comp = root / 'compile'
    if args.inspect_existing:
        result = json.loads((root / 'evidence/results.json').read_text())
        verify_evidence(result, (root / 'evidence/execution.log').read_bytes(), revision)
        assert result['sourceIdentity'] == source_identity(PROJECT, revision), 'execution is stale'
    else:
        if (root / 'compile').exists():
            shutil.rmtree(root / 'compile')
        generate(config, root / 'generated')
        comp = _assemble(config, root, root / 'generated')
        for path in (comp / 'wurst').glob('*.wurst'):
            if (args.smoke and path.name != 'QuestNavigationTests.wurst') or not selected(args.group, path.name):
                path.write_text(path.read_text().replace('@test', ''))
        _run('offline dependencies', [grill, 'install'], comp)
        typed = subprocess.run([grill, 'typecheck'], cwd=comp, env=toolchain_environment(),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (root / 'typecheck.log').write_text(typed.stdout)
        assert typed.returncode == 0, typed.stdout
        print('Pinned typecheck passed', flush=True)
        revision = source_revision(PROJECT)
        execute_tests(comp, grill, root / 'evidence', revision, project=PROJECT)
    if args.package:
        identity = source_identity(PROJECT, revision)
        (comp / 'map' / config.source_map.name / 'runtime/build-identity.json').write_text(
            json.dumps(identity, sort_keys=True) + '\n')
        if not args.inspect_existing:
            _run('diagnostic package', [grill, 'build', str(Path('map') / config.source_map.name)], comp)
        archive = _find_archive(comp / '_build')
        _inspect(config, archive, comp)
        reader = MpqReader(archive)
        lua = reader.read('war3map.lua').decode()
        packaged = json.loads(reader.read('runtime/scenario-runtime.json'))
        expected = json.loads((root / 'generated/scenario-runtime.json').read_text())
        assert packaged == expected
        symbols = ['QuestNavigationController_show', 'QuestNavigationController_resolve',
                   'QuestNavigationController_refreshMarker', 'WarcraftLocalQuestMarker_replace',
                   'TrackQuestCommand_execute', 'MapDiscoveryScreenController_focusGuidance']
        def body(symbol):
            match = re.search(r'^function \w*' + symbol + r'\([^\n]*\)[ \t]*\n(.*?)(?=^function |\Z)', lua, re.M | re.S)
            assert match, symbol
            return match[1]
        for symbol in symbols:
            body(symbol)
        assert 'AddSpecialEffect(' in body('WarcraftLocalQuestMarker_replace')
        assert 'DestroyEffect(' in body('WarcraftLocalQuestMarker_clear')
        assert 'dispatch_MapPresentationRuntime_focusExact(' in body('MapDiscoveryScreenController_focusGuidance')
        assert '"showonmap"' in lua and 'AddSpecialEffect(' in lua
        assert json.loads(reader.read('runtime/build-identity.json')) == identity
        # Compare actual compiled constructor/storage rows, not only embedded JSON.
        spec = importlib.util.spec_from_file_location('compiled_quests', PROJECT / 'reports/issue-445/inspect_compiled.py')
        inspector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inspector)
        graph_report = inspector.inspect(archive, json.loads(config.scenario_file.read_text()))
        fields = ['precision', 'regionId', 'destinationId', 'searchAreas', 'requiredClues']
        actual = inspector.rows(lua, 'QuestGuidance', fields)
        guides = []
        for quest in expected['questDefinitions']:
            journal = quest.get('journal', {})
            definitions = list(journal.get('destinations', {}).values())
            if journal.get('turnInDestination'):
                definitions.append(journal['turnInDestination'])
            for guide in definitions:
                guides.append(dict(precision=guide.get('precision', 'hidden'), regionId=guide.get('regionId', ''),
                                   destinationId=guide.get('locationId', guide.get('settlementId', '')),
                                   searchAreas=json.dumps(guide['searchAreas'], separators=(',', ':')) if guide.get('searchAreas') else '',
                                   requiredClues=''.join(x + '~' for x in guide.get('requiredClueIds', []))))
        def canonical(row):
            row = dict(row)
            row['searchAreas'] = json.loads(row['searchAreas']) if row['searchAreas'] else []
            return json.dumps(row, sort_keys=True)
        assert Counter(map(canonical, actual)) == Counter(map(canonical, guides)), 'compiled guidance definitions differ'
        report = dict(sourceIdentity=identity, archiveSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                      generatedDefinitionsMatch=True, compiledSymbols=symbols,
                      localMarkerNative=True, showOnMapRegistration=True,
                      compiledGuidanceCount=len(guides), compiledGuidanceDefinitionsMatch=True,
                      questCount=graph_report['questCount'], stageCount=graph_report['stageCount'],
                      nativeClient='not_run', releaseReady=False)
        (root / 'packaged-guidance.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
