#!/usr/bin/env python3
"""Refresh existing reports without granting native or release acceptance."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

BASE = Path('/workspace/scratch/243ebc79fa0a')
REPO = BASE / 'WarCraftMap'
PROJECT = REPO / 'maps/historical-world-rpg/age-of-sail-world'
OUT = BASE / 'validation-536/continue-fix/source-checks'
REVISION = '264b34c9a0762bdadda377fb10cb44a63af33052'
EXPECTED_SOURCE = 'b69fd4f0100a2a9f5f5e4c266e4e68ee3e35af3dc5be91d010be9b325e97b62d'
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from integration_evidence import source_identity


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    assert not OUT.exists(), 'Preserve previous attempts'
    OUT.mkdir(parents=True)
    before = source_identity(PROJECT, REVISION)
    assert before['sourceTreeSha256'] == EXPECTED_SOURCE
    receipt = {
        'format': 'source_report_refresh_v1',
        'scope': 'source-only report freshness; no native or release acceptance',
        'baselineRevision': REVISION, 'worktreeDirty': True,
        'sourceIdentity': before, 'nativeStatus': 'not_run',
        'startedAt': datetime.now(timezone.utc).isoformat(),
        'commands': [], 'status': 'running',
    }
    write(OUT / 'receipt.json', receipt)
    commands = [
        ('runtime', [sys.executable, '-B', 'tooling/runtime_acceptance.py', '--write', '--source-revision', REVISION], 1),
        ('release', [sys.executable, '-B', 'tooling/release_blocker_audit.py', '--write', '--source-revision', REVISION], 1),
        ('traceability', [sys.executable, '-B', 'tooling/requirement_traceability_audit.py', '--write', '--check', '--source-revision', REVISION], 0),
        ('report-freshness', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_release_blocker_audit.py', '-k', 'test_checked_in_machine_and_human_reports_are_current', '-v'], 0),
        ('diff-check', ['git', 'diff', '--check'], 0),
    ]
    try:
        for name, command, expected in commands:
            started = time.monotonic()
            result = subprocess.run(command, cwd=PROJECT, capture_output=True)
            (OUT / (name + '.stdout')).write_bytes(result.stdout)
            (OUT / (name + '.stderr')).write_bytes(result.stderr)
            row = {'name': name, 'command': command, 'exitCode': result.returncode,
                   'expectedExitCode': expected, 'elapsedSeconds': round(time.monotonic() - started, 3),
                   'stdoutSha256': hashlib.sha256(result.stdout).hexdigest(),
                   'stderrSha256': hashlib.sha256(result.stderr).hexdigest()}
            receipt['commands'].append(row)
            write(OUT / 'receipt.json', receipt)
            print(json.dumps(row), flush=True)
            assert result.returncode == expected, name + ': unexpected exit'
        runtime = json.loads((PROJECT / 'reports/runtime-acceptance.json').read_text())
        trace = json.loads((PROJECT / 'reports/traceability/requirements.json').read_text())
        release_summary = json.loads((OUT / 'release.stdout').read_text())
        receipt.update(runtimeFailures=len(runtime['failures']),
                       releaseBlockers=release_summary['unresolvedCampaignBlockers'],
                       traceabilityBlockers=trace['blockerCount'])
        assert [receipt['runtimeFailures'], receipt['releaseBlockers'], receipt['traceabilityBlockers']] == [30, 238, 7004]
        assert runtime['releaseReady'] is False and trace['candidateReady'] is False
        receipt['sourcesUnchanged'] = source_identity(PROJECT, REVISION) == before
        assert receipt['sourcesUnchanged']
        receipt['status'] = 'pass_freshness_with_acceptance_still_blocked'
    except BaseException as error:
        receipt.update(status='fail', error=str(error), errorType=type(error).__name__)
        raise
    finally:
        receipt['finishedAt'] = datetime.now(timezone.utc).isoformat()
        write(OUT / 'receipt.json', receipt)


if __name__ == '__main__':
    main()
