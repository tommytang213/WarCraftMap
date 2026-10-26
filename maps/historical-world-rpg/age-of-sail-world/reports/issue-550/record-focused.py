"""Retain focused development evidence; never output a full-suite release result."""
from pathlib import Path
import gzip,json,re,sys
project=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(project.parent/'_shared/tooling'),str(project/'tooling')]
from wurst_execution import parse_results,sha,canonical,PINNED_COMPILER_SHA256,PINNED_IMAGE,source_revision
from integration_evidence import source_identity,load_contract,observed_probes
from land_army_catalog import COMPARATIVE_PATHS
folder=Path(__file__).resolve().parent
repo=project.parents[2];root=project/'_build/issue-550'
identity=source_identity(project,source_revision(project))

def retain(name,build,raw):
    expected=json.loads((build/'expected.json').read_text())
    rows,errors=parse_results(raw.decode(),expected)
    assert not errors,errors
    assert len(rows)==len(expected) and all(row['status']=='pass' for row in rows)
    inputs=json.loads((build/'inputs.json').read_text())
    log=raw.decode()
    assert '/home/wurstuser/.wurst/wurst-compiler/wurstscript.jar: OK' in log
    for path,digest in inputs.items():
        assert sha((build/'compile'/path).read_bytes())==digest,path
        assert log.count(path+': OK')>=2,path
    result=dict(format='warcraftmap_focused_wurst_v1',status='pass',sourceIdentity=identity,
                expected=expected,tests=rows,compilerSha256=PINNED_COMPILER_SHA256,pinnedImage=PINNED_IMAGE,
                inputSetSha256=sha(canonical(inputs)),logSha256=sha(raw),fullSuite=False,nativeClient='not_run')
    if name=='focused':
        probes=observed_probes(log,rows,load_contract(project))
        for pair,(system,test,required) in COMPARATIVE_PATHS.items():
            assert required<=set(probes['wurst/LandArmyEffectsTests.wurst:'+test]),system
        result['productionCoverage']=probes
    (folder/(name+'-results.json')).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (folder/(name+'-wurst.log.gz')).write_bytes(gzip.compress(raw,mtime=0))
    return len(rows)
counts={}
counts['focused']=retain('focused',root,(repo/'_build/issue-550/focused-wurst.log').read_bytes())
raw=(repo/'_build/issue-550/framework-wurst.log').read_bytes()
starts=[m.start() for m in re.finditer(rb'^Running tests\r?$',raw,re.M)]
assert len(starts)==2
# Include the preceding compiler and input checks in each variant's transcript.
cut=raw.index(b'/home/wurstuser/.wurst/wurst-compiler/wurstscript.jar: OK',starts[0])
for name,log in [('original',raw[:cut]),('mutated',raw[cut:])]:
    counts[name]=retain('framework-'+name,root/'framework'/(name+'-build'),log)
for name in ('shipping-build','boundary','payload-inspection','packaged-inspection','audits','research-generation','audit-tests','affected-python'):
    path=repo/('_build/issue-550/'+name+'.log')
    if path.exists():(folder/(name+'.log.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
python_checks = {}
for name, count in [('research-generation', 11), ('audit-tests', 93)]:
    log=(repo/('_build/issue-550/'+name+'.log')).read_text()
    assert re.search(r'Ran '+str(count)+r' tests in ', log) and '\nOK\n' in log
    python_checks[name]=dict(tests=count,status='pass')
initial=(repo/'_build/issue-550/affected-python.log').read_text()
assert 'Ran 80 tests in ' in initial and 'FAILED (failures=1)' in initial
assert 'FAIL: test_all_220_typed_unlocks_and_13_multi_unlock_nodes_are_retained' in initial
python_checks['affected-before-expectation-update']=dict(tests=80,passed=79,failed=1,
    resolution='The sole stale generated-blocker expectation was corrected; all 11 generation tests then passed.')
assert 'OK: framework content and implementation boundary' in (repo/'_build/issue-550/boundary.log').read_text()
(folder/'validation.json').write_text(json.dumps(dict(sourceIdentity=identity,pinnedWurstTests=counts,pythonChecks=python_checks,distinctAffectedPythonCases=168,nativeClient='not_run',fullRepositoryValidation='controller after integration preflight'),indent=2,sort_keys=True)+'\n')
print(counts)
