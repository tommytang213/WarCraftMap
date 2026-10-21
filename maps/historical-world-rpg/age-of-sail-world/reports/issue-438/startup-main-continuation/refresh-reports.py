#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,sys,hashlib,time
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'WarCraftMap';PROJECT=REPO/'maps/historical-world-rpg/age-of-sail-world'
sys.path.insert(0,str(PROJECT.parent/'_shared/tooling'))
from integration_evidence import source_identity
revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
OUT=ROOT/'source-reports';assert not OUT.exists(),'Preserve previous report refresh';OUT.mkdir()
before=source_identity(PROJECT,revision)
receipt={'format':'pr536_continuation_source_report_refresh_v1','baselineRevision':revision,'sourceIdentity':before,'nativeStatus':'not_run','startedAt':datetime.now(timezone.utc).isoformat(),'commands':[]}
for name,script,args,code in [('runtime','runtime_acceptance.py',['--write'],1),('release','release_blocker_audit.py',['--write'],1),('traceability','requirement_traceability_audit.py',['--write','--check'],0)]:
 command=[sys.executable,'-B','tooling/'+script,*args,'--source-revision',revision]
 t=time.monotonic();r=subprocess.run(command,cwd=PROJECT,capture_output=True)
 (OUT/(name+'.stdout')).write_bytes(r.stdout);(OUT/(name+'.stderr')).write_bytes(r.stderr)
 item={'name':name,'command':command,'exitCode':r.returncode,'expectedExitCode':code,'seconds':round(time.monotonic()-t,3),'stdoutSha256':hashlib.sha256(r.stdout).hexdigest(),'stderrSha256':hashlib.sha256(r.stderr).hexdigest()}
 receipt['commands'].append(item);(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(item),flush=True)
 assert r.returncode==code,(name,r.returncode,r.stdout[-500:],r.stderr[-1000:])
assert source_identity(PROJECT,revision)==before
runtime=json.loads((PROJECT/'reports/runtime-acceptance.json').read_text());trace=json.loads((PROJECT/'reports/traceability/requirements.json').read_text())
assert runtime['releaseReady'] is False and trace['candidateReady'] is False
receipt.update(status='source_freshness_only_native_and_release_remain_blocked',runtimeFailures=len(runtime['failures']),traceabilityBlockers=trace['blockerCount'],sourcesUnchanged=True,finishedAt=datetime.now(timezone.utc).isoformat())
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
