-- Explicit late-startup native model. Unknown natives remain undefined.
-- This file supplies no Warcraft runtime and cannot establish native success.
local call,handle=__probe.call,__probe.handle
local units,quests,timers,regions={},{},{},{}
local function typed(value,kind)
 assert(type(value)=='table' and value.__probe_handle_type==kind,'Expected synthetic '..kind)
 return value
end
local function unit(value) return typed(value,'unit') end
function CreateUnit(owner,typeId,x,y,facing)
 call('CreateUnit');typed(owner,'player')
 local value=handle('unit')
 value.owner=owner;value.typeId=typeId;value.x=x;value.y=y;value.facing=facing
 value.alive=true;value.maxLife=1000;value.life=1000;value.maxMana=500;value.mana=500
 value.level=1;value.xp=0;value.abilities={};value.inventory={};value.invulnerable=false;value.moveSpeed=300
 table.insert(units,value);return value
end
function GetUnitTypeId(value) call('GetUnitTypeId');if value==nil then return 0 end;return unit(value).alive and value.typeId or 0 end
function GetUnitX(value) call('GetUnitX');return unit(value).x end
function GetUnitY(value) call('GetUnitY');return unit(value).y end
function SetUnitX(value,x) call('SetUnitX');unit(value).x=x end
function SetUnitY(value,y) call('SetUnitY');unit(value).y=y end
function SetUnitPosition(value,x,y) call('SetUnitPosition');unit(value).x=x;value.y=y end
function GetUnitFacing(value) call('GetUnitFacing');return unit(value).facing end
function SetUnitFacing(value,facing) call('SetUnitFacing');unit(value).facing=facing end
function GetUnitMoveSpeed(value) call('GetUnitMoveSpeed');return unit(value).moveSpeed end
function SetUnitMoveSpeed(value,speed) call('SetUnitMoveSpeed');unit(value).moveSpeed=speed end
function GetUnitCurrentOrder(value) call('GetUnitCurrentOrder');return unit(value).currentOrder or 0 end
function IssueImmediateOrderById(value,order)
 call('IssueImmediateOrderById');unit(value).currentOrder=order;return true
end
function IssuePointOrderById(value,order,x,y)
 call('IssuePointOrderById');unit(value).currentOrder=order;value.orderPoint={x=x,y=y};return true
end
function IssueTargetOrderById(value,order,target)
 call('IssueTargetOrderById');unit(value);unit(target);value.currentOrder=order;value.orderTarget=target;return true
end
-- Synthetic movement defaults to foot; these enum values are local tokens.
MOVE_TYPE_FOOT='probe_move_foot';MOVE_TYPE_HORSE='probe_move_horse'
MOVE_TYPE_FLOAT='probe_move_float';MOVE_TYPE_AMPHIBIOUS='probe_move_amphibious';MOVE_TYPE_FLY='probe_move_fly'
UNIT_IF_MOVE_TYPE='probe_field_move_type'
function BlzGetUnitIntegerField(value,field)
 call('BlzGetUnitIntegerField');unit(value)
 if field==UNIT_IF_MOVE_TYPE then return 1 end
 error('Unmodeled integer unit field '..tostring(field))
end
function ConvertMoveType(value)
 call('ConvertMoveType');assert(value==1,'Unmodeled move type value');return MOVE_TYPE_FOOT
end
function GetOwningPlayer(value) call('GetOwningPlayer');return unit(value).owner end
function SetUnitOwner(value,owner,color) call('SetUnitOwner');typed(owner,'player');unit(value).owner=owner end
function RemoveUnit(value) call('RemoveUnit');unit(value).alive=false end
function BlzGetUnitMaxHP(value) call('BlzGetUnitMaxHP');return unit(value).maxLife end
function BlzSetUnitMaxHP(value,hp) call('BlzSetUnitMaxHP');unit(value).maxLife=hp end
function BlzGetUnitMaxMana(value) call('BlzGetUnitMaxMana');return unit(value).maxMana end
function BlzSetUnitMaxMana(value,mana) call('BlzSetUnitMaxMana');unit(value).maxMana=mana end
UNIT_STATE_LIFE='probe_life';UNIT_STATE_MANA='probe_mana'
function GetUnitState(value,state)
 call('GetUnitState');unit(value)
 if state==UNIT_STATE_LIFE then return value.life elseif state==UNIT_STATE_MANA then return value.mana end
 error('Unmodeled unit state '..tostring(state))
end
function SetUnitState(value,state,amount)
 call('SetUnitState');unit(value)
 if state==UNIT_STATE_LIFE then value.life=amount elseif state==UNIT_STATE_MANA then value.mana=amount else error('Unmodeled unit state '..tostring(state)) end
