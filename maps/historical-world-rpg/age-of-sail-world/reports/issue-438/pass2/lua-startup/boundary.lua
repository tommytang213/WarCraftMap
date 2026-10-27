-- Explicit recording boundary. It implements only this selector's observed
-- API calls; absent native definitions fail as ordinary Lua errors.
TRACE_TEXT = ""
local phase = "root"
local nextId = 0
local players = {}
TIMERS = {}
MESSAGES = {}
ERRORS = {}
EXPIRED = nil
PAUSED = false
__wurst_bootstrap_done = false
bj_MAX_PLAYERS = 24
bj_MAX_PLAYER_SLOTS = 28
MAP_PLACEMENT_TEAMS_TOGETHER = {kind="placement", id=0}
RACE_PREF_HUMAN = {kind="racepreference", id=1}
MAP_CONTROL_USER = {kind="control", id=0}

local function text(value)
    if type(value) == "table" and value.kind then return value.kind .. ":" .. value.id end
    if type(value) == "function" then return "callback" end
    return tostring(value):gsub("\n", "\\n")
end
function trace(name, ...)
    local arguments = table.pack(...)
    local row = {phase, name}
    for i = 1, arguments.n do row[#row + 1] = text(arguments[i]) end
    TRACE_TEXT = TRACE_TEXT .. table.concat(row, "\t") .. "\n"
end
function setPhase(value) phase = value; trace("milestone", value) end
local function new(kind)
    nextId = nextId + 1
    return {kind=kind,id=nextId}
end
local function typed(value, kind)
    assert(type(value) == "table" and value.kind == kind and not value.destroyed,
        "expected live " .. kind .. ", got " .. text(value))
end
function Player(index)
    assert(math.type(index) == "integer" and index >= 0 and index < 28)
    if not players[index] then players[index] = {kind="player",id=index} end
    return players[index]
end
function GetLocalPlayer() trace("GetLocalPlayer"); return Player(0) end
function ConvertPlayerColor(index) return {kind="playercolor",id=index} end
function SetMapName(name) assert(type(name) == "string"); trace("SetMapName",name) end
function SetMapDescription(name) assert(type(name) == "string"); trace("SetMapDescription",name) end
function SetPlayers(count) assert(count == 1); trace("SetPlayers",count) end
function SetTeams(count) assert(count == 1); trace("SetTeams",count) end
function SetGamePlacement(value) typed(value,"placement"); trace("SetGamePlacement",value) end
function DefineStartLocation(index,x,y) assert(index == 0 and type(x) == "number" and type(y) == "number"); trace("DefineStartLocation",index,x,y) end
function SetPlayerStartLocation(p,id) typed(p,"player"); assert(id == 0); trace("SetPlayerStartLocation",p,id) end
function SetPlayerColor(p,color) typed(p,"player"); typed(color,"playercolor"); trace("SetPlayerColor",p,color) end
function SetPlayerRacePreference(p,race) typed(p,"player"); typed(race,"racepreference"); trace("SetPlayerRacePreference",p,race) end
function SetPlayerRaceSelectable(p,value) typed(p,"player"); assert(type(value) == "boolean"); trace("SetPlayerRaceSelectable",p,value) end
function SetPlayerController(p,value) typed(p,"player"); typed(value,"control"); trace("SetPlayerController",p,value) end
function SetPlayerTeam(p,value) typed(p,"player"); assert(value == 0); trace("SetPlayerTeam",p,value) end
function SetStartLocPrioCount(index,count) assert(index == 0 and count == 0); trace("SetStartLocPrioCount",index,count) end
function SetEnemyStartLocPrioCount(index,count) assert(index == 0 and count == 0); trace("SetEnemyStartLocPrioCount",index,count) end
function SetDayNightModels(terrain,units) assert(type(terrain) == "string" and type(units) == "string"); trace("SetDayNightModels",terrain,units) end
function InitBlizzard() trace("InitBlizzard"); end -- Opaque boundary: NOT Blizzard implementation.
function Location(x,y) assert(type(x) == "number" and type(y) == "number"); trace("Location",x,y); return new("location") end
function CreateForce() local v = new("force"); trace("CreateForce",v); return v end
function CreateGroup() local v = new("group"); trace("CreateGroup",v); return v end
function CreateTimer()
    if MODE == "timer_unavailable" then trace("CreateTimer",nil); return nil end
    local v = new("timer"); trace("CreateTimer",v); return v
end
function TimerStart(timer,delay,periodic,callback)
    typed(timer,"timer"); assert(type(delay) == "number" and delay >= 0)
    assert(type(periodic) == "boolean" and (callback == nil or type(callback) == "function"))
    timer.delay, timer.periodic, timer.callback = delay, periodic, callback
    TIMERS[#TIMERS + 1] = timer
    trace("TimerStart",timer,delay,periodic,callback)
end
function GetExpiredTimer() trace("GetExpiredTimer",EXPIRED); return EXPIRED end
function DestroyTimer(timer) typed(timer,"timer"); trace("DestroyTimer",timer); timer.destroyed=true end
function CreateTrigger() local v = new("trigger"); trace("CreateTrigger",v); return v end
function TriggerRegisterPlayerChatEvent(trigger,p,prefix,exact)
    typed(trigger,"trigger"); typed(p,"player"); assert(type(prefix) == "string" and type(exact) == "boolean")
    trace("TriggerRegisterPlayerChatEvent",trigger,p,prefix,exact)
end
function TriggerAddAction(trigger,callback) typed(trigger,"trigger"); assert(type(callback) == "function"); trace("TriggerAddAction",trigger,callback) end
function InitGameCache(name)
    assert(type(name) == "string")
    if MODE == "cache_unavailable" then trace("InitGameCache",name,nil); return nil end
    local v = new("gamecache"); trace("InitGameCache",name,v); return v
end
function DisplayTimedTextToPlayer(p,x,y,duration,message)
    typed(p,"player"); assert(type(x) == "number" and type(y) == "number" and type(duration) == "number" and type(message) == "string")
    MESSAGES[#MESSAGES+1] = message; trace("DisplayTimedTextToPlayer",p,x,y,duration,message)
end
function PauseGame(value) assert(type(value) == "boolean"); PAUSED=value; trace("PauseGame",value) end
function StringLength(value) assert(type(value) == "string"); return #value end
function StringCase(value,upper) assert(type(value) == "string"); return upper and string.upper(value) or string.lower(value) end
function SubString(value,start,ending) assert(type(value) == "string"); return string.sub(value,start+1,ending) end
function S2I(value) return math.tointeger(tonumber(value)) or 0 end
function R2I(value) return value < 0 and math.ceil(value) or math.floor(value) end
-- Only a deterministic recording model. Does not assert Storm StringHash values.
function StringHash(value)
    assert(type(value) == "string")
    local hash=0
    for i=1,#value do hash=((hash*31)+string.byte(value,i)) & 0x7fffffff end
    return hash
end
function BJDebugMsg(message) ERRORS[#ERRORS+1] = tostring(message); trace("BJDebugMsg",message) end
local instructions = 0
debug.sethook(function() instructions=instructions+10000; assert(instructions < 10000000,"instruction limit") end,"",10000)
