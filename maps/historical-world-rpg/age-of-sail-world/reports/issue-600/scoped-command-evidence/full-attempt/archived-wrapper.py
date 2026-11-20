from pathlib import Path
import sys, os, json, subprocess
base=Path('/workspace/scratch/d496e51c7d30')
repo=base/'wc3-ci-followup-20261118'
project=repo/'maps/historical-world-rpg/age-of-sail-world'
sys.path[:0]=[str(project.parent/'_shared/tooling'),str(project/'tooling')]
from focused_wurst_replay import assemble, snapshot, clean_revision, require_local_tooling
from integration_evidence import source_identity
from wurst_execution import execute_tests, toolchain_environment
revision='6b6a3dacc58fe59876bb9066b5024fc46b9f401c'
out=base/'wc3-full-6b6a-validation'
home=base/'wc3-pinned-toolchain/root/home/wurstuser'
exe=home/'.wurst/grill'; compiler=home/'.wurst/wurst-compiler/wurstscript.jar'
require_local_tooling(project); clean_revision(project,revision)
out.mkdir(exist_ok=False)
identity=source_identity(project,revision)
root=assemble(project,out,base/'wc3-help-3c0b-validation/compile/_build')
frozen=snapshot(root,exe,compiler)
(out/'pretypecheck-inputs.json').write_text(json.dumps(frozen,indent=2))
def unchanged():
    clean_revision(project,revision)
    assert source_identity(project,revision)==identity
    assert snapshot(root,exe,compiler)==frozen
os.environ['HOME']=str(home)
os.environ['JAVA_TOOL_OPTIONS']=f'-Xmx8g -Duser.home={home}'
os.environ.pop('WURST_IMAGE',None)
receipt={'scope':'Full production Python execution gate with extracted compiler, not Docker/native acceptance','sourceRevision':revision,'sourceIdentity':identity,'completed':False}
try:
    unchanged()
    with (out/'typecheck.log').open('w') as f:
        subprocess.run([str(exe),'typecheck'],cwd=root,env=toolchain_environment(),stdout=f,stderr=subprocess.STDOUT,check=True)
    unchanged()
    execute_tests(root,str(exe),out/'evidence',revision,project=project)
    unchanged()
    receipt['completed']=True
finally:
    receipt['unchangedAtTermination']=snapshot(root,exe,compiler)==frozen and source_identity(project,revision)==identity
    (out/'wrapper-scope.json').write_text(json.dumps(receipt,indent=2))
