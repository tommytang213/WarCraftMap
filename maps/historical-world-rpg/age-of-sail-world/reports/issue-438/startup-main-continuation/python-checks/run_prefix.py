import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path('/workspace/scratch/37daecc7d55a/WarCraftMap')
OUT = Path('/workspace/scratch/37daecc7d55a/validation-536-continuation/python-checks')
EXPECTED_HEAD = 'd6697380d979f96b2f3543593c6383402ba26e5b'
EXPECTED_SOURCE = 'd08445f912a604b5fdb43beed2ec9573904075beb2e1ed6c40771df75852be37'
PROJECT = ROOT / 'maps/historical-world-rpg/age-of-sail-world'
sys.path.insert(0, str(ROOT / 'maps/historical-world-rpg/_shared/tooling'))
from integration_evidence import source_identity

def git(*args):
    return subprocess.run(['git', '--no-optional-locks', *args], cwd=ROOT,
                          check=True, stdout=subprocess.PIPE).stdout

def snapshot():
    head = git('rev-parse', 'HEAD').decode().strip()
    paths = git('ls-files', '-z').split(b'\0')
    files = {}
    for path in paths:
        if path:
            name = os.fsdecode(path)
            files[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    canonical = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
    return {'head': head, 'statusPorcelain': git('status', '--porcelain=v1').decode(),
            'gitTree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
            'sourceIdentity': source_identity(PROJECT, head),
            'trackedFileCount': len(files),
            'trackedContentSha256': hashlib.sha256(canonical).hexdigest()}

OUT.mkdir(parents=True, exist_ok=True)
before = snapshot()
(OUT / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
assert before['head'] == EXPECTED_HEAD, before
assert before['sourceIdentity']['sourceTreeSha256'] == EXPECTED_SOURCE, before
assert before['statusPorcelain'] == '', before

receipt = {'format': 'warcraftmap-pr536-python-prefix-v1',
           'scope': 'Source and Python validation prefix only; Wurst execution explicitly skipped here and independently run by root.',
           'command': ['bash', 'automation/run_checks.sh'],
           'environmentOverride': {'WARCRAFTMAP_WURST_CHECK': 'skip', 'PYTHONDONTWRITEBYTECODE': '1'},
           'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status': 'running', 'before': before}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': 'started', 'head': before['head'], 'source': EXPECTED_SOURCE, 'log': str(OUT / 'execution.log')}), flush=True)
env = os.environ.copy()
env['WARCRAFTMAP_WURST_CHECK'] = 'skip'
env['PYTHONDONTWRITEBYTECODE'] = '1'
start = time.monotonic()
with (OUT / 'execution.log').open('wb') as log:
    completed = subprocess.run(['bash', 'automation/run_checks.sh'], cwd=ROOT,
                               env=env, stdout=log, stderr=subprocess.STDOUT)
elapsed = time.monotonic() - start
after = snapshot()
(OUT / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
raw = (OUT / 'execution.log').read_bytes()
text = raw.decode('utf-8', errors='replace')
receipt.update({'status': 'completed', 'exitCode': completed.returncode,
                'endedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'durationSeconds': elapsed, 'after': after,
                'beforeAfterIdentical': before == after,
                'logSha256': hashlib.sha256(raw).hexdigest(), 'logBytes': len(raw),
                'unittestSummaries': [{'tests': int(n), 'durationSeconds': float(t)}
                                      for n, t in re.findall(r'^Ran (\d+) tests? in ([0-9.]+)s', text, re.MULTILINE)],
                'wurstSkippedWarningPresent': 'WARNING: Wurst typecheck and execution skipped by explicit WARCRAFTMAP_WURST_CHECK=skip' in text,
                'fullWurstGateSatisfiedByThisRun': False})
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2), flush=True)
print('\nLAST LOG LINES\n' + '\n'.join(text.splitlines()[-55:]), flush=True)
if not receipt['beforeAfterIdentical']:
    raise SystemExit('Source/head/tracked contents changed during the prefix run')
raise SystemExit(completed.returncode)
