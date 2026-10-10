# Published native Lua control candidate

`BalanceBenchStockTest.w3x` is a small, independently authored Lua map with a
published retail-client execution report. It is a **candidate positive control**,
not a native pass measured by this investigation. It must visibly run on the
owner's same client and graphics configuration before a diagnostic comparison is
interpreted. No WGC, external executable, account setup or unattended run is
required by this evidence.

## Pinned source and identity

- Author/project: [KSAGlory/WC3-BalanceBench](https://github.com/KSAGlory/WC3-BalanceBench).
- Release `v1.0.0` resolves to commit
  `b1d956d28f957f160fc282623186d9fe21ff74af`.
- [Unmodified stock map](https://github.com/KSAGlory/WC3-BalanceBench/blob/b1d956d28f957f160fc282623186d9fe21ff74af/Map/BalanceBenchStockTest.w3x):
  29,511 bytes; SHA-256
  `de049fd937253244edf7eb00dc7f938ca51835a95f39d5e5f0d04ed74439ef95`.
- Git blob: `00bb921d4061a5d4cb491c9eed6ebffb8b621aa2`.
- Embedded `war3map.lua` SHA-256:
  `9cb0d9f3b326334b4fecc3aaa215cedf39c65ea59723b312024956945f33097f`.
- Embedded W3I reports format 39, producer `3.0.0.24268`, Lua.
- [MIT license](https://github.com/KSAGlory/WC3-BalanceBench/blob/b1d956d28f957f160fc282623186d9fe21ff74af/LICENSE):
  SHA-256 `71c28108b2a26d9f06bd79c581a4fbe8d0391efc5cb2742342d3c611089586d3`.
  Any distributed map copy must include this license and copyright notice.

The pinned
[verification report](https://github.com/KSAGlory/WC3-BalanceBench/blob/b1d956d28f957f160fc282623186d9fe21ff74af/Docs/TEST-RESULTS.md)
has SHA-256
`0dd576cd68e15fa3ea696ae2c8c55ab40722f87f0d9dcdaa1eff00f9b635ea3c`.
It reports Windows retail Warcraft III `3.0.0.24268`, **classic graphics**, on
2026-09-28. Its stock comparison uses the same packaged filename and configuration
found in this map: `footman-2v1 / stock-420hp`, two Footmen versus one Footman,
two rounds and a 45-second timeout. It records two completed rounds, side changes,
survivors, approximately 27.6/27.7 seconds, and a repeated in-game report.

This is stronger evidence than an editor-only format fixture, but the author did
**not publish a test-time map hash, client executable hash, recording or raw
execution receipt**. The release commit binds the supplied bytes and report; it
does not independently prove that these exact bytes were the ones executed.
The report also explicitly says the separate `BalanceBenchDemo.w3x` was rebuilt
after stress testing, so that demo was deliberately not chosen. No corresponding
post-test rebuild is stated for the stock comparison. HD mode, another client
version, campaign-wrapped execution and this owner's environment remain unproven.

## Source review boundary

The pinned repository was obtained read-only and its MIT license reviewed.
The stock archive was extracted with the repository MPQ reader; that reader's
complete-member enumeration found only ordinary map/editor resources, no imported
models, SLK overrides, custom unit objects, native executables or additional
runtime scripts. `war3map.lua` was read in full. Its normalized text contains the
pinned `Scripts/BalanceBench.lua` verbatim, followed by the stock test configuration
and explicit `config`/`main` functions.

The script uses ordinary Warcraft player/unit/timer/trigger/text natives and Lua
tables, arithmetic and protected calls. Review found no `io`, `os`, package loader,
dynamic code loader, `Preload`/preload-file generation, `ExecuteFunc`, game-cache,
save/load, network or external-process operations. The script installs chat
commands at map initialization; combat starts only after `-bb start`. It creates
and removes its own test units. No game code or third-party build tooling was
executed in this investigation.

A successful control shows `Installed: footman-2v1 / stock-420hp`; `-bb start`
should spawn the matchup and eventually show `COMPLETE` with `2/2` rounds.
`-bb report` repeats that result. These visible milestones qualify the local
control; a live process, loader entry or `Played` record does not.

The control has the same Lordaeron day/night model paths as the exact failed
selector. It additionally establishes camera and sound settings and uses a
newer W3I. Those differences are hypotheses to isolate, not evidence justifying
adding arbitrary initialization calls or upgrading the campaign format.

## Physical-map finding outside this crash

Independent decoding of the exact failed selector matches its authoring terrain,
pathing, empty doodads and one complete `sloc` placement. The selector bypasses
the regional terrain writer. In `materialize_physical_map.py::_w3e`, that writer
puts its intended texture index in the variation byte while leaving the texture
nibble zero. The pinned War3Net
[binary tile reader](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/src/War3Net.Build.Core/Serialization/Binary/Environment/TerrainTile.cs)
and [field accessors](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/src/War3Net.Build.Core/Environment/TerrainTile.cs)
independently establish the packing mistake. It affects regional tile selection,
cannot explain this first-selector failure, and belongs in a separate follow-up.
No terrain or gameplay repair is made on that basis here.