end
function GetHeroLevel(value) call('GetHeroLevel');return unit(value).level end
function SetHeroLevel(value,level,eyeCandy) call('SetHeroLevel');unit(value).level=level end
function GetHeroXP(value) call('GetHeroXP');return unit(value).xp end
function SetHeroXP(value,xp,eyeCandy) call('SetHeroXP');unit(value).xp=xp end
function UnitAddAbility(value,ability) call('UnitAddAbility');unit(value).abilities[ability]=1;return true end
function UnitRemoveAbility(value,ability) call('UnitRemoveAbility');local present=unit(value).abilities[ability]~=nil;value.abilities[ability]=nil;return present end
function GetUnitAbilityLevel(value,ability) call('GetUnitAbilityLevel');return unit(value).abilities[ability] or 0 end
function SetUnitAbilityLevel(value,ability,level) call('SetUnitAbilityLevel');unit(value).abilities[ability]=level;return level end
function SetUnitInvulnerable(value,flag) call('SetUnitInvulnerable');unit(value).invulnerable=flag end
function BlzIsUnitInvulnerable(value) call('BlzIsUnitInvulnerable');return unit(value).invulnerable end
function UnitItemInSlot(value,slot) call('UnitItemInSlot');return unit(value).inventory[slot] end
UNIT_TYPE_DEAD='probe_dead';UNIT_TYPE_HERO='probe_hero';UNIT_TYPE_STRUCTURE='probe_structure'
function IsUnitType(value,kind)
 call('IsUnitType');unit(value)
 if kind==UNIT_TYPE_DEAD then return not value.alive or value.life<=0 end
 if kind==UNIT_TYPE_HERO then local first=(value.typeId>>24)&255;return first>=65 and first<=90 end
 if kind==UNIT_TYPE_STRUCTURE then return false end
 error('Unmodeled unit type predicate '..tostring(kind))
end
function GetHandleId(value)
 call('GetHandleId');assert(type(value)=='table' and value.__probe_handle_type,'Expected synthetic handle')
 if value.__probe_handle_id==nil then __probe.nextHandleId=(__probe.nextHandleId or 0)+1;value.__probe_handle_id=__probe.nextHandleId end
 return value.__probe_handle_id
end
function PauseGame(flag) call('PauseGame');__probe.paused=flag end
function PanCameraToTimedForPlayer(player,x,y,duration) call('PanCameraToTimedForPlayer');typed(player,'player');__probe.camera={x=x,y=y,duration=duration} end
function CreateQuest() call('CreateQuest');local q=handle('quest');table.insert(quests,q);return q end
function DestroyQuest(q) call('DestroyQuest');typed(q,'quest').destroyed=true end
for _,entry in ipairs({{'QuestSetTitle','title'},{'QuestSetDescription','description'},{'QuestSetRequired','required'},{'QuestSetEnabled','enabled'},{'QuestSetCompleted','completed'},{'QuestSetDiscovered','discovered'}}) do
 local name,field=entry[1],entry[2]
 _G[name]=function(q,value) call(name);typed(q,'quest')[field]=value end
end
function Rect(minx,miny,maxx,maxy) call('Rect');local r=handle('rect');r.minx=minx;r.miny=miny;r.maxx=maxx;r.maxy=maxy;return r end
function GetWorldBounds() call('GetWorldBounds');return Rect(-8192,-8192,8192,8192) end
-- The observed compiled boundary-install call discards this result. The
-- synthetic return uses retained W3I camera bounds, not a native BJ setup.
function GetPlayableMapRect() call('GetPlayableMapRect');return Rect(-6912,-7424,6912,6912) end
function RemoveRect(value) call('RemoveRect');typed(value,'rect').removed=true end
function GetRectMinX(value) call('GetRectMinX');return typed(value,'rect').minx end
function GetRectMinY(value) call('GetRectMinY');return typed(value,'rect').miny end
function GetRectMaxX(value) call('GetRectMaxX');return typed(value,'rect').maxx end
function GetRectMaxY(value) call('GetRectMaxY');return typed(value,'rect').maxy end
function CreateRegion() call('CreateRegion');local r=handle('region');r.rects={};table.insert(regions,r);return r end
function RegionAddRect(region,rect) call('RegionAddRect');typed(region,'region');typed(rect,'rect');table.insert(region.rects,{rect.minx,rect.miny,rect.maxx,rect.maxy}) end
function RemoveRegion(region) call('RemoveRegion');typed(region,'region').removed=true end
function TriggerRegisterEnterRegion(trigger,region,filter) call('TriggerRegisterEnterRegion');typed(trigger,'trigger');typed(region,'region');return handle('event') end
function TriggerRegisterPlayerUnitEvent(trigger,player,event,filter) call('TriggerRegisterPlayerUnitEvent');typed(trigger,'trigger');typed(player,'player');assert(event~=nil,'Missing player unit event constant');return handle('event') end
function TriggerRegisterTimerEvent(trigger,timeout,periodic) call('TriggerRegisterTimerEvent');typed(trigger,'trigger');return handle('event') end
function DestroyTrigger(trigger) call('DestroyTrigger');typed(trigger,'trigger').destroyed=true end
function GroupClear(group) call('GroupClear');typed(group,'group').units={} end
function GroupEnumUnitsInRect(group,rect,filter)
 call('GroupEnumUnitsInRect');typed(group,'group');typed(rect,'rect');assert(filter==nil,'Unmodeled enumeration filter');group.units={}
 for _,value in ipairs(units) do if value.alive and value.x>=rect.minx and value.x<=rect.maxx and value.y>=rect.miny and value.y<=rect.maxy then table.insert(group.units,value) end end
