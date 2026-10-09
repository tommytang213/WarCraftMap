# Issue #438: persistent Begin Campaign crash

**Diagnosis: `diagnosis_unconfirmed`. Real-client launch: FAILED. Do not close
#438 as repaired.** This change implements investigation evidence, versioned
diagnostic identity and an opt-in local WGC adapter. It makes no gameplay,
startup, object, map-format or save-schema repair. No player retest is requested.

## Baseline preserved before implementation

Downloaded [Actions run 37864283149](https://github.com/tommytang213/WarCraftMap/actions/runs/37864283149),
artifact `11587974377`, `age-of-sail-LAUNCH-SMOKE-NOT-RELEASE-3`, using existing
authenticated, read-only access. Original files, ZIP, manifest, map and pinned
source checkout are retained locally under `build/issue-438/baseline/` at the
repository root; no input was rewritten. Private chat attachments were neither
requested nor accessed. `smoke-3-build-receipt.json` is an **unchanged historical
receipt**: its old `not_revalidated` claim is superseded by the confirmed failure.

| Identity | Verified value |
|---|---|
| Outer artifact ZIP SHA-256 | `6fb8726ef81a80df057cbdeece995e022d36cc2d45bf7d01f6c44e024819af8f` |
| Failing W3N SHA-256 | `4f2f9cf8ca56f81aaeca524f257ae15e273c2366e52adfaa1eafdf5b996ff9ad` |
| Source revision | `1bdfe32feae8775979735d89a379ecfdd0b28c83` |
| Recomputed pinned source-tree SHA-256 | `30e90e93d033d0f1b869de6aba4e3c90ca1fc8000771195addbdc9f0f113e230` |
| First embedded map | `Maps/AgeOfSailWorld.w3x` |
| Exact first-map SHA-256 | `3c953659969c956e509093cb2732aaf1e2d94ed6355556a98204637ab1cb1f16` |
| First-map Lua SHA-256 | `efaffe67682ca0c3c952722ce0a5f42be1ba954a27c5ad49177f48b6c536ebe3` |
| Checkout base for this implementation | `b27e1bf76c0e2aed24ae85f0d48db0fb5f05162d` |
| Checkout source tree before edits | `bbb1d0665e876b0eef9c40d5c93dac046e298016ebac563a23e0386865e6fe97` |

The pinned tree was recovered with `git archive`, and `source_identity` was
recomputed against it. It agrees with both the original build receipt and the
map's archived `runtime/build-identity.json`. This checkout is newer than the
failing build; it is not relabeled as that build. All 17 nested maps match their
original internal manifest hashes. ZIP and W3N checksums are distinct.

The following native facts come from the owner's sanitized issue evidence,
not from local dump analysis:

| Observation | Smoke #2 | Smoke #3 |
|---|---|---|
| Actual retail client | 3.0.1 build 24342 | 3.0.0 build 24268 |
| Main-thread exception | `0xC0000005`, read `0x3A0`, `RCX=0` | same |
| Executable fault RVA | `0x8E3F42` | `0x8CAA02` |
| Instruction bytes | `48 8B 89 A0 03 00 00` | same |

The repeated null-base dereference supports a repeated engine path, not a
specific object identity. The latest dump timestamp is `2026-10-09T14:09:19Z`.
The log opens the campaign and first map, then records `Played`; none establishes
origin UI or gameplay. No Lua exception is established. The screenshot GUID
does not independently identify the exact dump. Editor visibility of the title
and 17 maps establishes editor readability only. Missing WTG/WCT trigger data
and campaign-level Custom Data displays are separate editor symptoms.

## Independent archive and format observations

The separately downloaded, unmodified
[mpyq source](https://github.com/eagleflo/mpyq/blob/6bfba18ec403f702666b4109db3d95f3b97b1dc5/mpyq.py)
was inspected before importing it. Pin: `6bfba18ec403f702666b4109db3d95f3b97b1dc5`;
source SHA-256 `e10fa2f422d837345f438934a99a3cdf67fa9148c7106d421408e1ecfa83e239`.
Its BSD license was inspected; no third-party code was vendored. The adapter
checks that hash before import. The repository reader is supplemental only.

`independent-archive.json.gz` records agreement for all 20 outer members and
814 nested members. Each map's encrypted `(listfile)` is unsupported by mpyq:
17 exclusions are explicit. The repository reader supplies those nested member
names, then mpyq independently decodes their payloads. This is not a claim of
independent decryption of listfiles or native MPQ acceptance.

The pinned [War3Net reference campaign](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/tests/War3Net.TestTools.UnitTesting/TestData/Campaigns/campaign_3.0.0.w3n)
SHA is `aac17d7739cf181e59846808960d0ccdbf0ccadbd68e6b18df0cbdf5079f1530`.
The [3.0 empty-map fixture](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/tests/War3Net.TestTools.UnitTesting/TestData/Maps/patch_3.0.0_Empty.w3x)
SHA is `18af23464674350adf20270e070766ce4894f5e878ccae3c1034b88c02281893`.
War3Net's MIT license and binary-reader sources were inspected. These are
independent **format references**, not a locally established working Lua/native
positive control. Both archives use raw MPQ. No proven same-client Lua control
is available here; claiming otherwise would overstate the evidence.

`compare.py` uses an offset-recording investigation cursor based on the pinned
[CampaignInfo](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/src/War3Net.Build.Core/Serialization/Binary/Info/CampaignInfo.cs),
[MapInfo](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/src/War3Net.Build.Core/Serialization/Binary/Info/MapInfo.cs)
and [PlayerData](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/src/War3Net.Build.Core/Serialization/Binary/Info/PlayerData.cs)
layouts, separately from the production parsers. It consumes the actual W3F
(732 bytes), selector W3I (299), reference W3F (217) and reference W3I (381)
exactly. It supports these fixtures, not arbitrary Warcraft formats.
`format-comparison.json.gz` records every field's offset, size and value.

| Actual member / offset | Observed selector value | Reference / implication |
|---|---|---|
| W3F `0` | format 3 | reference also 3 |
| W3F `12` | title `Age of Sail: The World` | supported title field; deliberately untouched |
| W3F `149`, `184` | flags 2, race 0 | reference flags 4 at 60, race 4 at 112; distinct settings, not a demonstrated violation |
| W3F `216`, `262`, `286` | one button, exact first-map path, 17 map records | all references resolve in the verified outer archive |
| W3I `0`, `12` | format 31; producer 3.0.0.24268 | reference format 39; same producer label |
| W3I `191`, `199`, `203`, `211` | Lua 1, game-data version 1, one player, human controller 1 | reference JASS 0 at 217, game-data version 2 at 225; not equivalent script/data contexts |

The v39 fixture has additional HUD/fog/water fields that the v31 format does
not prescribe. Blindly inserting them or bumping the version would confound the
test. Physical-header receipts retain exact bytes/hashes. The actual selector
has W3E v11, a 256-by-256 WPM payload (65,552 bytes including header), a 65,536-byte
shadow file, zero placed doodads and one `sloc` start-location record. No new
physical-record violation was demonstrated. Supplemental existing structure
checks remain separate from this independent evidence.

The actual Lua includes `SetDayNightModels` followed by `InitBlizzard` (lines
2584–2585), after Wurst bootstrap/global setup and before package initialization.
That is a static call-site observation, not an executed native trace. Thus #430
did repair an omission, but **that omission is insufficient to explain the
hash-confirmed smoke #3 failure**. Neither the old call contract nor a new
guessed initialization call can establish crash causality.

## Hypotheses and discriminators

| Hypothesis | Evidence for | Evidence against / limits | Falsifiable controlled test and expected interpretation |
|---|---|---|---|
| Outer W3N/W3F or routing | failure starts through Custom Campaigns | W3F fully decodes; exact chapter exists; editor opens it | Same exact selector standalone with qualified controls: success shifts attention to campaign metadata/context; matching failure means the outer container is not necessary for that failure, subject to lost campaign context. |
| Embedded W3X/W3I/physical records | crash occurs during first-map loading | independent payload agreement and complete field decoding; no identified malformed field | If standalone fails with passing controls, a later minimal-script fixture retaining physical members can test whether failure precedes gameplay script. No such revised W3N is produced now. |
| Lua startup | origin UI never appears; generated initialization differs from editor script | lighting and Blizzard calls are already present; no established Lua exception | On the later controlled minimal fixture, reaching a visible main-entry milestone while original Lua fails supports a script-dependent path. A static call-presence test cannot distinguish it. |
| Native model/object/client compatibility | native null read on two different retail binaries | identical instruction is not object identification; selector is not a regional gameplay map | After map/script isolation, remove one demonstrated referenced asset/object in a diagnostic fixture; change in native outcome would support that dependency. No speculative asset removal now. |

The **next single decisive experiment** is one owner-initiated local WGC session:
qualify a known-working 3.0 Lua control and the corrupted standalone fixture in
the same slot/client context, then launch this exact extracted selector at 1x.
Retain client EXE hash/build, WGC/dependency pins, map/W3N hashes and observed
milestones. A live process or `Played` entry is not acceptance. Standalone
failure can also reflect lost campaign game-cache context; standalone success
never proves the W3N works. Subsequent fixture branches above are hypotheses,
not requests for repeated tests or prepared arbitrary repairs.

## Implemented diagnostics and limits

- `stage_launch_smoke.py` uses a reproducible `smoke-r<run>-a<attempt>-g<revision>-t<tree>-h<archive>`
  identity (or `smoke-local-...`). Installed W3N names, checksum file, instructions
  and JSON agree. Post-stage CI rechecks the actual file/hash. Local dirty trees
  and content changes receive distinct identifiers. Known smoke #2/#3 bytes
  cannot be published through `stage` as a new candidate.
- Staging only copies bytes. W3F title, nested map/member set, chapter references
  and gameplay source identity remain unchanged. Menu-title patching is explicitly
  deferred; future instructions require one installed diagnostic at a time.
  Official compilation and release basenames/determinism gates are unchanged.
  `identity-preservation.json` records an independently reread, byte-identical
  local control copy of smoke #3 under a generated filename: 20 outer members
  and all 17 map hashes agree. It is not a new candidate. The ordinary staging
  entry point rejects those known failed bytes (`negative-controls.json`).
- The diagnostic workflow is manual only. This integration does not trigger
  another full campaign build or request a filename-only retest. It does not
  recycle `LAUNCH-425-LIGHTING-1` or claim a new repair.
- Shared `prepare_native_map_diagnostic.py` independently extracts any selected
  actual manifest map, beginning with the selector, checking all 17 map hashes.
  Local output: `build/issue-438/native-diagnostic/`. Its recorded JSON is retained
  here. It includes the exact map, a separate corrupt control, portable adapter
  and instructions, without a WGC/Lua binary bundle.
  The manual diagnostic workflow prepares the same standalone package before
  upload, using the reviewed mpyq pin; it never invokes the native runner.
- WGC 1.1 upstream source/license/dependency review could **not** be completed:
  direct Hive retrieval returned HTTP 403 and web download returned cache miss;
  the published bundle remains pending staff review. No source pin is invented.
  `wgc_local_adapter.py` defaults to `native_runner_unavailable`, runs nothing
  without an explicit local opt-in, and requires complete source/dependency/license
  review plus owner-approved file hashes. No copy was executed or vendored.
- The local runner definition uses `--map`, `--gameexe`, `--gamespeed 1`, a human
  slot 0 and observer slot 1, exact client EXE hash/FileVersion, a 90-second
  Windows Job Object timeout, and cleanup of only newly claimed scratch. It
  refuses an existing Warcraft process/scratch directory. Source review must
  establish the write/process assumptions before use. Reforged absolute
  `-loadfile` behavior on 3.0.x is **unconfirmed** until the positive control
  works. The Windows-specific lifecycle code is not executed by Linux tests.
- The #438 routing exemption removes only `runtime:evidence` as a selection
  prerequisite for this explicitly marked crash investigation. It does not
  remove blockers or change release, runtime evidence, test or merge gates.

No Windows VM, resident test node, self-hosted runner, account dependency,
remote desktop command, installed-game change, credential access or upload is
introduced. The adapter collects only explicitly selected War3Log loader-event
counts and owner-observed milestones; it never uploads raw logs/dumps.

## Reproduction and validation

All commands below run from the repository root. Obtain the pinned mpyq source
in `build/issue-438/upstream/`; it is verified before import. Obtain the reference
archives from the exact War3Net revision above. Do not substitute a rebuilt
campaign for the hash-bound downloaded baseline.

```sh
PYTHONPATH=build/issue-438/upstream python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-425/inspect-independent.py \
  build/issue-438/baseline/Campaigns/AgeOfSailWorldCampaign.w3n \
  --sha256 4f2f9cf8ca56f81aaeca524f257ae15e273c2366e52adfaa1eafdf5b996ff9ad \
  --output build/issue-438/baseline/independent.json
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-438/compare.py \
  --reader build/issue-438/upstream/mpyq.py \
  --campaign build/issue-438/baseline/Campaigns/AgeOfSailWorldCampaign.w3n \
  --reference-campaign build/issue-438/upstream/campaign_3.0.0.w3n \
  --reference-map build/issue-438/upstream/patch_3.0.0_Empty.w3x \
  --output build/issue-438/format-comparison.json
python3 maps/historical-world-rpg/_shared/tooling/prepare_native_map_diagnostic.py \
  --campaign build/issue-438/baseline/Campaigns/AgeOfSailWorldCampaign.w3n \
  --sha256 4f2f9cf8ca56f81aaeca524f257ae15e273c2366e52adfaa1eafdf5b996ff9ad \
  --reader build/issue-438/upstream/mpyq.py --map Maps/AgeOfSailWorld.w3x \
  --build-evidence build/issue-438/baseline/launch-smoke.json \
  --output build/issue-438/native-diagnostic-new
python3 -m unittest discover -s maps/historical-world-rpg/age-of-sail-world/tests -p test_launch_diagnostics.py
python3 -m unittest automation.tests.test_closure
WARCRAFTMAP_WURST_CHECK=skip bash automation/run_checks.sh
```

Final commands/results, separate pinned Wurst validation and evidentiary levels
are in `validation.json`. Passed: 955 scenario Python tests, 137 automation
tests, all 14 final diagnostic tests, 361 Wurst tests, and original/mutated
framework campaigns (two Wurst tests each). The full suite was collected before
the final two diagnostic test additions; the final targeted suite covers them.
The Wurst receipt belongs to the documented validation snapshot before final
diagnostic-only tooling refinements. It is not final-revision release evidence.
The outer worker's authoritative full command remains `bash automation/run_checks.sh`.
Python tests cover rejection of corrupt campaign/map
hashes, wrong provenance, stale staged identity, mixed installed files, unsafe
filenames, unpinned code, absent controls and mismatched client contexts.
Positive/negative fixture tests establish harness behavior, **not a reproducible
native crash repair**. No concrete engine defect was isolated, so no new native
regression or repair claim is made. Native runner qualification, the decisive
standalone experiment, and eventual full retail campaign launch remain open.
