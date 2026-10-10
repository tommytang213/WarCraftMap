# Local standalone-map diagnostic

Default status is `native_runner_unavailable`, `map_standalone_native=not_run`,
`campaign_native=not_run`. No program starts unless the owner supplies `--run`.
This is a portable adapter, not a bundled/approved WGC installation. Python 3.10+
and a separately reviewed local WGC 1.1/Lua copy are required. No accounts,
service, VM, remote access, self-hosted runner or scheduled launches are used.

WGC source/dependency/license review is **incomplete**: the upstream download
was unavailable during #438 (HTTP 403; web download cache miss). Nothing from
that bundle was executed or vendored. Do not fill approval fields by guessing.
Review all Lua dependencies, bundled executables/DLLs, process creation and
filesystem writes before producing the local approval. Keep it outside the
reviewed bundle and do not commit personal paths. If review cannot establish
the adapter's scratch/write and child-process assumptions, stop here.

The [WGC author's documentation](https://www.hiveworkshop.com/threads/wgc-utility-1-1-%E2%80%94-test-maps-at-high-game-speed.341181/)
describes standalone `--map`/`--gameexe` launch, 1x as speed 1, and different
`-loadfile` path handling for Classic and Reforged. It does not prove 3.0.x path
semantics or full W3N support. This adapter requests Reforged absolute paths;
the positive control must establish they work on the exact executable/build.
Do not use `--classic`, change speed, or infer behavior from 1.27/1.31 results.

Preparation verifies the original W3N SHA, independently reads every manifest
map with pinned mpyq, and copies the requested W3X **without changing a byte**.
`diagnostic.json` records map/source/compiler identities. The original W3N is
never modified. `corrupt-control.w3x` is deliberately truncated MPQ data, created
separately. It is not a repaired map. The War3Net JASS fixtures are format
references; they are not a known-working 3.0 Lua positive control.

Before any targeted session, a developer must provide a known-working Lua map
with SHA, native provenance and the same retail build. One controlled session
consists of positive control, corrupted control, then the exact selector. If
either control behaves unexpectedly, stop; do not attribute a target failure
to the campaign. This adapter does not request a player session now.

The provisional slot profile is human player 0, team 0, human race, red, 100%
handicap, plus observer slot 1 on team 0. WGC 1.1 documents an observer check.
The selector declares human slot 0. This extra observer/context must work on
the positive control and permit interacting with origin selection; otherwise
the profile is unqualified. Do not substitute observer-only success for UI
interaction. Keep this same profile, executable and WGC bundle across cases.

Example **local-only** approval shape (all hashes must be complete SHA-256;
`files` must enumerate every file in the isolated reviewed WGC/Lua folder):

```json
{
  "format": "wgc_local_approval_v1",
  "ownerApproved": false,
  "upstreamVersion": "1.1",
  "review": {"source": false, "dependencies": false, "license": false},
  "bundle": "C:/diagnostics/reviewed-wgc-1.1",
  "files": {"wgc-launch.lua": "FULL_SHA256", "lua.exe": "FULL_SHA256"},
  "lua": "lua.exe",
  "script": "wgc-launch.lua",
  "gameRoot": "C:/Games/Warcraft III/_retail_",
  "gameExe": "C:/Games/Warcraft III/_retail_/x86_64/Warcraft III.exe",
  "gameExeSha256": "FULL_SHA256",
  "clientBuild": "3.0.0.24268",
  "allowGameRootScratch": false,
  "reviewedWriteScope": "UNCONFIRMED",
  "reviewedLoadfileMode": "UNCONFIRMED",
  "war3Log": "C:/explicit-local-path/War3Log.txt",
  "positiveControl": {
    "path": "C:/diagnostics/known-working-lua.w3x",
    "sha256": "FULL_SHA256",
    "knownWorkingClientBuild": "3.0.0.24268",
    "scriptLanguage": "Lua",
    "provenance": "REQUIRED: actual native gameplay observation and date"
  }
}
```

Only after review may `reviewedWriteScope` be set to
`session_and_game_root_map-wgc-test_only` and the opt-ins enabled. No elevation
is requested. Review the actual `-loadfile` command construction before setting
`reviewedLoadfileMode` to `reforged_absolute`; the positive control must then
confirm it in the retail client with a matching new War3Log opening-map entry.
If WGC cannot work without other installation changes, leave the
runner unavailable. The adapter refuses existing game processes or an existing
`map-wgc-test` directory. A Windows Job Object bounds this invocation and its
children to 90 seconds and terminates them on timeout, early launcher exit
after children finish, or Ctrl-C. Only its own scratch directory is cleaned.
Windows process handling has not been executed in Linux CI.

From the prepared package in PowerShell, the read-only/default check is:

```powershell
Get-FileHash -Algorithm SHA256 .\selector-*.w3x
python .\wgc_local_adapter.py
```

For the single future owner-initiated, qualified session:

```powershell
python .\wgc_local_adapter.py --approval C:/diagnostics/local-approval.json --case positive --run
python .\wgc_local_adapter.py --approval C:/diagnostics/local-approval.json --case negative --run
python .\wgc_local_adapter.py --approval C:/diagnostics/local-approval.json --case target --run
```

The adapter asks for the observed milestone after each bounded run. A positive
`gameplay_frames` and negative `load_rejected` receipt under identical pins are
required before the target can run. Record `origin_selection` only when the
selector UI visibly opens; a live process, loading screen, or `Played` log line
is insufficient. Target failure without that milestone means launch acceptance
was not established, not necessarily a native crash. Process-start evidence
describes the Lua launcher only. Appended War3Log evidence is reduced to counts
of matching loader entries. No raw logs, dumps, paths or credentials are uploaded.
Receipts are local assertions, not automatic release acceptance evidence.

Standalone success suggests investigating outer W3F/routing or campaign context.
Standalone failure with passing controls suggests a map/runtime/client branch,
but missing campaign game-cache context remains a confounder. A full retail
Custom Campaigns W3N launch is always required separately. Do not set
`campaign_native=passed` from this adapter or rerun unchanged campaign bytes.
