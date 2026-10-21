-- Supplemental observer for the unchanged, actually archived destination Lua.
-- This wraps selected compiled functions only to measure them, delegates every
-- call, and supplies explicitly named timer-context natives. It is not Warcraft.
__audit = {phases={}, indexOf={}, cacheWrites={}, callbacks={}, callbackErrors={},
           nativeStatus='not_run', simulatedTime=0, instructions=0}
__audit_payloads = {}
local A = __audit
local events = {}
local activeEvent = nil
local call = __probe.call
local function counts()
 local out={}
 for k,v in pairs(__probe.nativeCalls) do out[k]=v end
 return out
end
local function delta(before)
 local out={}
 for k,v in pairs(__probe.nativeCalls) do if v~=(before[k] or 0) then out[k]=v-(before[k] or 0) end end
 return out
end
local function measure(name, fn, ...)
 local row={name=name,startInstructions=A.instructions,nativeBefore=counts(),startCpu=os.clock()}
 table.insert(A.phases,row)
 local out=table.pack(pcall(fn,...))
 row.instructions=A.instructions-row.startInstructions
 row.cpuSeconds=os.clock()-row.startCpu
 row.nativeCalls=delta(row.nativeBefore);row.nativeBefore=nil;row.startCpu=nil
 row.completed=out[1]
 if not out[1] then row.error=tostring(out[2]);error(out[2],0) end
 if type(out[2])=='string' then row.returnedStringBytes=#out[2] end
 if type(out[2])=='boolean' or type(out[2])=='number' then row.returnValue=out[2] end
 return table.unpack(out,2,out.n)
end
local observed={
 'initializeRegionalCampaign','registerCampaignDomains',
 'PlayableCampaignServices_PlayableCampaignServices_startup',
 'PlayableCampaignServices_PlayableCampaignServices_startNewCampaign',
 'PlayableCampaignServices_PlayableCampaignServices_restoreOrdinaryStartup',
 'PlayableCampaignServices_PlayableCampaignServices_finishStartup',
 'PlayableCampaignState_PlayableCampaignState_captureAuthoritativeState',
 'PlayableCampaignState_PlayableCampaignState_captureDomains',
 'PlayableCampaignState_PlayableCampaignState_validateAuthoritativeState',
 'PlayableCampaignState_PlayableCampaignState_projectParty',
 'MilitarySettlementRuntime_MilitarySettlementRuntime_parseSnapshot',
 'PlayableTradeRuntime_PlayableTradeRuntime_validateSnapshot',
 'PlayableCampaignCodec_PlayableCampaignCodec_encode','runtimeChecksum',
 'PlayableCountryInteractionRuntime_PlayableCountryInteractionRuntime_captureState',
 'WarcraftRpgRuntime_WarcraftRpgRuntime_captureState',
 'CampaignClock_CampaignClock_advanceElapsed',
 'MilitaryCombatEvents_MilitaryCombatEvents_onTimer',
 'PlayerGodModeController_PlayerGodModeController_reconcile',
 'CampaignUnstuckRecovery_CampaignUnstuckRecovery_refresh',
}
A.observerWrappedFunctions=observed
for _,name in ipairs(observed) do
 local original=assert(_G[name],name)
 _G[name]=function(...) return measure(name,original,...) end
end
local indexOf=assert(string_indexOf)
function string_indexOf(value,needle,site)
 local key=tostring(site)..' | needle='..needle
 local row=A.indexOf[key]
 if not row then row={calls=0,totalInputBytes=0,maxInputBytes=0,substringCalls=0};A.indexOf[key]=row end
 row.calls=row.calls+1;row.totalInputBytes=row.totalInputBytes+#value;row.maxInputBytes=math.max(row.maxInputBytes,#value)
 local before=__probe.nativeCalls.SubString or 0
 local result=indexOf(value,needle,site)
 row.substringCalls=row.substringCalls+(__probe.nativeCalls.SubString or 0)-before
 return result
