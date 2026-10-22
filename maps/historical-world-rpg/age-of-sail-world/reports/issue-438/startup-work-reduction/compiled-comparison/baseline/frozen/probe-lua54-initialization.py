#!/usr/bin/env python3
"""Supplemental stock-Lua startup probe; explicit stubs, never Warcraft execution."""
from pathlib import Path
import ctypes
import ctypes.util
import argparse
import json
import hashlib
import re
import os
import sys
import time

ROOT = Path(__file__).resolve().parent
LIBRARY = os.environ.get('WC3_LUA_PROBE_LIBRARY') or ctypes.util.find_library('lua5.4')
lib = ctypes.CDLL(LIBRARY)
lib.luaL_newstate.restype = ctypes.c_void_p
lib.luaL_openlibs.argtypes = [ctypes.c_void_p]
lib.luaL_loadfilex.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
lib.luaL_loadfilex.restype = ctypes.c_int
lib.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.luaL_loadstring.restype = ctypes.c_int
lib.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_longlong, ctypes.c_void_p]
lib.lua_pcallk.restype = ctypes.c_int
lib.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
lib.lua_tolstring.restype = ctypes.c_char_p
lib.lua_getglobal.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.lua_getglobal.restype = ctypes.c_int
lib.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.lua_close.argtypes = [ctypes.c_void_p]

PRELUDE = r'''
__probe = {nativeCalls={}, phases={}, messages={}, instructions=0, expectedStop=false}
local function call(name) __probe.nativeCalls[name] = (__probe.nativeCalls[name] or 0) + 1 end
local function handle(kind) return {__probe_handle_type=kind} end
local players = {}
function Player(id) call('Player'); if not players[id] then players[id]=handle('player') end; return players[id] end
function GetLocalPlayer() call('GetLocalPlayer'); return Player(0) end
function GetPlayerId(p) for id,value in pairs(players) do if value==p then return id end end; error('Unknown player handle') end
function CreateForce() call('CreateForce'); return handle('force') end
function CreateGroup() call('CreateGroup'); return handle('group') end
function CreateTimer() call('CreateTimer'); return handle('timer') end
function CreateTrigger() call('CreateTrigger'); return handle('trigger') end
function TriggerRegisterPlayerChatEvent(trigger,player,text,exact) call('TriggerRegisterPlayerChatEvent'); return handle('event') end
function TriggerAddAction(trigger,action) call('TriggerAddAction');trigger.action=action;return handle('triggeraction') end
function Location(x,y) call('Location'); return {__probe_handle_type='location',x=x,y=y} end
function TimerStart(timer,seconds,repeated,callback) call('TimerStart'); timer.seconds=seconds;timer.repeated=repeated;timer.callback=callback end
function StringLength(s) call('StringLength'); return #s end
function SubString(s,first,last) call('SubString'); return string.sub(s,first+1,last) end
function StringCase(s,upper) call('StringCase'); if upper then return string.upper(s) else return string.lower(s) end end
local hashIds, nextHash = {}, 0
function StringHash(s) call('StringHash'); if hashIds[s]==nil then nextHash=nextHash+1;hashIds[s]=nextHash end; return hashIds[s] end
function I2S(v) call('I2S'); return tostring(v) end
function S2I(v) call('S2I'); return math.tointeger(tonumber(v)) or 0 end
function S2R(v) call('S2R'); return tonumber(v) or 0 end
function I2R(v) call('I2R'); return v+0.0 end
function R2I(v) call('R2I'); return v>=0 and math.floor(v) or math.ceil(v) end
function R2S(v) call('R2S'); return string.format('%.3f',v) end
function GetLocalizedString(s) call('GetLocalizedString'); return s end
function ConvertPlayerColor(v) call('ConvertPlayerColor'); return v end
function BJDebugMsg(s) call('BJDebugMsg'); table.insert(__probe.messages,tostring(s)) end
function DisplayTimedTextToPlayer(p,x,y,t,s) call('DisplayTimedTextToPlayer'); table.insert(__probe.messages,tostring(s)) end
function InitBlizzard() call('InitBlizzard') end
function SetDayNightModels(a,b) call('SetDayNightModels') end
for _,name in ipairs({'SetMapName','SetMapDescription','SetPlayers','SetTeams','SetGamePlacement','DefineStartLocation','SetPlayerStartLocation','SetPlayerColor','SetPlayerRacePreference','SetPlayerRaceSelectable','SetPlayerController','SetPlayerTeam','SetStartLocPrioCount','SetEnemyStartLocPrioCount'}) do
  _G[name]=function(...) call(name) end
end
MAP_PLACEMENT_TEAMS_TOGETHER='probe_teams_together'
RACE_PREF_HUMAN='probe_human'
MAP_CONTROL_USER='probe_user'
bj_MAX_PLAYER_SLOTS=24
bj_MAX_PLAYERS=24
local caches={}
function InitGameCache(name)
  call('InitGameCache')
  if not caches[name] then caches[name]={bootstrap={request='v1|1|pending|austria|europe_central_east|europe_central_alpine|vienna'}} end
  return caches[name]
end
function GetStoredString(cache,mission,key) call('GetStoredString'); return cache[mission] and cache[mission][key] or '' end
function HaveStoredString(cache,mission,key) call('HaveStoredString'); return cache[mission]~=nil and cache[mission][key]~=nil end
function StoreString(cache,mission,key,value) call('StoreString'); cache[mission]=cache[mission] or {};cache[mission][key]=value;return true end
function SaveGameCache(cache) call('SaveGameCache'); return true end
function FlushStoredString(cache,mission,key) call('FlushStoredString'); if cache[mission] then cache[mission][key]=nil end end
local function quote(s) return '"'..tostring(s):gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r'):gsub('\t','\\t')..'"' end
local function json(v)
 if type(v)=='string' then return quote(v) end
 if type(v)=='number' or type(v)=='boolean' then return tostring(v) end
 if v==nil then return 'null' end
 local rows={}
 if #v>0 then for _,x in ipairs(v) do table.insert(rows,json(x)) end;return '['..table.concat(rows,',')..']' end
 for k,x in pairs(v) do table.insert(rows,quote(k)..':'..json(x)) end
 return '{'..table.concat(rows,',')..'}'
end
__probe.json=json
__probe.call=call
__probe.handle=handle
__probe.caches=caches
function __probe.wrap(name)
 local original=_G[name]
 if type(original)~='function' then error('Cannot wrap '..name) end
 _G[name]=function(...)
   local row={name=name,startInstruction=__probe.instructions};table.insert(__probe.phases,row)
   row.stringArgumentLengths={}
   local arguments={...}
   for index,value in ipairs(arguments) do if type(value)=='string' then row.stringArgumentLengths[tostring(index)]=#value end end
   if name=='PlayableTradeRuntime_PlayableTradeRuntime_validateSnapshot' and not __probe.tradeSnapshotPath then
    local path=__probe_snapshot_path
    local output=assert(io.open(path,'wb'));output:write(arguments[2]);output:close()
    __probe.tradeSnapshotPath=path
   end
   local began=os.clock();local results=table.pack(pcall(original,...))
   row.cpuSeconds=os.clock()-began;row.instructions=__probe.instructions-row.startInstruction
   row.completed=results[1]
   if not results[1] then row.error=tostring(results[2]);error(results[2],0) end
   if type(results[2])=='boolean' or type(results[2])=='number' then row.returnValue=results[2] end
   return table.unpack(results,2,results.n)
 end
end
'''


