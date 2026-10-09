// Wurst retains this main body before adding package initialization.
// Initialize Blizzard's shared state before campaign timers and services use it.
function config takes nothing returns nothing
endfunction

function main takes nothing returns nothing
    // The source terrain uses Lordaeron lighting. InitBlizzard does not load
    // these renderer resources; the editor normally sets both before it.
    call SetDayNightModels("Environment\\DNC\\DNCLordaeron\\DNCLordaeronTerrain\\DNCLordaeronTerrain.mdl", "Environment\\DNC\\DNCLordaeron\\DNCLordaeronUnit\\DNCLordaeronUnit.mdl")
    call InitBlizzard()
endfunction
