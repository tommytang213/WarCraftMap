set -eu
mkdir -p /tmp/issue469
cd /source
tar --exclude=.git --exclude=./.agents --exclude=./.aws --exclude=./.codex --exclude=_build --exclude=__pycache__ -cf - maps automation .github AGENTS.md | tar -C /tmp/issue469 -xf -
mkdir -p /tmp/issue469-tools
cp /dependencies/usr/bin/python3.14 /tmp/issue469-tools/python3
export PYTHONHOME=/dependencies/usr
export PATH=/tmp/issue469-tools:/home/wurstuser/.wurst:$PATH
cat > /tmp/issue469-tools/grill <<'GRILL'
#!/bin/sh
set -eu
mkdir -p _build/dependencies
if [ ! -d _build/dependencies/WurstStdlib2 ]; then
  cp -R /dependencies/tmp/issue383-package/age-of-sail-world/_build/compile/_build/dependencies/wurstStdlib2 _build/dependencies/WurstStdlib2
fi
if [ "$1" = install ]; then
  printf '%s\n' "$PWD/_build/dependencies/WurstStdlib2" > wurst.dependencies
  python3 - <<'CORE'
from pathlib import Path
from zipfile import ZipFile
jar=ZipFile('/home/wurstuser/.wurst/grill-cli/grill.jar')
for name in ('common.j','blizzard.j'):
    Path('_build',name).write_bytes(jar.read('core-jass/v3.0/'+name))
CORE
  exit 0
fi
exec /home/wurstuser/.wurst/grill "$@"
GRILL
chmod +x /tmp/issue469-tools/grill
cd /tmp/issue469/maps/historical-world-rpg/age-of-sail-world
python3 - <<'CHECK'
import os, sys, re, subprocess, shutil, contextlib, json
from pathlib import Path
sys.path.insert(0,'../_shared/tooling')
from package_wurst_map import load_config,generate,_assemble,_run,_find_archive,_inspect
from wurst_execution import execute_tests, toolchain_environment
config=load_config(Path('package.json'));root=Path('_build/issue469')
if root.exists():
    shutil.rmtree(root)
root.mkdir(parents=True)
generate(config,root/'generated');comp=_assemble(config,root,root/'generated')
if os.environ.get('COMBAT_TARGETED') == '1':
    keep={'MilitaryCombatEventsTests.wurst', 'MilitarySettlementRuntimeTests.wurst', 'MilitaryOrderEventsTests.wurst', 'ExactNaturalTests.wurst', 'ExactRationalTests.wurst', 'AbstractSettlementTests.wurst', 'CampaignLoadTransactionTests.wurst', 'CampaignStartupTests.wurst', 'WarcraftRpgRuntimeTests.wurst'}
    if os.environ.get('COMBAT_SMOKE') == '1':
        keep={'MilitaryCombatEventsTests.wurst', 'ExactRationalTests.wurst'}
    for p in (comp/'wurst').glob('*.wurst'):
        if p.name not in keep:
            p.write_text(p.read_text().replace('@test',''))
_run('offline dependencies',['/tmp/issue469-tools/grill','install'],comp)
print('Running pinned typecheck',flush=True)
typed = subprocess.run(['/tmp/issue469-tools/grill','typecheck'],cwd=comp,env=toolchain_environment(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(root/'typecheck.log').write_text(typed.stdout)
assert typed.returncode == 0, typed.stdout
if os.environ.get('TYPECHECK_ONLY') == '1':
    sys.exit(0)
if os.environ.get('PACKAGE_ONLY') != '1':
    print('Running pinned execution',flush=True)
    try:
        with (root/'execution-gate.log').open('w') as output, contextlib.redirect_stdout(output):
            execute_tests(comp,'/tmp/issue469-tools/grill',root/'evidence',os.environ['SOURCE_REVISION'],project=config.project)
    except Exception:
        report = json.loads((root/'evidence/results.json').read_text())
        print('Failed tests:', [row for row in report['tests'] if row['status'] != 'pass'], flush=True)
        raise
    print('Pinned tests passed', flush=True)
    print('Execution complete',flush=True)
if os.environ.get('COMBAT_FRAMEWORK') == '1':
    print('Checking original and mutated framework campaigns',flush=True)
    result = subprocess.run(['python3','../_shared/tooling/validate_framework_fixture.py','../conformance-campaign'],
                            cwd=config.project,env=toolchain_environment(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (root/'framework-validation.log').write_text(result.stdout)
    assert result.returncode == 0, result.stdout[-4000:]
    print('Framework campaigns passed',flush=True)
CHECK
