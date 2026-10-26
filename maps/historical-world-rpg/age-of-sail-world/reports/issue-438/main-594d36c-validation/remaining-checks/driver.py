"""Run unchanged static/automation commands omitted by the PR workflows.

This is a component check, never a substitute receipt for run_checks.sh.
"""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / 'WarCraftMap'
OUT = ROOT / 'remaining-checks-attempt2'
COMMIT = '791ce7f44944af124fe87400d2f1ecfa5882240b'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip() == COMMIT
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=REPO, text=True).strip()
OUT.mkdir(exist_ok=False)
sys.path.insert(0, str(REPO / 'maps/historical-world-rpg/_shared/tooling'))
from integration_evidence import source_identity
project = REPO / 'maps/historical-world-rpg/age-of-sail-world'
before = source_identity(project, COMMIT)
commands = [
    ['python3', 'maps/historical-world-rpg/_shared/tooling/audit_framework_boundary.py'],
    ['python3', 'maps/historical-world-rpg/_shared/tooling/validate_world.py', 'maps/historical-world-rpg/conformance-campaign/scenario/world/world.json'],
    ['python3', 'maps/historical-world-rpg/_shared/tooling/validate_world.py', 'maps/historical-world-rpg/age-of-sail-world/scenario/world/world.json'],
    ['python3', 'maps/historical-world-rpg/age-of-sail-world/tooling/europe_geography.py'],
    ['python3', 'maps/historical-world-rpg/age-of-sail-world/tooling/validate_map_source.py'],
    ['python3', 'maps/historical-world-rpg/age-of-sail-world/tooling/requirement_traceability_audit.py', '--check'],
    ['python3', '-m', 'unittest', 'discover', '-s', 'automation/tests', '-p', 'test_*.py'],
]
receipt = {'status': 'running', 'testedCommit': COMMIT, 'sourceIdentity': before,
           'scope': 'Unchanged static checks and automation suite; full project Python/Wurst verification delegated to existing PR CI. Canonical local gate did not pass.',
           'nativeStatus': 'not_run', 'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'commands': []}
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
def save():
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
save()
for i, command in enumerate(commands):
    log = OUT / f'{i+1:02d}.log'
    with log.open('w') as f:
        result = subprocess.run(command, cwd=REPO, env=env, stdout=f, stderr=subprocess.STDOUT)
    receipt['commands'].append({'command': command, 'exitCode': result.returncode, 'log': log.name,
        'logSha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'logBytes': log.stat().st_size})
    save()
    print(json.dumps(receipt['commands'][-1]), flush=True)
receipt['sourceUnchanged'] = source_identity(project, COMMIT) == before
receipt['worktreeClean'] = not subprocess.check_output(['git', 'status', '--porcelain'], cwd=REPO, text=True).strip()
receipt['status'] = 'pass_component_checks' if receipt['sourceUnchanged'] and receipt['worktreeClean'] and all(c['exitCode'] == 0 for c in receipt['commands']) else 'failed'
receipt['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
save()
print(json.dumps(receipt), flush=True)
sys.exit(0 if receipt['status'] == 'pass_component_checks' else 1)
