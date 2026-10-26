#!/usr/bin/env python3
"""Run the reviewed scoped and canonical gates once on the committed candidate."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / 'WarCraftMap'
PROJECT = REPO / 'maps/historical-world-rpg/age-of-sail-world'
COMMIT = '791ce7f44944af124fe87400d2f1ecfa5882240b'
TREE = 'fdd7fa78e57430b6c75c11c3ba00b642aaa4c9d8'
SOURCE = '91996f8be9079d4e0c3a3c6dd84b7b96f04f119ff38714765804052f7750c450'
WRAPPER_SHA = '683682e2d9016f97e97c905e498416079c72a2efa07ae1ab969160dc493db5df'
DIAGNOSTIC_SHA = 'd6ca065f4ef926108d0a74522b1016c75efde51eaa87cfedbf6ae65092fc8a4f'
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from integration_evidence import source_identity, execution_sources, load_contract
from wurst_execution import discover


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO).decode().strip()


def unchanged():
    assert git('rev-parse', 'HEAD') == COMMIT and git('rev-parse', 'HEAD^{tree}') == TREE
    assert git('status', '--porcelain=v1') == '', 'Candidate worktree changed'
    assert source_identity(PROJECT, COMMIT)['sourceTreeSha256'] == SOURCE
    assert digest(ROOT / 'bin/grill') == WRAPPER_SHA
    assert digest(ROOT / 'diagnostic_python/sitecustomize.py') == DIAGNOSTIC_SHA


def now():
    return datetime.now(timezone.utc).isoformat()


class RunInterrupted(Exception):
    pass


def interrupted(signum, frame):
    raise RunInterrupted('Received signal ' + str(signum))


def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_owned_group(child):
    """Only signal the new session created for this driver's exact child."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    for signum, seconds in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        child.poll()
        if group_exists(child.pid):
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            result = child.poll()
            if result is not None and not group_exists(child.pid):
                return {'childExitCode': result, 'ownedGroupStopped': True}
            time.sleep(0.1)
    return {'childExitCode': child.poll(), 'ownedGroupStopped': not group_exists(child.pid)}


assert sys.flags.optimize == 0 and os.environ.get('PYTHONOPTIMIZE', '') in ('', '0')
unchanged()
assert not (ROOT / 'required-attempt3').exists(), 'Retain prior attempt; do not duplicate validation'
for process in Path('/proc').iterdir():
    if not process.name.isdigit():
        continue
    try:
        args = (process / 'cmdline').read_bytes().split(b'\0')
    except OSError:
        continue
    assert not (args and args[0].endswith(b'/java') and
                any(arg.endswith((b'/grill.jar', b'/wurstscript.jar')) for arg in args)), 'Compiler already running'
OUT = ROOT / 'required-attempt3'
OUT.mkdir()
authored_discovery = discover(PROJECT, sources=execution_sources(PROJECT))
contract = load_contract(PROJECT)
(OUT / 'authored-discovery.json').write_text(json.dumps(authored_discovery, indent=2) + '\n')
record = {'status': 'running', 'startedAt': now(), 'driverPid': os.getpid(),
          'commit': COMMIT, 'gitTree': TREE, 'sourceIdentity': source_identity(PROJECT, COMMIT),
          'integratedMain': '594d36cfdcd1660753ea4cd743132a823443dcf3',
          'sourceState': 'clean_committed_tree', 'authoredTestsDiscovered': len(authored_discovery),
          'contractProbes': len(contract['probes']), 'contractSystems': len(contract['systems']),
          'wrapperSha256': WRAPPER_SHA, 'wrapperRelocation': 'workspace paths and launcher digest only; original review retained historically',
          'driverSha256': digest(Path(__file__)), 'commands': [], 'nativeStatus': 'not_run',
          'executionEnvironment': 'verified extracted pinned toolchain on workspace host; complete OCI image not run',
          'resultLoggingInstrumentation': {'path': str(ROOT / 'diagnostic_python/sitecustomize.py'), 'sha256': DIAGNOSTIC_SHA, 'effect': 'Print immediate unittest addError/addFailure tracebacks after original result accounting; standard addSubTest unchanged'},
          'gateChanges': False, 'fullAgeOfSailWurstRunsPlanned': 1}


