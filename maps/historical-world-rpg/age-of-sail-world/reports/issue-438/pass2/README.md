# Issue 438: package-initialization isolation, 2026-10-10

**Native root cause remains unproven. Baseline retail launch remains FAILED.**
No gameplay, production packager, source-map metadata, save schema, release
gate or worker implementation is changed by this follow-up. Do not close #438.

The useful new result is execution of the **actual failing compiled Lua** through
origin presentation under a bounded Lua recording environment, plus one prepared
native experiment which skips package initialization without rebuilding maps.
It is more specific than repeating PR #442's archive/field-layout comparison.

## Baseline and ownership

Started on main `bac9d0c29e83fc677ea38ec6acdbd44745270022` in a new isolated
checkout/branch, `fix/438-native-startup-investigation`. PR #453 was still open;
the pending one-time resume marker in #438 was superseded and PR #453 notified.
No VM state, worktree or running Codex process was touched.

Downloaded the original artifact from run `37864283149`, artifact `11587974377`.
Verified ZIP `6fb8726ef81a80df057cbdeece995e022d36cc2d45bf7d01f6c44e024819af8f`,
W3N `4f2f9cf8ca56f81aaeca524f257ae15e273c2366e52adfaa1eafdf5b996ff9ad`,
selector W3X `3c953659969c956e509093cb2732aaf1e2d94ed6355556a98204637ab1cb1f16`
and Lua `efaffe67682ca0c3c952722ce0a5f42be1ba954a27c5ad49177f48b6c536ebe3`.
Original bytes stay unchanged under `build/issue-438/baseline/`.

Recorded retail evidence remains 3.0.0.24268 / 3.0.1.24342, access violation
reading `0x3A0` with `RCX=0`, instruction `48 8B 89 A0 03 00 00` before origins.
No symbol or trace identifies that engine object. `Played` is not acceptance.

## New discriminating work

| Hypothesis | Evidence and experiment | Conclusion / remaining discriminator |
|---|---|---|
| Metadata values differ from reference, therefore malformed | Read pinned War3Net enum semantics as well as layouts: expansion flag 2, campaign Human 0, default background 0, map TFT data 1, SD+HD 3 and User controller 1 are supported. Reference Unset values are not mandatory defaults. | No demonstrated malformed field; no speculative v31→v39 conversion. A campaign-context native failure remains possible. |
| Empty authored config or omitted generic slot helpers loses player setup | Exact generated config has player/team/controller/start-location calls. Pinned Wurst/wc3libs deliberately emits custom setup; generic BJ helpers are not dropped by transpilation. | No demonstrated config-generation defect. Native acceptance remains separate. |
| Lua package/global ordering or missing cache handle fails before origins | Execute exact Lua in installed Lua 5.4 with explicit typed native substitutes. 230 origins/page 1 of 29 appear, with no recorded Lua error; nil cache still reaches the page. Missing timer, nil player, missing Bootstrap and missing diagnostic marker are rejected controls. | New bounded execution evidence, not engine emulation. Does not rule out native initialization sensitivity or renderer failure. |
| A custom model, unit or frame created by selector startup crashes | Executed trace reaches no frame, unit/item creation or custom model API before origins. Selector physical members retain stock terrain, no doodads and one `sloc`. | Those specific application paths are not reached. Native stock asset/terrain loading is still opaque. |
| Wurst package execution is required for the crash | New W3N retains exact Lua root/config/functions and existing main prelude, then replaces only 35 package init calls with immediate/deferred markers. | Native outcome pending. Stable markers would implicate the omitted execution path; matching failure would show that path is unnecessary. Neither identifies a particular native by itself. |

Detailed executable evidence and all eight assertions are in
[`lua-startup/README.md`](lua-startup/README.md) and `lua-startup/results.json`.
The runtime is **host Lua 5.4**, with an unestablished retail Lua build and
substituted handles. `InitBlizzard` is opaque. This is deliberately not labelled
`headless Warcraft` or native acceptance.

## Independent primary-source comparisons

