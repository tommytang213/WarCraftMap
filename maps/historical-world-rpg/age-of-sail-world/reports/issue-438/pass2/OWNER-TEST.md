# Issue 438: one package-initialization isolation test

**Diagnostic only. This is deliberately not playable and is not a crash repair.**
No WGC, extra executable, installation, remote access or automatic upload is
included. Start these tests yourself when convenient. Do not replay smoke #3.

The revised campaign keeps all 17 maps, campaign metadata, terrain, assets,
player configuration and the original lighting/Blizzard initialization. It
replaces the first map's **35 Wurst package initialization calls** with two
visible markers. Origin selection is deliberately absent. Only the first
map's Lua payload and its manifest checksum change. Archived source identity
still identifies the original compiler inputs; `diagnostic.json` separately
identifies the exact diagnostic recipe revision and resulting hashes.

## Before you start

- Keep your normal graphics settings; record the Warcraft client version/build
  and graphics mode. The control's author tested **3.0.0.24268, classic graphics**.
  Other contexts must pass the control here; no downgrade is requested.
  Record whether these match your confirmed failing campaign session. If the
  client or graphics changed, a success cannot isolate package execution as the
  reason: that environment change may independently affect the old crash.
- Close Warcraft between cases. Keep all existing campaigns and saves. Move
  existing Age of Sail diagnostics temporarily **outside** the Campaigns folder
  so its unchanged menu title cannot select the wrong file.
- Extract this ZIP. Open PowerShell in the extracted folder and verify all files:

```powershell
$ErrorActionPreference = 'Stop'
Get-Content -LiteralPath '.\SHA256SUMS.txt' | ForEach-Object {
    if ($_ -notmatch '^([0-9a-f]{64})  (.+)$') { throw 'Invalid checksum line' }
    $expected = $Matches[1]
    $file = Join-Path (Get-Location) $Matches[2]
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        throw "Checksum mismatch: $file"
    }
}
'All checksums match'
```

## One controlled session

1. **Positive control.** Set `$gameExe` to your actual installed
   `Warcraft III.exe` path (do not guess a second installation), then run:

   ```powershell
   $gameExe = Read-Host 'Full path to your Warcraft III.exe (without quotation marks)'
   (Get-Item -LiteralPath $gameExe).VersionInfo.FileVersion
   & $gameExe -launch -loadfile (Join-Path (Get-Location) 'Controls\BalanceBenchStockTest.w3x')
   ```

   Confirm the in-game label **footman-2v1 / stock-420hp**. Enter `-bb start`;
   require **COMPLETE 2/2**, then `-bb report` repeats the result. This qualifies
   the control for this client/context. The upstream report has no test-time
   checksum, so its publication alone is not a local pass. If this fails, stop;
   report the control failure, not an Age of Sail result.

2. **Negative control.** Close Warcraft, then run:

   ```powershell
   & $gameExe -launch -loadfile (Join-Path (Get-Location) 'Controls\CorruptControl.w3x')
   ```

   This intentionally truncated MPQ must be rejected as an invalid/unloadable
   map. A crash, another map starting, or merely returning to a menu without a
   clear rejection is **inconclusive**; stop rather than counting that as a pass.

3. **Revised campaign.** Close Warcraft. Copy the single versioned `.w3n` from
   this package's `Campaigns` directory into your actual Warcraft III
   `Campaigns` directory. Keep that exact filename; do not overwrite or edit it.
   Open Warcraft normally: **Single Player → Custom Campaigns → Age of Sail:
   The World → Begin the Campaign**. Watch for:
   - `438: main tail reached`
   - `438: timer reached`

   Wait 10 seconds after the second marker. Record which markers appeared and
   whether the client stayed running or showed a native error. No origin menu
   is expected in this isolation build. Exit normally; no save is needed.

## What this establishes

| Observation, after both controls qualify | Interpretation |
|---|---|
| Both markers and stable map, in the same confirmed-failing client/graphics context | Supports investigating the omitted package execution next. It does not prove causality or establish gameplay acceptance. |
| Both markers and stable map, but the client/graphics changed or earlier settings are unknown | Establishes only that this diagnostic runs in this context; no package-causality inference. Do not rerun the old campaign to fill the gap. |
| First marker only | Main reached the replacement tail; failure is later in timer/render/game startup. Exact timing/error is needed. |
| Native crash before markers | This variant fails without package execution. Focus next on retained initialization/loading/context. Only a matching exception signature would establish the same native fault; the error dialog alone does not. |
| Different failure or no clear marker observation | Inconclusive; do not infer the crashing native or a repair. |

Share the package identity from `diagnostic.json`, client build/graphics mode,
control results and observed marker/error. A screenshot is enough initially;
do not publish private logs or dumps. A `Played` log entry alone never passes.
Keep #438 open regardless of this diagnostic result.

## Cleanup

Remove only this versioned diagnostic from the Campaigns folder and restore any
campaigns you temporarily moved. The package does not alter game installation
files or existing saves. The control and full campaign remain separate contexts;
standalone control success does not prove W3N compatibility.
