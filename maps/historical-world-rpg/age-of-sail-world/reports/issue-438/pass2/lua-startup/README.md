# Executed Lua boundary experiment (2026-10-10)

**No native crash cause was established.** This is a new execution of the exact
failing selector's Lua, independently of the Wurst interpreter. It narrows the
remaining investigation; it is not Warcraft execution, a fixed map, or a
qualified native positive control.

Input is the unmodified `war3map.lua` extracted from smoke #3 selector W3X
`3c953659969c956e509093cb2732aaf1e2d94ed6355556a98204637ab1cb1f16`.
The input Lua SHA-256 is
`efaffe67682ca0c3c952722ce0a5f42be1ba954a27c5ad49177f48b6c536ebe3`.
The host loads the already installed system Lua 5.4 shared library through its
documented C API; no new program is downloaded or installed. Its library and
three harness source hashes are in `results.json`. The retail client's exact
Lua build, compile options and API bindings have not been established.

## Experiment

`boundary.lua` explicitly defines the small set of external functions reached
by this map, records native-side operations and checks handle kinds/liveness.
Unimplemented natives remain undefined and cause ordinary Lua failures if called.
`exercise.lua` loads the complete archived script, calls `config`, calls `main`,
then fires the recorded zero-delay callback. It requires both the bootstrap and
origin-page messages, 230 registered origins, paused selection, and no captured
Lua initialization/callback error. It does not infer success from merely reaching
`main` or starting a timer.

| Controlled case | Result | What it establishes |
|---|---|---|
| Exact smoke #3 script, successful typed boundary allocations | Pass: origin page 1/29, 230 origins, no Lua errors | The archived Lua can complete this startup path with the explicit recorded API behavior. |
| Same script, `InitGameCache` returns nil | Same page reached | A missing game-cache handle is not dereferenced by this Lua path before presenting origins. |
| Same script, `CreateTimer` returns nil | Expected failure: only bootstrap text, no origin page | Earlier bootstrap text does not fool the milestone check. |
| Same script, deliberate nil player argument after callback | Expected failure: live-player type check | The native recording boundary rejects invalid handles rather than accepting every call. |
| One mutation: missing function in `xpcall(init_Bootstrap, ...)` | Expected failure: recorded Lua error and missing page | Real package initialization errors are detected; the mutated script has a separate recorded hash. |
| Isolated package tail: replace only 35 main-entry package calls with two diagnostic markers | Pass: immediate and delayed markers; Bootstrap/ScenarioSettings remain uninitialized | The revised diagnostic Lua parses and follows the intended boundary path. |
| Same isolation, wrong timer-marker text | Expected failure: missing timer marker | Merely reaching the main-tail marker cannot satisfy the diagnostic. |
| Wrong baseline hash supplied to isolation transformer | Expected refusal | The transformer cannot silently derive the experiment from different source. |

These are **harness controls**, not native positive/negative control maps.
All eight outcomes are asserted by the command's exit status.

## Observed order and exclusions

The root chunk makes no calls to the defined native boundary. The archived
`config()` is populated by Wurst: it sets the map name, player/team counts,
placement, start location, color, race, controller, team, and priorities.
The empty `config()` in the authoring JASS therefore does **not** demonstrate
missing compiled configuration.

`main()` executes pure-Lua Wurst bootstrap/global/compile-time table setup,
then `SetDayNightModels`, then `InitBlizzard`. Package execution reaches
`Location`, `GetLocalPlayer`, timers, force/group creation, `InitGameCache`,
trigger creation, 24 player-chat registrations and bootstrap text. The deferred
origin callback destroys its timer, calls `PauseGame(true)` and emits the full
origin page through `DisplayTimedTextToPlayer`.

No frame creation/manipulation, unit/item creation, custom-model loading,
game-cache read/write, save operation or map transition is reached before this
page. References to such functions elsewhere in source are not evidence that
this minimal selector executes them. It presents text, not a custom frame UI.

## Limits

`InitBlizzard` is one opaque recorded call; this experiment does not reproduce
its internals, renderer state, map loading, native threading, return-value
semantics or retail client crashes. Handles are typed Lua tables. String helpers
use byte-oriented Lua operations; `StringHash` is a deterministic surrogate,
not Storm's algorithm. The player-count constants are boundary inputs, not
measurements from the owner's running client. Periodic callbacks, chat selection,
handoff, saves and regional maps are outside this experiment. The exact source
may still crash through a native operation even though the recording boundary
accepts its arguments. This result cannot eliminate an engine-sensitive ordering
or initialization omission.

An independently authored editor Lua fixture was also read from War3Net's
[`NewLuaMap.w3m`](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/tests/War3Net.TestTools.UnitTesting/TestData/Maps/NewLuaMap.w3m).
Its archive SHA is `6aba03735fa21802249971dfe4ded3cfcc988e4f48add08cf497b057d2e9e631`,
Lua SHA is `3f58806055f4f7499d79ae0c1afe1c0bfecfcb0b4bb8b5c37f92aa42c09640c5`,
and its producer is 1.31.1.12164, **not 3.0**. Its main additionally sets camera,
audio and music before Blizzard initialization. Its config additionally invokes
generic slot setup. Those differences are hypotheses, not independent proof
that our configuration is invalid. No corresponding speculative call was added.
It is not a locally qualified native control.

`../isolation_lua.py` implements the next native discriminator: preserve the
original script's root/config, functions and native initialization spine, and
replace only the 35 executed Wurst package-initialization calls with immediate
and delayed visible markers. It pins the input hash and exact initializer
sequence. The resulting script SHA-256 is
`7b989c6ba232655f90620169628190a9a5eeea29f595a142331f6b740f9ffdba`.
It makes no speculative camera/audio calls and does not pause the game. A same-client pass
would implicate omitted package execution; a failure would leave loader and
native-spine causes open. It would not establish full campaign playability.
Packaging and archive identity are recorded separately by the package builder.

## Reproduce

From the repository root, after extracting the hash-confirmed baseline Lua:

```sh
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-438/pass2/lua-startup/trace.py \
  --lua build/issue-438/baseline/selector.lua \
  --library /usr/lib/x86_64-linux-gnu/liblua5.4.so.0 \
  --output build/issue-438/startup/reproduced.json
```

Expected: eight `true` checks, exit 0. An absent system Lua 5.4 library is an
external prerequisite; this script does not install one automatically.

Host API reference: [Lua 5.4 manual](https://www.lua.org/manual/5.4/manual.html#4).