- War3Net commit `18e88f0e1f67e6b16870dcbcd827740275fe2173`,
  [`Info` enums](https://github.com/Drake53/War3Net/tree/18e88f0e1f67e6b16870dcbcd827740275fe2173/src/War3Net.Build.Core/Info):
  `CampaignFlags`, `CampaignRace`, `GameDataSet`, `GameDataVersion`,
  `PlayerController`, `PlayerRace`, `SupportedModes`.
- Pinned compiler [`ProjectConfigBuilder.java`](https://github.com/wurstscript/WurstScript/blob/edd2e5e74898b3e15beaeb4e8887cab8875e982e/de.peeeq.wurstscript/src/main/java/de/peeeq/wurstio/languageserver/ProjectConfigBuilder.java)
  delegates config creation to wc3libs; its pinned
  [`W3I.java`](https://github.com/inwc3/wc3libs/blob/5ad2e5be4c480bb14112222521e6bc5571d00076/src/main/java/net/moonlightflower/wc3libs/bin/app/W3I.java)
  emits custom player/team/priority functions. The corresponding
  [`Blizzard Lua fixture`](https://github.com/wurstscript/WurstScript/blob/edd2e5e74898b3e15beaeb4e8887cab8875e982e/de.peeeq.wurstscript/src/test/resources/luaruntime/blizzard.j.lua)
  shows generic slot bookkeeping and no team rearrangement in map-settings mode.
- The independently authored stock control uses the same Lordaeron day/night
  model paths. Its camera/audio calls differ; that alone is not evidence that
  adding those calls repairs this null read.

## One manual-only native package

[`CONTROL-PROVENANCE.md`](CONTROL-PROVENANCE.md) records an MIT-licensed 29.5 KB
Lua map with **author-reported** 3.0.0.24268/classic gameplay. The exact pinned
release bytes were reviewed, but the author did not publish a test-time hash.
Thus it is a candidate positive control: the owner must first qualify those
bytes in the same client/graphics context. No qualified local native pass is
invented. The truncated-MPQ negative control must be clearly rejected; an
ambiguous menu return or native crash does not qualify it.

`build_isolation.py` produces a versioned installed W3N, controls, full SHA-256
list, provenance and [`OWNER-TEST.md`](OWNER-TEST.md). It launches nothing and
needs neither WGC nor a Windows runner. WGC remains unreviewed/unavailable;
its adapter and release gates are untouched.

`mpq_patch.py` edits only the target allocation and necessary encrypted block
table sizes. Archive lengths and member offsets stay fixed. It rejects
attributes/signatures, encryption on the target, aliases, overlapping ranges,
unsupported compression and growth. An identical replacement is byte-identical.
The builder independently decodes before/after using the existing reviewed mpyq
pin; encrypted listfiles are the explicit exception. It verifies all 17 map
hashes and that all 47 other selector members, all 16 regional maps, W3F and W3I
are unchanged. Outer changed members are only the selector and its manifest SHA.

This is a diagnostic derivative of the original compiled revision, **not a new
full compilation or release candidate**. Original archived build identity stays
intact and is explicitly distinguished from recipe revision and override hash
in the receipt. There is no renamed-copy repair claim.

Native interpretation is conditional on controls, observed markers and the
confirmed-failing client/graphics context. A pass after an update or graphics
change does not isolate package execution as causal; do not rerun the old build
to fill that evidence gap. A familiar crash dialog does not prove a matching
exception signature. Changed
compressed Lua bytes still require Blizzard's decoder to accept them; independent
decoding cannot prove that. If a result is ambiguous, do not diagnose package
code solely from that ambiguity. No original full campaign retest is requested.

## Reproduce and validate

From repository root, with the pinned baseline and reviewed mpyq source acquired
as documented in the parent report:

```sh
python3 -m unittest discover -s maps/historical-world-rpg/age-of-sail-world/tests -p test_launch_isolation.py -v
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-438/pass2/lua-startup/trace.py \
  --lua build/issue-438/baseline/selector.lua \
  --library /usr/lib/x86_64-linux-gnu/liblua5.4.so.0 \
  --output build/issue-438/pass2/lua-verification.json
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-438/pass2/build_isolation.py \
  --campaign build/issue-438/baseline/Campaigns/AgeOfSailWorldCampaign.w3n \
  --reader build/issue-438/upstream/mpyq.py \
  --control-root build/issue-438/balancebench-v1.0.0 \
  --output build/issue-438/owner-isolation
bash automation/run_checks.sh
```

The builder requires its recipe files to match the current commit exactly;
commit changes before generation. Obtain the control at tag `v1.0.0`, verify
revision `b1d956d28f957f160fc282623186d9fe21ff74af`; the builder checks map,
license and upstream test-report hashes. It refuses existing output directories.
Final command outcomes and package hashes are recorded separately in the
follow-up validation receipt, so historical PR #442 results are not reused as
new evidence.

## Shortest remaining path

One owner-initiated controlled session distinguishes package execution from
retained loading/native initialization. Then narrow that side using a specific
failing call or field, implement its evidence-supported repair, rebuild and run
required CI, and finally establish retail origin selection and campaign handoff.
Until then there is no defensible gameplay repair and #438 remains open.
