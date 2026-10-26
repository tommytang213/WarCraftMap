#!/usr/bin/env python3
"""Run existing Wurst gates with pinned tools and newly generated source inputs."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, shutil, subprocess, sys, time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'WarCraftMap'
PROJECT=REPO/'maps/historical-world-rpg/age-of-sail-world'
PREVIOUS=Path('/workspace/scratch/243ebc79fa0a')
LAUNCHER=ROOT/'toolchain/grill'
DEPENDENCY=PREVIOUS/'pinned-wurst/WurstStdlib2'
COMPILER=ROOT/'toolchain/home/.wurst/wurst-compiler/wurstscript.jar'
sys.path.insert(0,str(PROJECT.parent/'_shared/tooling'))
from integration_evidence import execution_sources, source_identity, verify_execution_coverage
from package_wurst_map import load_config, generate, verify_generated, _assemble
from wurst_execution import discover, execute_tests, select_tests, input_hashes, verify_evidence, canonical, PINNED_COMPILER_SHA256, WurstExecutionError

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args,cwd=REPO): return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def write(p,data):
    temporary=p.with_suffix(p.suffix+'.part')
    temporary.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n'); os.replace(temporary,p)
def depstate(p):
    return {'revision':git('rev-parse','HEAD',cwd=p),'dirty':bool(git('status','--porcelain',cwd=p)),
            'files':{x.relative_to(p).as_posix():sha(x) for x in sorted(p.rglob('*')) if x.is_file() and '.git' not in x.relative_to(p).parts}}
def sources(): return {p:sha(f) for p,f in sorted(execution_sources(PROJECT).items())}
def now(): return datetime.now(timezone.utc).isoformat()
def assert_no_compiler():
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit(): continue
        try: cmd=(proc/'cmdline').read_bytes().split(b'\0')
        except OSError: continue
        assert not (cmd and cmd[0].endswith(b'/java') and any(a.endswith(b'/wurstscript.jar') for a in cmd)), 'Another compiler is running'

def prepare():
    out=ROOT/'seed';assert not out.exists(),'Preserve existing assembly'
    out.mkdir();revision=git('rev-parse','HEAD');identity=source_identity(PROJECT,revision)
    assert sha(COMPILER)==PINNED_COMPILER_SHA256
    dependency=depstate(DEPENDENCY)
    assert dependency['revision']=='cce79096e71dcb066cf94785bc5cb48ef66c26db' and not dependency['dirty']
    config=load_config(PROJECT/'package.json')
    print('Generating current merged scenario and settings',flush=True)
    generate(config,out/'generated');verify_generated(config,out/'generated')
    compile_root=_assemble(config,out,out/'generated',include_tests=True)
    shutil.copytree(DEPENDENCY,compile_root/'_build/dependencies/WurstStdlib2')
    for name in ['common.j','blizzard.j']:
        shutil.copy2(PREVIOUS/'validation-536/continue-fix/test-seed/_build'/name,compile_root/'_build'/name)
    discovered=discover(compile_root)
    assert discovered==discover(PROJECT,sources=execution_sources(PROJECT))
    assert source_identity(PROJECT,revision)==identity
    receipt={'sourceIdentity':identity,'baselineReference':revision,'sourceState':'working_tree',
             'authoredInputs':sources(),'generatedInputs':{p.name:sha(p) for p in (compile_root/'wurst').glob('Scenario*.wurst')},
             'dependency':dependency,'compilerSha256':sha(COMPILER),'discovered':len(discovered),
             'nativeStatus':'not_run','playerArtifactProduced':False,'createdAt':now()}
    write(out/'receipt.json',receipt);write(out/'discovery.json',discovered)
    print(json.dumps({'prepared':str(compile_root),'tests':len(discovered),'sourceTreeSha256':identity['sourceTreeSha256']}),flush=True)

def run(mode,label):
    out=ROOT/label;assert not out.exists(),'Preserve previous attempt'
    assert_no_compiler();out.mkdir()
    revision=git('rev-parse','HEAD');identity=source_identity(PROJECT,revision)
    seed=ROOT/'seed';seed_receipt=json.loads((seed/'receipt.json').read_text())
    assert sources()==seed_receipt['authoredInputs'],'Refresh assembly explicitly if authored input changes'
    compile_root=out/'compile';shutil.copytree(seed/'compile',compile_root)
    receipt={'mode':mode,'sourceRevision':revision,'sourceState':'clean_committed_tree' if not git('status','--porcelain') else 'working_tree',
             'sourceIdentity':identity,'startedAt':now(),'nativeStatus':'not_run','playerArtifactProduced':False,
             'toolchain':'verified extracted pinned compiler and JDK on workspace host; full OCI image not run',
             'compilerSha256':sha(COMPILER),'javaToolOptions':'-Xmx6g','repositoryGateModified':False,'repositoryTestDeadlineModified':False}
    expected=discover(compile_root)
    if mode=='focused':
        families={'TradeSnapshotTests.wurst','MilitarySnapshotValidationTests.wurst','CampaignStartupTests.wurst'}
        expected=[t for t in expected if Path(t['id'].split(':')[0]).name in families]
    elif mode=='negative-guard':
        names={'emptySessionEncodingPreservesPendingStartupAndCanRetry','emptyMilestoneEncodingPreservesPendingStartupAndCanRetry'}
        expected=[t for t in expected if t['id'].split(':')[-1] in names]
        assert len(expected)==2
        file=compile_root/'wurst/PlayableCampaignRuntime.wurst';text=file.read_text()
        for slot,var in [('session_start','session'),('major_milestone','milestone')]:
            before='if '+var+' == "" or not saves.storage.writeTransactional("'+slot+'", '+var+')'
            assert text.count(before)==1
            text=text.replace(before,'if not saves.storage.writeTransactional("'+slot+'", '+var+')')
        file.write_text(text)
        receipt['negativeControl']='Only the two newly added empty-encoding guards are removed from this copied assembly'
    if mode!='full':
        for p in (compile_root/'wurst').rglob('*.wurst'):
            names={t['id'].split(':')[-1] for t in expected if compile_root/t['id'].split(':')[0]==p}
            p.write_text(select_tests(p.read_text(),names))
        assert discover(compile_root)==expected
    before=input_hashes(compile_root);dep_before=depstate(compile_root/'_build/dependencies/WurstStdlib2')
    assert not dep_before['dirty'] and dep_before==seed_receipt['dependency']
    write(out/'compiler-inputs-before.json',before);write(out/'dependency-before.json',dep_before)
    write(out/'discovery.json',expected);receipt['testCount']=len(expected);write(out/'receipt.json',receipt)
    os.environ['JAVA_TOOL_OPTIONS']='-Xmx6g'
    print('Running '+mode+': '+str(len(expected))+' tests',flush=True)
    start=time.monotonic()
    try:
        result=None
        try: result=execute_tests(compile_root,str(LAUNCHER),out,revision,project=PROJECT if mode=='full' else None)
        except WurstExecutionError:
            if mode!='negative-guard': raise
            result=json.loads((out/'results.json').read_text())
        if mode=='negative-guard':
            assert result['discovered']==2 and result['succeeded']==0 and result['executionStatus']=='completed'
            assert len(result['tests'])==2 and all(x['status']=='assertion_failed' for x in result['tests'])
            log=(out/'execution.log').read_text()
            assert 'Exception' not in log and 'No builtin function' not in log and 'Error in File' not in log
            receipt['status']='expected_assertion_failures';receipt['negativeControlVerified']=True
        else:
            verify_evidence(result,(out/'execution.log').read_bytes(),revision)
            assert result['expected']==expected
            if mode=='full': receipt['productionCoverage']=verify_execution_coverage(result,(out/'execution.log').read_bytes(),PROJECT,revision)
            receipt['status']='pass'
        assert input_hashes(compile_root)==before
        assert depstate(compile_root/'_build/dependencies/WurstStdlib2')==dep_before
        assert sources()==seed_receipt['authoredInputs']
        assert source_identity(PROJECT,revision)==identity
        receipt.update(discovered=result['discovered'],succeeded=result['succeeded'],sourceInputsUnchanged=True,compilerInputsUnchanged=True,dependencyInputsUnchanged=True)
    except BaseException as e:
        receipt.update(status='fail',error=type(e).__name__+': '+str(e));raise
    finally:
        receipt.update(finishedAt=now(),wallSeconds=round(time.monotonic()-start,3));write(out/'receipt.json',receipt)
        write(out/'compiler-inputs-after.json',input_hashes(compile_root))
    print(json.dumps({k:receipt[k] for k in ['status','discovered','succeeded','wallSeconds']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','focused','full','negative-guard']);p.add_argument('--label');args=p.parse_args()
    if args.mode=='prepare':prepare()
    else:run(args.mode,args.label or args.mode)