end
-- Counts describe argument traffic, not bytes copied by Warcraft's native.
A.nativeArgumentVolumes={SubString={inputBytes=0,requestedSpanBytes=0},StringLength={inputBytes=0},StringHash={inputBytes=0}}
local substringNative,lengthNative,hashNative=SubString,StringLength,StringHash
function SubString(value,first,last)
 local row=A.nativeArgumentVolumes.SubString
 row.inputBytes=row.inputBytes+#value;row.requestedSpanBytes=row.requestedSpanBytes+math.max(0,last-first)
 return substringNative(value,first,last)
end
function StringLength(value)
 A.nativeArgumentVolumes.StringLength.inputBytes=A.nativeArgumentVolumes.StringLength.inputBytes+#value
 return lengthNative(value)
end
function StringHash(value)
 A.nativeArgumentVolumes.StringHash.inputBytes=A.nativeArgumentVolumes.StringHash.inputBytes+#value
 return hashNative(value)
end
A.nativeModelExtension={collisionSize=32,hidden=false,flying=false}
function BlzGetUnitCollisionSize(value)
 call('BlzGetUnitCollisionSize');assert(type(value)=='table' and value.__probe_handle_type=='unit');return 32.
end
function IsUnitHidden(value)
 call('IsUnitHidden');assert(type(value)=='table' and value.__probe_handle_type=='unit');return false
end
UNIT_TYPE_FLYING='probe_flying'
local unitType=IsUnitType
function IsUnitType(value,kind)
 if kind==UNIT_TYPE_FLYING then call('IsUnitType');assert(type(value)=='table' and value.__probe_handle_type=='unit');return false end
 return unitType(value,kind)
