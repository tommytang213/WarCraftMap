#!/usr/bin/env python3
"""Bounded, supplementary profiling of actual archived Lua; never a native gate."""
import ctypes
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

ROOT=Path('/workspace/scratch/243ebc79fa0a')
OUT=ROOT/'validation-536/native-boundary-audit/startup-observer-collision32'
EVIDENCE=ROOT/'WarCraftMap/maps/historical-world-rpg/age-of-sail-world/reports/issue-438/trade-startup'
SCRIPT=ROOT/'validation-536/startup-candidate/extracted/europe_central_east/war3map.lua'
RECEIPT=ROOT/'validation-536/startup-candidate/final-europe-build-receipt.json'
LIBRARY=ROOT/'validation-536/lua53-runtime/liblua5.3.6-probe.so'

def identity(path):
 data=path.read_bytes()
 return dict(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

report=dict(format='supplemental_final_candidate_startup_cost_and_first_callbacks_v1',
 status='failed',nativeStatus='not_run',releaseStatus='not_a_release_gate',
 limitations=[
  'Unchanged actual archived Lua, observed through delegating function wrappers; this is not a production function identity gate.',
  'Frozen explicit synthetic native model, collision-free StringHash and successful in-memory cache writes; engine native latency and limits absent.',
  'Supplementary timer model advances only after main returns, chooses registration order for tied deadlines, and executes only through 1.001 simulated seconds.',
  'Additional callback model: synthetic collision radius32, all modeled units visible and nonflying. These are explicit defaults, not object-data measurements.',
  'First periodic timer/trigger callbacks can run; unit events, collisions, preplaced units, assets, rendering, real persistence and operating-system scheduling remain absent.',
  'Observed instruction samples include Lua stubs and measurement overhead; 2B startup and 200M callback budgets are local safety bounds, not Warcraft limits.',
  'Exact embedded Warcraft Lua patch version is unverified. Timing is stock Lua5.3.6 with these observers, not native load time.',
 ])
state=None
began=time.monotonic()
try:
 harness=EVIDENCE/'probe-lua54-initialization.py'
 stubs=EVIDENCE/'late-startup-stubs.lua'
 assert identity(harness)['sha256']=='b3bd4b946cd4ceb9b46a7c254fb1c9d498868c9deae31cf72836ff8dc1225948'
 assert identity(stubs)['sha256']=='3c7eda8627f7ba5d4c3d3f49328be834d7598f1e8616462f665b02ae8cdaa630'
 assert identity(SCRIPT)['sha256']==json.loads(RECEIPT.read_text())['compiledScriptSha256']=='a4fc97bb27b36466bc62bad74605128258c6847c4f46791efe2df184c3f85a45'
 report['inputs']={name:identity(path) for name,path in dict(compiledLua=SCRIPT,buildReceipt=RECEIPT,
  harness=harness,nativeStubs=stubs,observer=OUT/'observe-startup.lua',runner=Path(__file__),library=LIBRARY).items()}
 os.environ['WC3_LUA_PROBE_LIBRARY']=str(LIBRARY)
 spec=importlib.util.spec_from_file_location('frozen_startup_probe',harness)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 lib=module.lib
 ptr=ctypes.CFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t))(('lua_tolstring',lib))
 state=lib.luaL_newstate();assert state;lib.luaL_openlibs(state)
 def get_bytes(name):
  lib.lua_getglobal(state,name.encode());size=ctypes.c_size_t();address=ptr(state,-1,ctypes.byref(size))
  assert address,name
  data=ctypes.string_at(address,size.value);lib.lua_settop(state,0);return data
 report['runtimeVersion']=get_bytes('_VERSION').decode()
 assert report['runtimeVersion']=='Lua 5.3'
 status=lib.luaL_loadfilex(state,str(SCRIPT).encode(),b't')
 if not status: status=lib.lua_pcallk(state,0,0,0,0,None)
 if status: raise RuntimeError(lib.lua_tolstring(state,-1,None).decode(errors='replace'))
 module.execute(state,module.PRELUDE)
 module.execute(state,stubs.read_text())
 module.execute(state,(OUT/'observe-startup.lua').read_text())
 for phase in ['startup','callbacks']:
  phase_began=time.monotonic()
  try: module.execute(state,'__audit_'+phase+'()')
  finally:
   module.execute(state,'debug.sethook();__audit_json=__probe.json(__audit)')
   report['execution']=json.loads(get_bytes('__audit_json'))
   report.setdefault('phaseWallSeconds',{})[phase]=round(time.monotonic()-phase_began,6)
   print(json.dumps({'phase':phase,'wallSeconds':report['phaseWallSeconds'][phase]},sort_keys=True),flush=True)
  if phase=='startup':
   for index,row in enumerate(report['execution']['cacheWrites'],1):
    module.execute(state,'__audit_payload=__audit_payloads['+str(index)+']')
    data=get_bytes('__audit_payload')
    path=OUT/('cache-write-'+str(index)+'.txt.gz')
    assert not path.exists(),'Refusing to overwrite prior observer payload'
    path.write_bytes(gzip.compress(data,mtime=0))
    row['sha256']=hashlib.sha256(data).hexdigest();row['compressed']=identity(path)
   report['cachePayloads']=report['execution']['cacheWrites']
 assert identity(SCRIPT)==report['inputs']['compiledLua']
 assert len(report['execution']['callbackErrors'])==0
 report['status']='completed_under_explicit_stubs'
except Exception as exc:
 report['error']=str(exc)
finally:
 if state: lib.lua_close(state)
 report['wallSeconds']=round(time.monotonic()-began,6)
 destination=OUT/'startup-and-first-callbacks.json'
 assert not destination.exists(),'Refusing to overwrite prior observer report'
 temporary=destination.with_suffix('.part');temporary.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 os.replace(temporary,destination)
print(json.dumps({k:report[k] for k in ['status','nativeStatus','wallSeconds']},sort_keys=True))
if report['status']=='failed':
 print(report.get('error','Unspecified failure'))
 raise SystemExit(1)
