# Issue #425: Begin the Campaign investigation

The implementation restores the missing `SetDayNightModels(terrain, unit)`
initialization before `InitBlizzard()` in the authoritative source maps.
**The native crash cause remains provisional.** The null-base read at executable
offset `0x8E3F42` has not been mapped to an engine function or object, and no
Warcraft III execution occurred in this environment. The revised diagnostic
still requires launch validation on **3.0.1 build 24342**.

The changes are based on `a2e24e86dd8f2284e8d33786c11d125c7fe513f4` and preserve
the recovery, god-mode, settlement, save-schema and pinned-toolchain changes in
that tree. Both consumers use Lordaeron terrain; the stock model paths come from
the independent editor fixture. No map metadata version, terrain, object
definition, campaign authority or gameplay initialization order was changed.

## Evidence and limits

`investigation.json` records the sanitized observations. The exact Actions
artifact was downloaded with existing authenticated GitHub access. Its W3N hash
is `d6651b77a48a3c7c1b4916a204676b506a380f77a4496fbadd417697e8d87abc`, matching
the installed reproduction. All 17 nested maps match their manifest hashes.
The private crash ZIP, text logs and dump were not available on the VM and were
not accessed or uploaded. The exception facts are explicitly attributed to the
sanitized issue findings, including the original exception context.

The unmodified [mpyq reader](https://github.com/eagleflo/mpyq/blob/6bfba18ec403f702666b4109db3d95f3b97b1dc5/mpyq.py)
independently agrees on the 20 campaign members and 814 nested members, including
the first chapter's Lua, metadata, terrain and placements. It cannot decrypt
Grill's nested `(listfile)` members; those 17 files are explicitly excluded from
the independent result. `inspect-independent.py` reproduces this comparison and
checks the supplied campaign and reader hashes. Detailed receipts are compressed
beside this report.

The first chapter has W3I v31, one playable human slot, Lua script mode and valid
placement/terrain structure under the existing contracts. The independently
published [War3Net 3.0 empty-map fixture](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/tests/War3Net.TestTools.UnitTesting/TestData/Maps/patch_3.0.0_Empty.w3x)
uses W3I v39 and producer version 3.0.0.24268. Neither that difference nor a parser
pass proves compatibility or incompatibility with client 3.0.1 build 24342.

The editor fixture's `main` initializes terrain/unit lighting before Blizzard
initialization. War3Net's independent [main generator](https://github.com/Drake53/War3Net/blob/18e88f0e1f67e6b16870dcbcd827740275fe2173/src/War3Net.Build/MapScriptBuilder/Common/Main.cs)
also emits this separate call. The failing first-chapter Lua has `InitBlizzard()`
but **no** lighting initialization anywhere. The pinned `blizzard.j` has no
`SetDayNightModels` reference, so calling `InitBlizzard()` does not replace the
missing call. Other editor-prelude differences are recorded, not speculatively
copied into the campaign.

The regression locks the exact failing Lua by SHA-256. A controlled single-call
insertion makes its startup contract pass; comments, strings, conditional or
shadowed calls, empty paths and incorrect ordering still fail. This establishes
a specific source/compiled initialization defect, **not a native crash fix**.
The compiled-archive gate applies the stronger contract to all maps. Existing
structural and release gates remain intact.

## Revised diagnostic

`LAUNCH-425-LIGHTING-1` uses the existing isolated launch-smoke build. Its staging
step reopens every embedded map, verifies the compiled startup and physical-map
contracts, requires exact source identity and passing Wurst execution evidence,
and writes `launch-smoke.json`, the full source revision, source-tree hash and
campaign SHA-256. The source-tree hash distinguishes this uncommitted worktree
from its base revision. The outer worker must rebuild after committing under the
new revision; these bytes must not be relabeled as that future commit.

The local artifact location, exact digest and automated results are recorded in
`validation.json`. Generated W3N/W3X outputs remain ignored build products. No
commit, push, PR/issue change, workflow dispatch, public upload or player testing
was performed during this implementation.

Local W3N, relative to the repository root:
`build/issue-425/diagnostic/Campaigns/AgeOfSailWorldCampaign.w3n`.
SHA-256: `e9039d3b81e00425524dfb3095a844262d27e9a0e0e4ff76a7106d8341cbad7e`.
Source-tree SHA-256:
`b25155f9fa96cd357c58566ee8f0d417fe129a39ca1ee08d38d3f4efd0bd695a`.

Validation passed: 930 scenario Python tests, 129 automation tests, 335 pinned
Wurst tests, all 17 campaign maps, and original/content-mutated three-map
framework campaigns (two Wurst tests each; 158 shared source hashes unchanged).
`check-staging-rejections.py` also proves that stale revision evidence and a
missing archived lighting call reject before staging, even when the damaged
map's manifest checksum has been recalculated. The initial negative-control
matcher was corrected to match the gate's existing generic evidence error.

`validate-container.sh` records the local offline build recipe. It ran as the
image's unprivileged `wurstuser` with source and existing dependencies mounted
read-only, networking disabled, and compilation confined to container-private
`/tmp`. The pinned compiler and cached standard-library revision were verified;
the container was removed after its evidence was collected. Repository checks
used `WARCRAFTMAP_WURST_CHECK=skip` only because the full Wurst/campaign/framework
validation ran separately. No actual Wurst tests were skipped.

To reproduce after the ordinary pinned campaign build:

```sh
python3 tooling/stage_launch_smoke.py --source-revision FULL_REVISION --output _build/launch-smoke
```

For independent decoding, fetch the pinned `mpyq.py` into a disposable developer
directory and run:

```sh
PYTHONPATH=READER_DIRECTORY python3 reports/issue-425/inspect-independent.py \
  CAMPAIGN.w3n --sha256 EXACT_CAMPAIGN_SHA256 --output inspection.json
```

## Outstanding native acceptance

The precise next discriminator is whether origin selection opens when these
materially revised bytes are launched on **3.0.1 build 24342**. If the crash
persists, compare the new module-relative exception address and original context
before changing another startup input. A matching crash after lighting setup
would leave this omission insufficient to explain the failure; symbolic native
resolution or controlled native execution would then be needed to localize it.
The existing screenshot GUID is not asserted to identify the uploaded 22:05:02
session.

This focused comparison is authorized independently of unrelated integration
and exhaustive release-traceability closure. It does not publish a release
candidate or ask for incremental player QA. **Original real-client status:
failed. Revised real-client status: not revalidated. Release remains blocked.**