def execute(state, text):
    status = lib.luaL_loadstring(state, text.encode())
    if not status:
        status = lib.lua_pcallk(state, 0, 0, 0, 0, None)
    if status:
        error = lib.lua_tolstring(state, -1, None).decode(errors='replace')
        lib.lua_settop(state, 0)
        raise RuntimeError(error)


def probe(name, stop, instruction_limit, lua_path=None, override_path=None, report_label=None):
    path = Path(lua_path) if lua_path else ROOT / name / 'war3map.lua'
    text = path.read_text()
    state = lib.luaL_newstate()
    lib.luaL_openlibs(state)
    lib.lua_getglobal(state,b'_VERSION')
    runtime_version=lib.lua_tolstring(state,-1,None).decode()
    runtime_tag=runtime_version.lower().replace(' ','').replace('.','')
    lib.lua_settop(state,0)
    started = time.monotonic()
    try:
        status = lib.luaL_loadfilex(state, str(path).encode(), b't')
        if not status:
            status = lib.lua_pcallk(state, 0, 0, 0, 0, None)
        if status:
            raise RuntimeError(lib.lua_tolstring(state, -1, None).decode(errors='replace'))
        execute(state, PRELUDE)
        if stop=='startup-complete':
            execute(state, (ROOT/'late-startup-stubs.lua').read_text())
        if override_path:
            execute(state, Path(override_path).read_text())
        selected = re.findall(r'^function (init_\w+)\(', text, re.M)
        selected += [value for value in ['config','__wurst_init_bootstrap','bridge_initCompiletimeState_0','registerCampaignDomains','initializeRegionalCampaign','initializePlayableCampaignRuntime'] if re.search(r'^function '+value+r'\(',text,re.M)]
        selected += re.findall(r'^function (configureGenerated\w+)\(',text,re.M)
        selected += re.findall(r'^function ((?:PlayableCampaignServices|WarcraftRpgRuntime)_\w+_(?:startup|startNewCampaign|restoreOrdinaryStartup|finishStartup|captureState|restoreState|prepareNewCampaign))\(',text,re.M)
        selected += re.findall(r'^function ((?:PlayableCampaignState|PlayableTradeRuntime|MilitarySettlementRuntime|CampaignSaveCodec)_\w+_(?:captureAuthoritativeState|validateAuthoritativeState|validateSnapshot|parseSnapshot|validate|encode|decodeMigrateAndValidate))\(',text,re.M)
        setup='\n'.join('__probe.wrap('+json.dumps(value)+')' for value in selected)
        setup += r'''
error1=function(message,where) error('Wurst error: '..tostring(message)..' ['..tostring(where)..']',0) end
if __probe_stop=='campaign-startup' and PlayableCampaignServices_PlayableCampaignServices_startup then
 PlayableCampaignServices_PlayableCampaignServices_startup=function(...) __probe.expectedStop=true;error('__PROBE_STOP_BEFORE_CAMPAIGN_STARTUP',0) end
end
if __probe_stop=='engine-frontier' then
 for _,native in ipairs({'GetWorldBounds','IsTerrainPathable','CreateUnit','BlzCreateUnitWithSkin','BlzCreateFrame','BlzCreateFrameByType','GetUnitTypeId'}) do
  _G[native]=function(...)
   __probe.expectedStop=true;__probe.nativeFrontier=native
   __probe.nativeFrontierArgs={}
   for i,value in ipairs({...}) do
    if type(value)=='table' and value.__probe_handle_type then
     __probe.nativeFrontierArgs[i]='stub_'..value.__probe_handle_type
    else __probe.nativeFrontierArgs[i]=value end
   end
   __probe.nativeFrontierTrace=debug.traceback()
   error('__PROBE_NATIVE_FRONTIER:'..native,0)
  end
 end
end
__probe.hotspots={samples=0,leaf={},compiled={}}
local function addSample(bucket,key) bucket[key]=(bucket[key] or 0)+1 end
local function sampleFrame(info) return (info.name or '<anonymous>')..':'..tostring(info.currentline)..'@'..info.short_src end
debug.sethook(function()
 __probe.instructions=__probe.instructions+10000
 if __probe.instructions%100000==0 then
  __probe.hotspots.samples=__probe.hotspots.samples+1
  local leaf=debug.getinfo(2,'nSl')
  if leaf then addSample(__probe.hotspots.leaf,sampleFrame(leaf)) end
  for depth=2,10 do
   local frame=debug.getinfo(depth,'nSl')
   if not frame then break end
   if frame.source==__probe_compiled_source then addSample(__probe.hotspots.compiled,sampleFrame(frame));break end
  end
 end
 if __probe.instructions>__probe_instruction_limit then
  __probe.budgetTrace=debug.traceback()
  __probe.budgetFrames={}
  for depth=2,12 do
   local info=debug.getinfo(depth,'nSl')
   if not info then break end
   local frame={name=sampleFrame(info),locals={}}
   for index=1,200 do
    local name,value=debug.getlocal(depth,index)
    if not name then break end
    if type(value)=='number' or type(value)=='boolean' then frame.locals[name]=value
    elseif type(value)=='string' then frame.locals[name]={length=#value,prefix=string.sub(value,1,64)} end
   end
   table.insert(__probe.budgetFrames,frame)
  end
  debug.sethook();error('__PROBE_INSTRUCTION_BUDGET_EXHAUSTED',0)
 end
end,'',10000)
local ok,err=xpcall(function() config();main() end,debug.traceback)
debug.sethook()
__probe.completed=ok
if not ok then __probe.error=tostring(err) end
if __probe.collectLateState then __probe.collectLateState() end
__probe.result=__probe.json(__probe)
'''
        # Exclude the helper functions themselves from serialization.
        setup=setup.replace('__probe.result=__probe.json(__probe)', 'local encode=__probe.json;__probe.json=nil;__probe.wrap=nil;__probe.call=nil;__probe.handle=nil;__probe.caches=nil;__probe.collectLateState=nil;__probe.result=encode(__probe)')
        snapshot_path=ROOT/(name+'-'+(report_label or stop)+'-trade-snapshot.txt')
        execute(state, '__probe_stop='+json.dumps(stop)+'\n__probe_instruction_limit='+str(instruction_limit)+'\n__probe_compiled_source='+json.dumps('@'+str(path))+'\n__probe_snapshot_path='+json.dumps(str(snapshot_path))+'\n'+setup)
        lib.lua_getglobal(state,b'__probe')
        execute(state, '__probe_result=__probe.result')
        lib.lua_getglobal(state,b'__probe_result')
        result=json.loads(lib.lua_tolstring(state,-1,None).decode())
        result['status']='completed_under_stubs' if result['completed'] else 'expected_probe_stop' if result['expectedStop'] else 'probe_error_or_budget'
        result.update(map=name, wallSeconds=round(time.monotonic()-started,4), runtime=LIBRARY,
                      runtimeVersion=runtime_version,runtimeTag=runtime_tag,
                      compiledLuaPath=str(path), compiledLuaSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      harnessSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      lateNativeStubsSha256=hashlib.sha256((ROOT/'late-startup-stubs.lua').read_bytes()).hexdigest() if stop=='startup-complete' else None,
                      evidenceLevel='supplemental_'+runtime_tag+'_explicit_stub_probe',
                      instructionBudget=instruction_limit,
                      limitations=['Stock '+runtime_version+' is not the embedded Warcraft Lua runtime or a native client.',
                                   'Explicit native stubs; no engine assets, terrain, handles, callbacks or disk cache are executed.',
                                   'StringHash is a collision-free ID stub; it is not the Warcraft hash algorithm.',
                                   'InitBlizzard is a no-op; bj_MAX_PLAYER_SLOTS is set explicitly to 24.',
                                   'Instruction samples include instrumentation and Lua stub work.',
                                   'Probe mode: '+stop+'.'])
        if override_path:
            result['hypothesisOverride']={'path':str(override_path),'sha256':hashlib.sha256(Path(override_path).read_bytes()).hexdigest()}
            result['evidenceLevel']='supplemental_'+runtime_tag+'_scratch_function_override_hypothesis'
            result['limitations'].append('Hypothesis-only scratch function override; this is not actual compiler output for a source change.')
        if result.get('tradeSnapshotPath'):
            payload=Path(result['tradeSnapshotPath']).read_bytes()
            result['tradeSnapshotIdentity']={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
        if stop=='startup-complete':
            result['limitations'].extend([
                'Late native stubs use typed synthetic units/quests/regions/groups; no engine handles or visuals exist.',
                'All synthetic units start with 1,000 max/life, 500 max/mana, hero level 1, no inventory, move speed 300, foot movement; setters update the synthetic record.',
                'Terrain pathing is a base-WPM lookup only; collision, object footprints and engine coordinate nudging are not modeled.',
                'Game cache saves always succeed in memory; no cache limits, disk persistence, latency or failure is modeled.',
                'Only runtime-created synthetic units are enumerated; preplaced markers and engine-created objects are absent.',
                'Synthetic unit orders always return success and only record requested order/target; no engine order execution or unit movement occurs.',
            ])
        return result
    finally:
        lib.lua_close(state)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('names',nargs='*',default=['bootstrap_runtime_validation','europe_central_east'])
    parser.add_argument('--stop',choices=['campaign-startup','engine-frontier','startup-complete'],default='campaign-startup')
    parser.add_argument('--instruction-limit',type=int,default=100000000)
    parser.add_argument('--lua-path')
    parser.add_argument('--override-lua')
    parser.add_argument('--report-label')
    args=parser.parse_args()
    for name in args.names:
        result=probe(name,args.stop,args.instruction_limit,args.lua_path,args.override_lua,args.report_label)
        suffix=args.report_label or {'campaign-startup':'registration','engine-frontier':'native-frontier','startup-complete':'late-startup'}[args.stop]
        (ROOT/(name+'-'+result['runtimeTag']+'-'+suffix+'-probe.json')).write_text(json.dumps(result,indent=2)+'\n')
        summary={key:value for key,value in result.items() if key!='phases'}
        summary['phaseCount']=len(result['phases'])
        summary['lastPhases']=result['phases'][-5:]
        print(json.dumps(summary,indent=2))
