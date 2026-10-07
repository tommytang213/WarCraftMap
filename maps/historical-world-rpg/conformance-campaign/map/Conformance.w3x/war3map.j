// Wurst retains this main body before adding package initialization.
// Initialize Blizzard's shared state before campaign timers and services use it.
function config takes nothing returns nothing
endfunction

function main takes nothing returns nothing
    call InitBlizzard()
endfunction
