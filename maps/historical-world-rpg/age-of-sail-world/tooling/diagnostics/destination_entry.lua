-- Developer-owned destination-entry control, not the campaign runtime.
-- The builder retains the baseline config() text and all non-script members.
-- No campaign cache is opened, consumed, acknowledged, or saved by this script.
-- Native execution and player movement remain unverified until observed.

local marker = "AOS-DESTINATION-ISOLATION-54911ca-v1"
local stage = "script loaded"
local heartbeat = 0
local diagnosticUnit = nil

-- The original config() calls this compiler helper. Its regional Wurst globals
-- are deliberately absent from this script-isolation control. All native
-- player/start-location/configuration calls below remain byte-for-byte original.
function __wurst_init_bootstrap()
end

-- @BASELINE_CONFIG@

local function report(message)
    DisplayTimedTextToPlayer(Player(0), 0.02, 0.18, 8.0, marker .. " | " .. message)
end

local function enterDestination()
    stage = "entry callback"
    report("destination entry callback reached")
    PauseGame(false)
    EnableUserControl(true)
    EnableUserUI(true)
    SetCameraBounds(
        -- @CAMERA_BOUNDS@
    )
    FogMaskEnable(false)
    FogEnable(false)
    PanCameraToTimed(576.0, 64.0, 0.0)
    SetCameraField(CAMERA_FIELD_TARGET_DISTANCE, 1650.0, 0.0)

    diagnosticUnit = CreateUnit(Player(0), FourCC("hfoo"), 576.0, 64.0, 0.0)
    if diagnosticUnit == nil then
        stage = "FAILED: CreateUnit returned nil"
        report(stage .. "; destination entered but no playable unit exists")
        return
    end
    SetUnitInvulnerable(diagnosticUnit, true)
    PauseUnit(diagnosticUnit, false)
    ClearSelection()
    SelectUnit(diagnosticUnit, true)
    stage = "unit created; movement not yet verified"
    report("terrain and selected Footman should be visible at Vienna (576, 64)")
end

local function destinationEntryCallback()
    DestroyTimer(GetExpiredTimer())
    local ok, problem = xpcall(enterDestination, tostring)
    if not ok then
        stage = "FAILED: destination callback"
        report(stage .. " | " .. tostring(problem))
    end
end

local function destinationHeartbeat()
    heartbeat = heartbeat + 1
    local position = ""
    if diagnosticUnit ~= nil then
        position = " | unit at " .. tostring(GetUnitX(diagnosticUnit)) .. ", " .. tostring(GetUnitY(diagnosticUnit))
    end
    report("heartbeat " .. tostring(heartbeat) .. " | " .. stage .. position)
end

function main()
    SetDayNightModels("Environment\\DNC\\DNCLordaeron\\DNCLordaeronTerrain\\DNCLordaeronTerrain.mdl", "Environment\\DNC\\DNCLordaeron\\DNCLordaeronUnit\\DNCLordaeronUnit.mdl")
    InitBlizzard()
    stage = "main entered; Blizzard initialized"
    report(stage)
    local entryTimer = CreateTimer()
    local heartbeatTimer = CreateTimer()
    if entryTimer == nil or heartbeatTimer == nil then
        stage = "FAILED: CreateTimer returned nil"
        report(stage)
        if entryTimer ~= nil then DestroyTimer(entryTimer) end
        if heartbeatTimer ~= nil then DestroyTimer(heartbeatTimer) end
        return
    end
    TimerStart(entryTimer, 0.0, false, destinationEntryCallback)
    TimerStart(heartbeatTimer, 2.0, true, destinationHeartbeat)
end
