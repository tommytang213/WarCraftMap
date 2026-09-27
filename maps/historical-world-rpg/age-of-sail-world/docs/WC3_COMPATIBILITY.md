# Warcraft III compatibility boundary

`wurst/WC3Compatibility.wurst` is the reusable boundary between runtime systems
and patch-specific natives. The current target is Warcraft III 3.0 with the Lua
backend, pinned by `wurst.build`. Inventory/equipment, native save management,
frame UI, pathing/positioning, and modern unit access use its public adapters. It
contains no scenario IDs or behavior.

Capabilities are explicit. `requireWC3Compatibility()` runs at initialization
and aborts instead of silently degrading. The compile fixture makes a missing
native fail at build time.

## Adding a later patch family

1. Update the pinned Wurst toolchain, run `grill patch`, review its native diff,
   and only then deliberately align `wurst.build` and core JASS.
2. Change adapters and flags only in `WC3Compatibility.wurst`; keep stable public
   semantics or fail explicitly.
3. Extend the compile fixture; run the direct-native check, `grill typecheck`,
   `grill test`, and all repository checks.
4. Build and structurally inspect the canonical archive and Lua payload with
   `./tooling/package_release.sh`.
5. Regress inventory/equipment, UI lifecycle, safe-position/pathing, unit fields,
   native WC3 save/load, and campaign-save migration. Native save/load gameplay
   validation is a patch-migration release gate, not incremental player QA.

Do not put patch conditionals in gameplay packages. Add a separate implementation
behind this boundary if multiple patch families must coexist.
