from pathlib import Path
import sys,os,shutil,json,subprocess
base=Path('/workspace/scratch/d496e51c7d30');repo=base/'wc3-land-idle';project=repo/'maps/historical-world-rpg/age-of-sail-world';out=base/'wc3-land-idle-validation-attempt2';out.mkdir(exist_ok=False)
sys.path[:0]=[str(repo/'maps/historical-world-rpg/_shared/tooling'),str(project/'tooling')]
from package_wurst_map import load_config,generate,verify_generated,_assemble
from wurst_execution import input_hashes,discover,parse_results,compiler_identity,PINNED_IMAGE
cfg=load_config(project/'package.json');generate(cfg,out/'generated');verify_generated(cfg,out/'generated');root=_assemble(cfg,out,out/'generated');b=root/'wurst.build';b.write_text(b.read_text().replace('wurstscript/WurstStdlib2','wurstscript/wurstStdlib2'))
shutil.copytree(base/'wc3-questcheck-validation-1ddf23fb/compile/_build/dependencies/wurstStdlib2',root/'_build/dependencies/wurstStdlib2')
home=base/'wc3-pinned-toolchain/root/home/wurstuser';os.environ['HOME']=str(home);os.environ['JAVA_TOOL_OPTIONS']=f'-Xmx8g -Duser.home={home}';os.environ['WURST_IMAGE']=PINNED_IMAGE;exe=str(home/'.wurst/grill')
with (out/'typecheck.log').open('w') as f:subprocess.run([exe,'typecheck'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
inputs=input_hashes(root);(out/'inputs.json').write_text(json.dumps(inputs,indent=2))
for pkg in ['LandArmyEffectsTests']:
 with (out/f'{pkg}.log').open('w') as f:r=subprocess.run([exe,'test',pkg],cwd=root,stdout=f,stderr=subprocess.STDOUT)
 log=(out/f'{pkg}.log').read_text();expected=[t for t in discover(root) if t['id'].startswith('wurst/'+pkg+'.wurst:')];rows,issues=parse_results(log,expected);report={'scope':'focused only; not full or native acceptance','sourceRevision':'2ee66c55562ae62008a68c14716b86efbd7c6a96','compiler':compiler_identity(log),'returnCode':r.returncode,'tests':rows,'issues':issues,'inputsUnchanged':inputs==input_hashes(root)};(out/f'{pkg}.json').write_text(json.dumps(report,indent=2));print(pkg,len(rows),r.returncode,issues,report['inputsUnchanged'],flush=True)
 if r.returncode or issues or not report['inputsUnchanged']:break
