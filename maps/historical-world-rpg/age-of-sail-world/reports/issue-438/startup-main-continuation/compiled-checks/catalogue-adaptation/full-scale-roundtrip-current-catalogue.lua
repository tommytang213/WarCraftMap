-- Supplemental compiled-Lua regression. This supplies no Warcraft natives.
-- The archived production functions remain unchanged; debug hooks observe them.
local stack = 'when calling from the full-scale compiled-Lua regression'
__scale = {phases = {}, timerCallbacksExecuted = 0, nativeStatus = 'not_run'}

local watched = {}
for _, name in ipairs({
    'PlayableCampaignServices_PlayableCampaignServices_startup',
    'PlayableCampaignServices_PlayableCampaignServices_finishStartup',
    'PlayableCampaignServices_PlayableCampaignServices_rejectStartup',
    'PlayableCampaignServices_PlayableCampaignServices_rejectRestoration',
}) do
    assert(type(_G[name]) == 'function', 'Missing compiled function: ' .. name)
    watched[_G[name]] = name
end

local function phase(name, operation, observeStartup)
    local row = {name = name, instructions = 0, budget = __scale_budget,
                 stages = {}, observations = {}, completed = false}
    __scale.phases[name] = row
    __scale.activePhase = name
    local began = os.clock()
    debug.sethook(function(event)
        if event == 'count' then
            row.instructions = row.instructions + 10000
            if row.instructions > row.budget then
                row.budgetExhausted = true
                row.budgetTrace = debug.traceback()
                debug.sethook()
                error('__SCALE_INSTRUCTION_BUDGET_EXHAUSTED:' .. name, 0)
            end
        else
            local info = debug.getinfo(2, 'fl')
            local target = info and watched[info.func]
            if target then
                local observation = row.observations[target]
                if not observation then
                    observation = {entries = 0, tailEntries = 0, returns = {}}
                    row.observations[target] = observation
                end
                if event == 'call' or event == 'tail call' then
                    observation.entries = observation.entries + 1
                    if event == 'tail call' then
                        observation.tailEntries = observation.tailEntries + 1
                    end
                elseif event == 'return' then
                    table.insert(observation.returns, {
                        line = info.currentline,
                        literal = __scale_literal_returns[info.currentline] or 'unresolved',
                    })
                end
            end
        end
    end, observeStartup and 'cr' or '', 10000)
    local ok, problem = xpcall(function() operation(row) end, debug.traceback)
    debug.sethook()
    row.cpuSeconds = os.clock() - began
    row.completed = ok and not row.budgetExhausted
    if not ok then row.error = tostring(problem) end
    __scale.activePhase = nil
    assert(row.completed, row.error or ('Incomplete phase: ' .. name))
end

local function step(row, name, operation)
    local item = {name = name, startInstructions = row.instructions}
    table.insert(row.stages, item)
    local began = os.clock()
    operation()
    item.instructions = row.instructions - item.startInstructions
    item.cpuSeconds = os.clock() - began
    item.completed = true
end

local function catalogue()
    local services = assert(PlayableCampaignRuntime_campaignServices)
    local state = assert(PlayableCampaignServices_state_storage[services])
    local runtime = assert(PlayableCampaignState_extension_storage[state])
    assert(PlayableTradeRuntime_marketCount_storage[runtime] == 8426,
           'The full-scale gate requires exactly 8426 actual markets')
    assert(PlayableTradeRuntime_storeCount_storage[runtime] == 829,
           'The full-scale gate requires exactly 829 actual stores')
    return services, state, runtime
end