end
local store=StoreString
function StoreString(cache,mission,key,value)
 table.insert(A.cacheWrites,{mission=mission,key=key,bytes=#value,instructions=A.instructions})
 table.insert(__audit_payloads,value)
 return store(cache,mission,key,value)
end
local bjdebug=BJDebugMsg
function BJDebugMsg(value)
 if tostring(value):find('lua callback error:',1,true) then table.insert(A.callbackErrors,tostring(value)) end
 return bjdebug(value)
end
-- Synthetic time advances only after main returns. No engine scheduling,
-- asynchronous unit event, disk cache, rendering or asset behavior is modeled.
local createTimer,startTimer,registerTriggerTimer=CreateTimer,TimerStart,TriggerRegisterTimerEvent
function CreateTimer()
 local timer=createTimer();timer.__audit_kind='timer';table.insert(events,timer);return timer
end
function TimerStart(timer,seconds,repeated,callback)
 assert(type(timer)=='table' and timer.__probe_handle_type=='timer')
 assert(seconds>=0 and type(repeated)=='boolean')
 timer.__audit_started=A.simulatedTime;timer.__audit_due=A.simulatedTime+seconds
 timer.__audit_generation=(timer.__audit_generation or 0)+1;timer.__audit_paused=false
 return startTimer(timer,seconds,repeated,callback)
end
function PauseTimer(timer)
 call('PauseTimer');assert(type(timer)=='table' and timer.__probe_handle_type=='timer')
 timer.__audit_elapsed=math.max(0,A.simulatedTime-(timer.__audit_started or 0))
 timer.__audit_paused=true
end
function TimerGetElapsed(timer)
 call('TimerGetElapsed');assert(type(timer)=='table' and timer.__probe_handle_type=='timer')
 if timer.__audit_paused then return timer.__audit_elapsed end
 return math.min(timer.seconds,math.max(0,A.simulatedTime-timer.__audit_started))
end
function GetExpiredTimer()
 call('GetExpiredTimer');assert(activeEvent and activeEvent.__audit_kind=='timer','No modeled timer callback context')
 return activeEvent
end
EVENT_GAME_TIMER_EXPIRED='probe_EVENT_GAME_TIMER_EXPIRED'
function TriggerRegisterTimerEvent(trigger,seconds,repeated)
 local result=registerTriggerTimer(trigger,seconds,repeated)
 assert(seconds>0 and type(repeated)=='boolean')
 local event={__audit_kind='trigger_timer',trigger=trigger,seconds=seconds,repeated=repeated,
              __audit_started=A.simulatedTime,__audit_due=A.simulatedTime+seconds,__audit_generation=1}
 table.insert(events,event);return result
end
function GetTriggeringTrigger()
 call('GetTriggeringTrigger');assert(activeEvent and activeEvent.__audit_kind=='trigger_timer','No modeled trigger callback context')
 return activeEvent.trigger
end
function GetTriggerEventId()
 call('GetTriggerEventId');assert(activeEvent and activeEvent.__audit_kind=='trigger_timer','No modeled trigger callback context')
 return EVENT_GAME_TIMER_EXPIRED
end
local function hook(budget)
 local began=A.instructions
 debug.sethook(function()
  A.instructions=A.instructions+10000
  if A.instructions-began>budget then
   A.budgetExhausted=true;A.budgetTrace=debug.traceback()
   debug.sethook();error('__AUDIT_INSTRUCTION_BUDGET_EXHAUSTED',0)
  end
 end,'',10000)
end
function __audit_startup()
 hook(2000000000)
 local ok,err=xpcall(function() measure('config',config);measure('main',main) end,debug.traceback)
 debug.sethook()
 A.startupCompleted=ok and not A.budgetExhausted
 if not ok then A.startupError=tostring(err) end
 __probe.collectLateState()
 A.startup={instructions=A.instructions,nativeCalls=counts(),started=__probe.campaignStarted,
  registered=__probe.campaignRegistered,units=__probe.syntheticUnitCount,counts=__probe.runtimeCounts,
  finalCacheRequest=__probe.finalCacheRequest,timerRegistrations=__probe.timerRegistrations}
 local clock=CampaignTimeline_warcraftTimerClock
 A.startup.clock={day=CampaignClock_currentDay_storage[clock],daysPerSecond=CampaignClock_daysPerSecond_storage[clock],
  speed=CampaignClock_speed_storage[clock],fractionalDays=CampaignClock_fractionalDays_storage[clock]}
 assert(ok and not A.budgetExhausted and A.startup.started and A.startup.registered,'Startup did not complete under explicit stubs')
end
function __audit_callbacks()
 local begin=A.instructions
 hook(200000000)
 local ok,err=xpcall(function()
  while true do
   local chosen=nil
   for _,event in ipairs(events) do
    local callback=event.__audit_kind=='timer' and event.callback or event.trigger and event.trigger.action
    if callback and event.__audit_due and not event.destroyed and not event.__audit_paused
      and not (event.trigger and event.trigger.destroyed) and event.__audit_due<=1.001
      and (not chosen or event.__audit_due<chosen.__audit_due) then chosen=event end
   end
   if not chosen then break end
   assert(#A.callbacks<100,'Synthetic scheduler callback bound exceeded')
   A.simulatedTime=chosen.__audit_due;activeEvent=chosen
   local callback=chosen.__audit_kind=='timer' and chosen.callback or chosen.trigger.action
   local info=debug.getinfo(callback,'S')
   local nativeBefore=counts();local instructionBefore=A.instructions;local cpuBefore=os.clock()
   local errorBefore=#A.callbackErrors;local version=chosen.__audit_generation
   local result={kind=chosen.__audit_kind,atSeconds=A.simulatedTime,callbackDefinedLine=info.linedefined}
   table.insert(A.callbacks,result)
   callback()
   result.instructions=A.instructions-instructionBefore;result.cpuSeconds=os.clock()-cpuBefore
   result.nativeCalls=delta(nativeBefore);result.completed=#A.callbackErrors==errorBefore and not A.budgetExhausted
   assert(result.completed,'Actual callback reported an error under this explicit model')
   if version==chosen.__audit_generation then
    if chosen.repeated then chosen.__audit_started=A.simulatedTime;chosen.__audit_due=A.simulatedTime+chosen.seconds
    else chosen.__audit_due=nil end
   end
   activeEvent=nil
  end
 end,debug.traceback)
 debug.sethook()
 A.callbackPhase={completed=ok and not A.budgetExhausted,instructions=A.instructions-begin,
   throughSeconds=1.001,callbackCount=#A.callbacks,budget=200000000}
 if not ok then A.callbackPhase.error=tostring(err) end
 assert(ok and not A.budgetExhausted,'Callback phase failed under explicit model')
end
