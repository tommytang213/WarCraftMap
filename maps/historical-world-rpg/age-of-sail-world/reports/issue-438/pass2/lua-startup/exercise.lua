assert(TRACE_TEXT == "", "native called during root chunk")
setPhase("config")
config()
setPhase("main")
main()
setPhase("zero_timer")
for _,timer in ipairs(TIMERS) do
    if timer.delay == 0 and timer.callback and not timer.destroyed then
        EXPIRED=timer
        timer.callback()
        EXPIRED=nil
    end
end
assert(#ERRORS == 0, "recorded Lua errors: " .. table.concat(ERRORS,"; "))
if MODE == "isolation" then
    assert(#MESSAGES == 2, "expected exactly two isolation markers")
    assert(MESSAGES[1] == "438: main tail reached", "main-tail marker missing")
    assert(MESSAGES[2] == "438: timer reached", "timer marker missing")
    assert(Bootstrap_bootstrapOriginSelection == nil, "Bootstrap must not execute")
    assert(ScenarioSettings_CAMPAIGN_CACHE_FILE == "", "ScenarioSettings must not execute")
    assert(not PAUSED, "isolation must not pause the game")
    setPhase("complete")
    return
end
if MODE == "deliberate_nil_argument" then
    DisplayTimedTextToPlayer(nil,0,0,30,"negative control")
end
assert(#MESSAGES == 2,"expected bootstrap and origin messages, got " .. #MESSAGES)
assert(MESSAGES[2]:find("Use /origin page N",1,true),"origin UI text missing")
assert(PAUSED,"origin selector must pause the simulation")
assert(OriginCatalog_count_storage[Bootstrap_bootstrapOriginSelection] == 230,"unexpected origin count")
setPhase("complete")
