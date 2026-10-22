# Destination script isolation

This is a developer-owned control for the unresolved origin-to-region transition.
It is **not a production fix or release candidate**. No native success follows
from preparing it or from passing its automated tests. No player retest is
requested by this tooling.

The builder is bound to the failed campaign SHA-256
`b2f9dfa2ab04d54d97f465aeb11c80a5f4f7852b850d58a82a4cf7d8d2665ba8`
and baseline source revision
`54911cabe2a993b22f3a5d05b549df5dc3995c9c`. It refuses other input bytes and refuses
to emit a known failed hash as a new diagnostic.

## What changes

Only `EuropeCentralEast.w3x/war3map.lua` changes in decoded campaign content.
The original Lua occupies an unencrypted, multi-sector zlib MPQ block. The
replacement uses the same sector format and flags in that block's existing
slot. Only its compressed prefix and its packed/decoded length fields change.
The inner block table is re-encrypted; this changes ciphertext beyond the edited
row, but every other decoded row is verified unchanged.

The old script slot's unused tail remains byte-for-byte unchanged as inert
padding. Nested and outer archive lengths, both headers and hash tables, the
outer block table, every other packed member and every other decoded payload
remain unchanged. Complete listfile/hash-table coverage and live-block coverage
are mandatory. Unknown members are preserved; incomplete enumeration, signatures,
attributes, or unsupported packing cause refusal.

The selector, its cache commit, `ChangeLevel(path, true)`, all campaign paths,
W3F visibility, W3I identity, terrain, and other maps remain unchanged. The
external W3N filename also stays identical to the input basename. Supply the
baseline under the **exact filename previously installed for the failed run**;
use a separate output directory to distinguish the control.

## Script behavior

`destination_entry.lua` is a builder template. The builder inserts the exact
original `config()` declaration and camera bounds from archived W3I. It checks
that configuration depends only on Warcraft natives/constants, local variables,
and the explicitly documented no-op `__wurst_init_bootstrap()` adapter. Regional
Wurst initialization is intentionally absent. Original day/night lighting and
`InitBlizzard()` are retained.

The builder checks Austria's archived origin and Vienna settlement records agree
on `(576, 64)`, that the point lies inside the original camera bounds, and that
nine surrounding pathing pixels permit walking. The script reveals terrain,
focuses the camera and creates a selected, controllable stock Footman there.
It reports a null unit instead of dereferencing it and keeps a heartbeat running.

The visible marker is **`AOS-DESTINATION-ISOLATION-54911ca-v1`**. Entry status is
followed by a heartbeat every two seconds. A heartbeat alone establishes callback
activity. The native milestone requires visible terrain and a unit responding to
a movement order; Victory/Continue or a log entry alone is insufficient.

The destination never opens, consumes, acknowledges, or saves the campaign cache.
The unchanged selector still performs its existing pending-origin commit. This
control provides no campaign gameplay or save/load acceptance.

## Baseline provenance is intentionally stale for the transformed map

To keep every non-script member unchanged, the embedded `campaign-manifest.json`
and `runtime/build-identity.json` retain their baseline contents. In particular,
**the embedded destination checksum is intentionally stale and this transformed
campaign cannot pass release manifest verification**. It must not be submitted
to production/release staging. The separate `destination-isolation.json` records
the baseline identity, transformation source hashes, exact changed-member hashes,
block metadata and allowed byte-change regions. It explicitly says
`releaseCandidate: false` and `nativeStatus: native_not_run`.

## Commands

Run from `maps/historical-world-rpg/age-of-sail-world` after developer review:

```sh
python3 tooling/prepare_destination_isolation.py \
  --campaign /absolute/path/to/the-original-installed-name.w3n \
  --output /absolute/path/to/a-new-diagnostic-directory
```

This constructs the local control and receipt only. It does not launch Warcraft,
upload anything, install a campaign, or publish an archive. Keep the original
baseline untouched. Building all maps or rerunning the complete Wurst suite is
unnecessary for this diagnostic transformation.

Focused verification:

```sh
python3 -m unittest discover -s tests -p 'test_destination_isolation.py' -v
```

The tests exercise compressed-MPQ preservation, fail-closed enumeration and input
guards, configuration dependency checks, and the minimal Lua unit/heartbeat and
null-unit paths. Lua execution uses explicit native doubles with an optional
local stock Lua 5.3/5.4 library; it is not Warcraft execution.
