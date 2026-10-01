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

## Automated native save/load runner

`NativeSaveRegressionFixture.wurst` is a dormant, developer-controlled fixture
compiled into the packaged Lua map. It is never imported by `Bootstrap`; a
runner invokes its public lifecycle hooks. The fixture records authoritative
campaign/autosave/map/modal state in game cache, creates owned runtime objects,
uses native `SaveGame`, and reconstructs timers, frames, effects, sound and unit
representations after load. Unsafe transition, capture and campaign-commit
requests are deferred before the native call.

Run the always-available oracle and structural checks with:

```sh
python3 tooling/run_native_save_regression.py
```

No configured runtime produces canonical `status: "skip"` output and exit 0;
`--require-runtime` converts that condition to exit 1 for the dedicated CI job.
A configured runner crash, timeout, malformed result, or state mismatch is
always a failure.

For a native cycle, first package the map with `./tooling/package_release.sh`,
then set `WC3_NATIVE_SAVE_RUNNER` to a command and pass its `.w3x` using `--map`.
The command receives `--request <json> --result <json>`. Exact host capabilities,
timeout and protocol are locked in `scenario/benchmarks/native-save.json`. The
runner must launch Warcraft III 3.0 noninteractively, invoke the fixture hooks,
create and load the native save across a restored process/session where the host
supports that isolation, recover a deliberately missing representation, perform
the requested repeated loads, and write the observed canonical result. No
player interaction is part of this gate.