function __scale_run_startup()
    phase('startup', function()
        config()
        main()
    end, true)
    local observations = __scale.phases.startup.observations
    local startup = observations.PlayableCampaignServices_PlayableCampaignServices_startup
    local finish = observations.PlayableCampaignServices_PlayableCampaignServices_finishStartup
    assert(startup and startup.entries == 1, 'Missing or repeated initial startup entry')
    assert(finish and finish.entries == 1, 'Missing or repeated finishStartup entry')
    assert(#finish.returns == 1 and finish.returns[1].literal == 'true',
           'finishStartup did not observably return literal true')
    for _, result in ipairs(startup.returns) do
        assert(result.literal == 'true', 'startup returned false or an unresolved value')
    end
    assert(not observations.PlayableCampaignServices_PlayableCampaignServices_rejectStartup,
           'Startup rejection executed')
    assert(not observations.PlayableCampaignServices_PlayableCampaignServices_rejectRestoration,
           'Restoration rejection executed')
    -- In the actual compiled program startup tail-returns finishStartup. Lua
    -- removes that caller frame, so finishStartup's observed true return is
    -- the startup result; no production wrapper is installed to observe it.
    assert(#startup.returns == 1 or finish.tailEntries == 1,
           'No observed true startup return or tail-return through finishStartup')
    local services, state = catalogue()
    assert(PlayableCampaignServices_started_storage[services] == true)
    assert(PlayableCampaignServices_registered_storage[services] == true)
    assert(PlayableCampaignState_startupLocked_storage[state] == false)
    assert(PlayableCampaignServices_lastDiagnostic_storage[services] == '')
    __probe.collectLateState()
    assert(__probe.finalCacheRequest ==
        'v1|1|consumed|austria|europe_central_east|europe_central_alpine|vienna')
    assert(__probe.runtimeCounts.provenanceLots == 0, 'Unexpected initial provenance')
    assert(#__probe.timerRegistrations == 6, 'Missing activation timer registrations')
    __scale.startup = {
        started = true, registered = true, startupReturn = true, finishStartupReturn = true,
        startupReturnObservation = #startup.returns == 1 and 'literal_return' or 'tail_return_through_finishStartup',
        finalCacheRequest = __probe.finalCacheRequest,
        runtimeCounts = __probe.runtimeCounts,
        syntheticUnitCount = __probe.syntheticUnitCount,
        timerRegistrations = __probe.timerRegistrations,
        messages = __probe.messages,
    }
end

local function reverse(array, count)
    for i = 0, count // 2 - 1 do
        local other = count - 1 - i
        array[i], array[other] = array[other], array[i]
    end
end

function __scale_run_roundtrip()
    phase('roundtrip', function(row)
        local _, _, runtime = catalogue()
        local markets = PlayableTradeRuntime_markets_storage[runtime]
        local stores = PlayableTradeRuntime_stores_storage[runtime]
        local controller = PlayableTradeRuntime_controller_storage[runtime]
        local provenance = PlayableTradeController_provenance_storage[controller]
        local originalMarkets, originalStores, allowedGoods, origins = {}, {}, {}, {}
        local report = {marketCount = 8426, storeCount = 829, populatedStores = 0,
                        populatedLots = 0, totalCargoUnits = 0, selection = {}}
        __scale.roundtrip = report
        step(row, 'populate_actual_catalogue', function()
            CargoProvenance_CargoProvenance_clear(provenance, stack)
            for i = 0, 8425 do
                local market = assert(markets[i])
                originalMarkets[i] = market
                RuntimeMarket_stock_storage[market] = i + 100
                RuntimeMarket_money_storage[market] = i + 10000
                RuntimeMarket_previousUnitPrice_storage[market] = i + 10
                RuntimeMarket_eventPermille_storage[market] = -(i % 100)
            end
            for i = 0, 828 do
                local store = assert(stores[i])
                originalStores[i] = store
                local quantity = math.min(2, TradeStore_capacity_storage[store])
                assert(quantity >= 1, 'Actual store has no cargo capacity: ' .. TradeStore_id_storage[store])
                local chosen
                for offset = 0, 8425 do
                    local market = markets[(i * 10 + offset) % 8426]
                    local good = RuntimeMarket_goodName_storage[market]
                    if TradeStore_TradeStore_accepts(store, good, stack) then
                        chosen = market
                        break
                    end
                end
                assert(chosen, 'No registered permitted commodity for ' .. TradeStore_id_storage[store])
                local good = RuntimeMarket_goodName_storage[chosen]
                local origin = RuntimeMarket_id_storage[chosen]
                assert(good ~= '' and origin ~= '')
                allowedGoods[good], origins[origin] = true, true
                CargoBalances_CargoBalances_clear(TradeStore_contents_storage[store], stack)
                CargoBalances_CargoBalances_set(TradeStore_contents_storage[store], good, quantity, stack)
                TradeStore_money_storage[store] = i + 1000
                CargoProvenance_CargoProvenance_add(provenance, TradeStore_id_storage[store], good,
                                                  quantity, i + 20, origin, stack)
                assert(TradeStore_TradeStore_quantity(store, good, stack) == quantity)
                report.populatedStores = report.populatedStores + 1
                report.totalCargoUnits = report.totalCargoUnits + quantity
            end
            report.populatedLots = CargoProvenance_count_storage[provenance]
            assert(report.populatedStores == 829 and report.populatedLots == 829)
            report.distinctGoods, report.distinctOrigins = 0, 0
            for _ in pairs(allowedGoods) do report.distinctGoods = report.distinctGoods + 1 end
            for _ in pairs(origins) do report.distinctOrigins = report.distinctOrigins + 1 end
            local last = markets[8425]
            assert(PlayableTradeRuntime_PlayableTradeRuntime_selectMarket(runtime,
                RuntimeMarket_id_storage[last], RuntimeMarket_goodName_storage[last], stack))
            PlayableTradeRuntime_hold_storage[runtime] = stores[828]
            PlayableTradeRuntime_marketSelected_storage[runtime] = true
            PlayableTradeRuntime_storeSelected_storage[runtime] = true
            report.selection.savedMarketId = RuntimeMarket_id_storage[last]
            report.selection.savedGoodId = RuntimeMarket_goodName_storage[last]
            report.selection.savedStoreId = TradeStore_id_storage[stores[828]]
        end)
        step(row, 'capture_and_validate_populated_state', function()
            __scale_saved = PlayableTradeRuntime_PlayableTradeRuntime_capture(runtime, stack)
            assert(#__scale_saved > 539822, 'Populated capture is unexpectedly shortened')
            assert(PlayableTradeRuntime_PlayableTradeRuntime_validate(runtime, __scale_saved, stack),
                   'Full populated capture is invalid before mutation')
            report.savedBytes = #__scale_saved
        end)
        step(row, 'mutate_and_reverse_both_catalogues', function()
            for i = 0, 8425 do
                RuntimeMarket_stock_storage[markets[i]] = 0
                RuntimeMarket_money_storage[markets[i]] = 0
                RuntimeMarket_previousUnitPrice_storage[markets[i]] = 1
                RuntimeMarket_eventPermille_storage[markets[i]] = 0
            end
            for i = 0, 828 do
                CargoBalances_CargoBalances_clear(TradeStore_contents_storage[stores[i]], stack)
                TradeStore_money_storage[stores[i]] = 0
            end
            CargoProvenance_CargoProvenance_clear(provenance, stack)
            assert(CargoProvenance_count_storage[provenance] == 0)
            assert(PlayableTradeRuntime_PlayableTradeRuntime_selectMarket(runtime,
                RuntimeMarket_id_storage[markets[0]], RuntimeMarket_goodName_storage[markets[0]], stack))
            PlayableTradeRuntime_hold_storage[runtime] = stores[0]
            assert(PlayableTradeRuntime_market_storage[runtime] ~= originalMarkets[8425])
            assert(PlayableTradeRuntime_hold_storage[runtime] ~= originalStores[828])
            reverse(markets, 8426)
            reverse(stores, 829)
            assert(markets[0] == originalMarkets[8425] and stores[0] == originalStores[828])
            __scale_mutated = PlayableTradeRuntime_PlayableTradeRuntime_capture(runtime, stack)
            assert(__scale_mutated ~= __scale_saved, 'Mutation did not change the serialized state')
            report.mutatedMarkets, report.mutatedStores, report.clearedLots = 8426, 829, 829
            report.catalogueOrderChanged, report.selectionChanged = true, true
        end)
        step(row, 'reconstruct_through_actual_compiled_functions', function()
            report.reconstructReturned = PlayableTradeRuntime_PlayableTradeRuntime_reconstruct(runtime, __scale_saved, stack)
            assert(report.reconstructReturned == true, 'Actual reconstruct returned false')
            assert(markets[0] == originalMarkets[8425] and stores[0] == originalStores[828],
                   'Reconstruct unexpectedly reordered catalogue arrays')
            assert(PlayableTradeRuntime_market_storage[runtime] == originalMarkets[8425],
                   'Selected market identity was not restored')
            assert(PlayableTradeRuntime_hold_storage[runtime] == originalStores[828],
                   'Selected hold identity was not restored')
            assert(PlayableTradeRuntime_settlementId_storage[runtime] == report.selection.savedMarketId)
            assert(PlayableTradeRuntime_marketSelected_storage[runtime] == false)
            assert(PlayableTradeRuntime_storeSelected_storage[runtime] == false)
            assert(CargoProvenance_count_storage[provenance] == 829)
            report.restoredLots, report.selectionRestored = 829, true
            report.transientSelectionFlagsCleared = true
        end)
        step(row, 'restore_original_order_and_compare_every_saved_byte', function()
            reverse(markets, 8426)
            reverse(stores, 829)
            for i = 0, 8425 do assert(markets[i] == originalMarkets[i]) end
            for i = 0, 828 do assert(stores[i] == originalStores[i]) end
            __scale_restored = PlayableTradeRuntime_PlayableTradeRuntime_capture(runtime, stack)
            assert(__scale_restored == __scale_saved, 'Whole populated capture differs after restore')
            report.catalogueOrderRestored, report.exactCaptureEquality = true, true
            report.restoredBytes = #__scale_restored
        end)
    end, false)
    assert(__scale.roundtrip.exactCaptureEquality == true)
end