end
function FirstOfGroup(group) call('FirstOfGroup');return (typed(group,'group').units or {})[1] end
function GroupRemoveUnit(group,value) call('GroupRemoveUnit');typed(group,'group');unit(value);for i,entry in ipairs(group.units or {}) do if entry==value then table.remove(group.units,i);return end end end
function DestroyGroup(group) call('DestroyGroup');typed(group,'group').destroyed=true;group.units={} end
function DestroyTimer(timer) call('DestroyTimer');typed(timer,'timer').destroyed=true end
local originalCreateTimer,originalTimerStart=CreateTimer,TimerStart
function CreateTimer() local timer=originalCreateTimer();table.insert(timers,timer);return timer end
function TimerStart(timer,seconds,repeated,callback) typed(timer,'timer');return originalTimerStart(timer,seconds,repeated,callback) end
for _,name in ipairs({'EVENT_PLAYER_UNIT_DEATH','EVENT_PLAYER_UNIT_DAMAGED','EVENT_PLAYER_UNIT_DAMAGING','EVENT_PLAYER_UNIT_ISSUED_ORDER','EVENT_PLAYER_UNIT_ISSUED_POINT_ORDER','EVENT_PLAYER_UNIT_ISSUED_TARGET_ORDER','EVENT_PLAYER_UNIT_SUMMON','EVENT_PLAYER_UNIT_TRAIN_FINISH','EVENT_PLAYER_UNIT_CONSTRUCT_FINISH','EVENT_PLAYER_UNIT_CHANGE_OWNER'}) do _G[name]='probe_'..name end
PATHING_TYPE_WALKABILITY='probe_walk';PATHING_TYPE_FLOATABILITY='probe_float';PATHING_TYPE_FLYABILITY='probe_fly'
local pathingFile=assert(io.open('/workspace/scratch/243ebc79fa0a/validation-536/startup-audit/europe_central_east/war3map.wpm','rb'))
local pathing=pathingFile:read('*a');pathingFile:close()
local width,height=string.unpack('<I4I4',pathing,9)
function IsTerrainPathable(x,y,kind)
 call('IsTerrainPathable')
 local mask=({[PATHING_TYPE_WALKABILITY]=2,[PATHING_TYPE_FLOATABILITY]=64,[PATHING_TYPE_FLYABILITY]=4})[kind]
 assert(mask~=nil,'Unmodeled pathing type')
 local px,py=math.floor((x+8192)/32),math.floor((y+8192)/32)
 if px<0 or py<0 or px>=width or py>=height then return true end
 return (string.byte(pathing,17+py*width+px)&mask)~=0
end
-- Missing constants must stop the probe, even where compiler guards accept nil.
-- This is an error-only lookup hook, never an unknown-native fallback.
setmetatable(_G,{__index=function(_,name)
 if type(name)=='string' and name:match('^[A-Z][A-Z0-9_]*$') then
  error('Unmodeled native constant '..name,2)
 end
 return nil
end})
function __probe.collectLateState()
 __probe.syntheticUnitCount=#units;__probe.syntheticQuestCount=#quests;__probe.syntheticRegionCount=#regions
 __probe.timerRegistrations={}
 for _,timer in ipairs(timers) do
  local info=timer.callback and debug.getinfo(timer.callback,'S')
  table.insert(__probe.timerRegistrations,{seconds=timer.seconds,repeated=timer.repeated,hasCallback=timer.callback~=nil,destroyed=timer.destroyed or false,callbackDefinedLine=info and info.linedefined or nil})
 end
 __probe.campaignStarted=PlayableCampaignServices_started_storage and PlayableCampaignServices_started_storage[PlayableCampaignRuntime_campaignServices] or false
 __probe.campaignRegistered=PlayableCampaignServices_registered_storage and PlayableCampaignServices_registered_storage[PlayableCampaignRuntime_campaignServices] or false
 __probe.finalCacheRequest=__probe.caches['AgeOfSailCampaign.w3v'] and __probe.caches['AgeOfSailCampaign.w3v'].bootstrap.request or ''
 local services=PlayableCampaignRuntime_campaignServices
 local state=services and PlayableCampaignServices_state_storage[services]
 local military=state and PlayableCampaignState_militarySettlements_storage[state]
 local trade=state and PlayableCampaignState_extension_storage[state]
 local controller=trade and PlayableTradeRuntime_controller_storage[trade]
 local provenance=controller and PlayableTradeController_provenance_storage[controller]
 __probe.runtimeCounts={
  markets=trade and PlayableTradeRuntime_marketCount_storage[trade] or 0,
  stores=trade and PlayableTradeRuntime_storeCount_storage[trade] or 0,
  provenanceLots=provenance and CargoProvenance_count_storage[provenance] or 0,
  forces=military and MilitarySettlementRuntime_forceCount_storage[military] or 0,
  settlements=military and MilitarySettlementRuntime_settlementCount_storage[military] or 0,
 }
end
