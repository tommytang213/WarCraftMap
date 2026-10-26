-- Exercise the unmodified compiled storage methods, not campaign/main startup.
-- Only the five game-cache natives below are modeled. No Warcraft client runs.
local originals = {
    bootstrap = __wurst_init_bootstrap,
    construct = WarcraftCampaignSaveStorage_new_WarcraftCampaignSaveStorage,
    write = WarcraftCampaignSaveStorage_WarcraftCampaignSaveStorage_writeTransactional,
    diagnostic = WarcraftCampaignSaveStorage_WarcraftCampaignSaveStorage_diagnostic,
    main = main,
}
for name, fn in pairs(originals) do
    assert(type(fn) == 'function', 'Missing compiled function: ' .. name)
end
local cache = {}
local calls = {StoreString = 0, SaveGameCache = 0, HaveStoredString = 0,
               GetStoredString = 0, FlushStoredString = 0}
function StoreString(actual, mission, key, value)
    assert(actual == cache and mission == 'campaign' and key == 'session_start')
    assert(value == 'candidate')
    calls.StoreString = calls.StoreString + 1
    return false -- A rejected write does not enter the in-memory cache.
end
function SaveGameCache(actual)
    assert(actual == cache)
    calls.SaveGameCache = calls.SaveGameCache + 1
    return true -- Saving the unchanged cache does not prove the write succeeded.
end
function HaveStoredString(actual, mission, key)
    assert(actual == cache)
    calls.HaveStoredString = calls.HaveStoredString + 1
    return actual[mission] ~= nil and actual[mission][key] ~= nil
end
function GetStoredString(actual, mission, key)
    assert(actual == cache)
    calls.GetStoredString = calls.GetStoredString + 1
    return actual[mission] and actual[mission][key] or ''
end
function FlushStoredString(actual, mission, key)
    assert(actual == cache)
    calls.FlushStoredString = calls.FlushStoredString + 1
    if actual[mission] then actual[mission][key] = nil end
end

local instructions = 0
debug.sethook(function()
    instructions = instructions + 1000
    if instructions > 100000 then error('Cache probe instruction budget exceeded') end
end, '', 1000)
__wurst_init_bootstrap()
local storage = originals.construct(cache, 'campaign', 'cache-write-fault-probe')
local returned = originals.write(storage, 'session_start', 'candidate', 'cache-write-fault-probe')
local diagnostic = originals.diagnostic(storage, 'cache-write-fault-probe')
debug.sethook()
assert(__wurst_init_bootstrap == originals.bootstrap)
assert(WarcraftCampaignSaveStorage_new_WarcraftCampaignSaveStorage == originals.construct)
assert(WarcraftCampaignSaveStorage_WarcraftCampaignSaveStorage_writeTransactional == originals.write)
assert(WarcraftCampaignSaveStorage_WarcraftCampaignSaveStorage_diagnostic == originals.diagnostic)
assert(main == originals.main)
assert(type(returned) == 'boolean' and type(diagnostic) == 'string')
local function quote(value)
    return '"' .. value:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n')
                        :gsub('\r', '\\r'):gsub('\t', '\\t') .. '"'
end
local rows = {}
for name, count in pairs(calls) do rows[#rows + 1] = quote(name) .. ':' .. count end
__cache_probe_result = '{"returned":' .. tostring(returned) ..
    ',"stored":' .. tostring(cache.campaign ~= nil and cache.campaign.session_start ~= nil) ..
    ',"diagnostic":' .. quote(diagnostic) .. ',"nativeCalls":{' .. table.concat(rows, ',') ..
    '},"sampledInstructions":' .. instructions .. ',"productionFunctionsUnchanged":true' ..
    ',"mainCalled":false,"configCalled":false,"nativeStatus":"not_run"}'
