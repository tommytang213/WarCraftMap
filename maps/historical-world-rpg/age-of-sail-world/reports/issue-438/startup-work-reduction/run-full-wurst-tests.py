#!/usr/bin/env python3
"""Run the unchanged complete Wurst gate against frozen dirty-tree inputs.

This is regression evidence only. It does not compile player maps or establish
native Warcraft acceptance. Existing validation artifacts remain untouched.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

BASE = Path('/workspace/scratch/243ebc79fa0a')
REPO = BASE / 'WarCraftMap'
PROJECT = REPO / 'maps/historical-world-rpg/age-of-sail-world'
OUT = BASE / 'validation-536/continue-fix/full-wurst-tests'
ROOT = OUT / 'compile'
SEED = BASE / 'validation-536/continue-fix/authority-focused-attempt3/compile'
LAUNCHER = BASE / 'pinned-wurst/grill'
TOOL_HOME = BASE / 'pinned-wurst/rootfs/home/wurstuser/.wurst'
COMPILER = TOOL_HOME / 'wurst-compiler/wurstscript.jar'
DEPENDENCY_REVISION = 'cce79096e71dcb066cf94785bc5cb48ef66c26db'
GENERATED = {'wurst/ScenarioData.wurst', 'wurst/ScenarioSettings.wurst',
             'wurst/ConformanceData.wurst'}
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from integration_evidence import execution_sources, source_identity
from wurst_execution import (PINNED_COMPILER_SHA256, PINNED_IMAGE, canonical,
                             discover, execute_tests, input_hashes, verify_evidence)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(inputs):
    return hashlib.sha256(canonical(inputs)).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def git(*args, cwd=REPO):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.part')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    os.replace(temporary, path)


def source_inputs():
    roots = [PROJECT / name for name in
             ('map', 'scenario', 'wurst', 'wurst-bootstrap', 'tooling', 'tests')]
    roots.append(PROJECT.parent / '_shared')
    paths = [p for root in roots for p in root.rglob('*') if p.is_file()
             and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'}]
    paths += [p for p in PROJECT.iterdir()
              if p.is_file() and p.suffix in {'.json', '.build', '.args'}]
    return {Path(os.path.relpath(p, PROJECT)).as_posix(): sha(p)
            for p in sorted(set(paths))}


def dependency_state():
    dependency = ROOT / '_build/dependencies/WurstStdlib2'
    paths = [p for p in sorted(dependency.rglob('*'))
             if p.is_file() and '.git' not in p.relative_to(dependency).parts]
    assert paths and all(not p.is_symlink() for p in paths)
    inputs = {p.relative_to(dependency).as_posix(): sha(p) for p in paths}
    return {'revision': git('rev-parse', 'HEAD', cwd=dependency),
            'dirty': bool(git('status', '--porcelain', cwd=dependency)),
            'inputs': inputs, 'inputSetSha256': digest(inputs)}


def toolchain_state():
    paths = {'launcher': LAUNCHER, 'compiler': COMPILER,
             'grill': TOOL_HOME / 'grill-cli/grill.jar',
             'java': TOOL_HOME / 'wurst-runtime/bin/java'}
    return {name: {'path': str(path), 'sha256': sha(path)}
            for name, path in paths.items()}


def main():
    if OUT.exists():
        raise RuntimeError('Preserve prior evidence; full-wurst-tests already exists')
    OUT.mkdir(parents=True)
    revision = git('rev-parse', 'HEAD')
    dirty_status = git('status', '--porcelain', '--untracked-files=all')
    assert revision == '264b34c9a0762bdadda377fb10cb44a63af33052'
    assert dirty_status, 'This runner describes the explicitly authorized dirty-tree regression'
    receipt = {
        'format': 'warcraftmap_dirty_full_wurst_regression_v1',
        'scope': 'Complete unchanged Wurst interpreter regression on frozen working-tree bytes',
        'baselineRevision': revision,
        'baselineRevisionIsActualCleanSource': False,
        'sourceState': 'dirty_working_tree_bound_to_source_and_compiler_input_hashes',
        'gitStatusAtStart': dirty_status.splitlines(),
        'sourceIdentity': source_identity(PROJECT, revision),
        'startedAt': now(), 'status': 'preparing',
        'executionEnvironment': 'Verified extracted pinned toolchain on workspace host; full Docker image not executed',
        'expectedImage': PINNED_IMAGE,
        'nativeStatus': 'not_run', 'playerArtifactProduced': False,
        'repositoryTestAnnotationsModified': False,
        'repositoryTestDeadlinesModified': False,
        'repositoryExecutionGateModified': False,
        'compileTreeSeed': str(SEED),
        'inputPolicy': 'All current authored Wurst inputs and current build/args are overlaid; only three generated scenario packages are retained from the seed. The unchanged gate records instrumented inputs and each complete-discovery shard.',
        'dependencyPolicy': 'The copied clean pinned standard library is hashed before and after; no dependency installation or network refresh is invoked.',
        'dependencyDirectoryCase': 'The verified seed already uses WurstStdlib2, matching the unchanged authored dependency URL. Dependency bytes and Git revision are unchanged.',
    }
    receipt_path = OUT / 'run-receipt.json'
    write_json(receipt_path, receipt)
    started = time.monotonic()
    before_sources = before_inputs = before_dependency = before_toolchain = None
    error = None
    try:
        before_sources = source_inputs()
        assert digest(before_sources) == receipt['sourceIdentity']['sourceTreeSha256']
        write_json(OUT / 'source-inputs-before.json', before_sources)
        shutil.copytree(SEED, ROOT)
        seed_dependency = ROOT / '_build/dependencies/wurstStdlib2'
        authored_dependency = ROOT / '_build/dependencies/WurstStdlib2'
        if seed_dependency.is_dir() and not authored_dependency.exists():
            seed_dependency.rename(authored_dependency)
        assert authored_dependency.is_dir() and not seed_dependency.exists()
        sources = execution_sources(PROJECT)
        extra = {p.relative_to(ROOT).as_posix()
                 for p in (ROOT / 'wurst').rglob('*.wurst')} - set(sources)
        assert extra == GENERATED, f'Unexpected stale/generated seed packages: {sorted(extra)}'
        generated_inputs = {relative: sha(ROOT / relative) for relative in sorted(GENERATED)}
        for relative, source in sources.items():
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for name in ('wurst.build', 'wurst_run.args'):
            source, target = PROJECT / name, ROOT / name
            if source.is_file():
                shutil.copy2(source, target)
            elif target.exists():
                target.unlink()
        expected = discover(ROOT)
        canonical_expected = discover(PROJECT, sources=sources)
        assert expected == canonical_expected, 'Assembly discovery differs from all canonical source tests'
        assert source_identity(PROJECT, revision) == receipt['sourceIdentity']
        before_inputs = input_hashes(ROOT)
        before_dependency = dependency_state()
        assert before_dependency['revision'] == DEPENDENCY_REVISION and not before_dependency['dirty']
        before_toolchain = toolchain_state()
        assert before_toolchain['compiler']['sha256'] == PINNED_COMPILER_SHA256
        write_json(OUT / 'compiler-inputs-before.json', before_inputs)
        write_json(OUT / 'dependency-inputs-before.json', before_dependency)
        write_json(OUT / 'toolchain-before.json', before_toolchain)
        write_json(OUT / 'complete-discovery.json', expected)
        receipt.update(status='running', testCount=len(expected), generatedSeedInputs=generated_inputs,
                       dependencyRevision=DEPENDENCY_REVISION,
                       compilerSha256=PINNED_COMPILER_SHA256,
                       originalInputSetSha256=digest(before_inputs),
                       authoritativeSourceSetSha256=digest(before_sources),
                       dependencyInputSetSha256=before_dependency['inputSetSha256'],
                       javaToolOptions='-Xmx6g', executionGate='unchanged execute_tests(project=PROJECT)')
        write_json(receipt_path, receipt)
        os.environ['JAVA_TOOL_OPTIONS'] = '-Xmx6g'
        print(f'Executing ALL {len(expected)} discovered Wurst tests on dirty source {receipt["sourceIdentity"]["sourceTreeSha256"]}', flush=True)
        result = execute_tests(ROOT, str(LAUNCHER), OUT, revision, project=PROJECT)
        verify_evidence(result, (OUT / 'execution.log').read_bytes(), revision)
        assert result['expected'] == expected
        assert result['discovered'] == result['succeeded'] == len(expected)
        assert result['sourceIdentity'] == receipt['sourceIdentity']
        receipt.update(status='pass', executionStatus=result['executionStatus'],
                       discovered=result['discovered'], succeeded=result['succeeded'],
                       resultsSha256=sha(OUT / 'results.json'),
                       transcriptSha256=sha(OUT / 'execution.log'),
                       actualInstrumentedInputSetSha256=result['inputSetSha256'])
    except BaseException as exc:
        error = exc
        receipt.update(status='fail', error=str(exc), errorType=type(exc).__name__)
    finally:
        boundary_errors = []
        checks = [
            (before_sources, source_inputs, 'source-inputs-after.json',
             'authoritativeSourcesUnchanged', 'Authoritative sources changed during full regression'),
            (before_inputs, lambda: input_hashes(ROOT), 'compiler-inputs-after.json',
             'originalCompilerInputsRestoredAndUnchanged', 'Compiler inputs differ after gate restoration'),
            (before_dependency, dependency_state, 'dependency-inputs-after.json',
             'dependencyInputsUnchanged', 'Standard library changed during regression'),
            (before_toolchain, toolchain_state, 'toolchain-after.json',
             'toolchainUnchanged', 'Toolchain changed during regression'),
        ]
        for before, read_after, filename, field, diagnostic in checks:
            if before is None:
                continue
            try:
                after = read_after()
                write_json(OUT / filename, after)
                receipt[field] = before == after
                if before != after:
                    boundary_errors.append(diagnostic)
            except BaseException as exc:
                receipt[field] = False
                boundary_errors.append(f'{filename}: {type(exc).__name__}: {exc}')
        if boundary_errors:
            receipt.update(status='fail', boundaryErrors=boundary_errors)
            if error is None:
                error = RuntimeError('; '.join(boundary_errors))
        receipt.update(finishedAt=now(), elapsedSeconds=round(time.monotonic()-started, 3),
                       gitHeadAtEnd=git('rev-parse', 'HEAD'),
                       gitStatusAtEnd=git('status', '--porcelain', '--untracked-files=all').splitlines())
        write_json(receipt_path, receipt)
        print(json.dumps({key: receipt.get(key) for key in
                          ('status', 'discovered', 'succeeded', 'elapsedSeconds', 'error', 'boundaryErrors')}, sort_keys=True), flush=True)
    if error is not None:
        raise error


if __name__ == '__main__':
    main()