def save():
    temporary = OUT / 'receipt.json.tmp'
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    os.replace(temporary, OUT / 'receipt.json')


save()
environment = dict(os.environ, PATH=str(ROOT / 'bin') + os.pathsep + os.environ['PATH'],
                   WARCRAFTMAP_WURST_CHECK='required', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
                   PYTHONPATH=str(ROOT / 'diagnostic_python') + (os.pathsep + os.environ['PYTHONPATH'] if os.environ.get('PYTHONPATH') else ''))
commands = [('canonical-required', ['bash', 'automation/run_checks.sh'], REPO)]
active_child = None
launch_in_progress = False
signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)
try:
    for name, command, cwd in commands:
        unchanged()
        item = {'name': name, 'command': command, 'cwd': str(cwd), 'startedAt': now(), 'status': 'running'}
        record['commands'].append(item)
        save()
        print(json.dumps({'stage': name, 'status': 'starting', 'commit': COMMIT}), flush=True)
        start = time.monotonic()
        log = OUT / (name + '.log')
        with log.open('xb') as stream:
            launch_in_progress = True
            active_child = subprocess.Popen(command, cwd=cwd, env=environment, stdout=stream,
                                            stderr=subprocess.STDOUT, start_new_session=True)
            launch_in_progress = False
            item.update(pid=active_child.pid, ownedProcessGroup=active_child.pid)
            save()
            while active_child.poll() is None:
                stop_request = OUT / 'assistant-stop-request.txt'
                if stop_request.exists():
                    raise RunInterrupted('Assistant stop requested: ' + stop_request.read_text().strip())
                try:
                    active_child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
            result = active_child.returncode
        assert not group_exists(active_child.pid), 'Owned descendants remain after gate child exit'
        active_child = None
        item.update(exitCode=result, status='pass' if result == 0 else 'fail', finishedAt=now(),
                    seconds=round(time.monotonic() - start, 3), logSha256=digest(log), logBytes=log.stat().st_size)
        save()
        print(json.dumps(item), flush=True)
        assert result == 0, (name, result)
        unchanged()
    record.update(status='pass', sourceInputsUnchanged=True, worktreeClean=True)
except BaseException as exc:
    record.update(status='fail', error=type(exc).__name__ + ': ' + str(exc))
    if active_child is not None:
        recovery = {'childPid': active_child.pid, 'ownedProcessGroup': active_child.pid,
                    'attemptedAt': now(), 'ownedGroupStopped': False}
        try:
            recovery.update(stop_owned_group(active_child))
        except BaseException as cleanup_error:
            recovery['cleanupError'] = type(cleanup_error).__name__ + ': ' + str(cleanup_error)
        terminal = recovery.get('childExitCode') is not None and recovery['ownedGroupStopped']
        record.update(status='interrupted' if terminal else 'interrupted_process_state_unknown',
                      interruptedAt=now(), childReconciliation=recovery,
                      completionKnown=terminal, readOnlyReconciliationRequired=not terminal)
        item.update(status=record['status'], childReconciliation=recovery)
        if terminal:
            item.update(finishedAt=now(), logSha256=digest(log), logBytes=log.stat().st_size)
    elif launch_in_progress:
        record.update(status='interrupted_process_state_unknown', interruptedAt=now(),
                      completionKnown=False, readOnlyReconciliationRequired=True,
                      childReconciliation={'reason': 'Popen did not return a child handle; launch outcome is unknown'})
        item.update(status=record['status'])
    raise
finally:
    if record.get('completionKnown', True):
        record['finishedAt'] = now()
    try:
        save()
    except BaseException as receipt_error:
        print(json.dumps({'receiptWriteError': type(receipt_error).__name__ + ': ' + str(receipt_error),
                          'lastKnownRecord': record}), file=sys.stderr, flush=True)
        raise

print(json.dumps({'status': record['status'], 'commit': COMMIT, 'nativeStatus': 'not_run'}), flush=True)
