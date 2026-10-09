# Toolchain

## Target

- Warcraft III: latest supported Reforged 3.0.x client family.
- WurstScript as the source language/toolchain.
- Lua as the generated Warcraft scripting backend.
- Wurst project patch target: `v3.0`.
- Current bootstrap/source-controlled folder-map input at `map/AgeOfSailWorld.w3x/`; the final world target is a multi-map single-player custom-campaign package so each regional/subregional physical map receives its own terrain budget.
- The authored folder map uses the legacy W3I v33 layout with embedded game
  version `3.0.0.24268`; the pinned compiler emits v31. Neither is an extracted
  current-client format fixture. The independently sourced War3Net 3.0.0 map
  uses v39, including HUD, extended fog, water and player-HUD fields. The shared
  parser covers all three layouts; a version label does not prove playability.

## Why Wurst + Lua

WurstScript added explicit Warcraft III 3.0 support in September 2026. Its current tooling supports typed source, source-generated Warcraft object data, map folders, MPQ inspection, tests, and Jass/Lua output.

Lua is selected for this project because the target is modern Reforged rather than legacy Classic clients.

References:

- https://wurstlang.org/news/warcraft-3-reforged-3-support.html
- https://wurstlang.org/features/backends.html
- https://wurstlang.org/features/map-formats.html
- https://wurstlang.org/news/production-object-editor-safe-calls-and-tooling.html

## Core commands

From this map project directory:

```text
grill install wurstscript
grill install
grill typecheck
grill test
```

Validate the canonical input, typecheck the bootstrap/runtime, and prove that Wurst can inspect and build the folder map:

```text
./tooling/validate_map_source.sh
```

The script runs the repository-side binary/metadata validator, `grill typecheck`, and `grill build map/AgeOfSailWorld.w3x`. The build uses the Lua backend and `wc3Patch: v3.0` from `wurst.build`, injecting `wurst/Bootstrap.wurst` into generated output. Build output is generated under `_build/`; generated output is not the editable source of truth. No World Editor or player gameplay check is required.

For a fast map-input check that does not require Wurst or Warcraft III:

```text
python3 tooling/validate_map_source.py
python3 -m unittest tests/test_map_source.py
```

## Version policy

`wc3Patch: v3.0` is pinned in `wurst.build` so typechecking does not silently follow a different Warcraft native surface.

Before intentionally moving to a future Warcraft patch family:

1. update the Wurst toolchain;
2. run `grill patch`;
3. review the reported difference;
4. use `grill patch align` only as an intentional migration;
5. typecheck/tests;
6. native WC3 save/load regression;
7. campaign-save migration/regression.

Patch changes are treated as compatibility work, not casual dependency updates.

## CI

GitHub CI uses the immutable Wurst image declared in each build workflow.
`automation/prepare_wurst_image.sh` first reuses an available local digest,
then tries Google's public Docker Hub mirror and the canonical Docker Hub
repository. Both requests use the same SHA-256 manifest pin. The selected
registry reference is passed to `docker run --pull=never`; `WURST_IMAGE` in
build provenance retains the canonical compiler identity. No mutable tag,
registry credentials, or Docker daemon reconfiguration is required. If neither
registry supplies the pinned image, validation fails before compilation.

This handles the Docker Hub rate-limit failure observed in PR #442 without
changing compilers or skipping any checks. The mirror is a cache and can miss;
its availability is not a validation or native-launch result. See the
[issue #438 evidence](../reports/issue-438/README.md) for the verified manifest
and the separate native launch blocker.

CI validates the folder structure and performs a full Wurst build from the canonical source path, but does not retain `_build/` as source.

The shared Wurst execution gate prints the retained interpreter transcript on
failure, including failed test names and timeout or assertion diagnostics. This
keeps failures reviewable when CI removes its private build container. Successful
runs report the passing count and evidence path without replaying the transcript.

The `Age of Sail campaign artifact` workflow runs the repository-controlled
`./tooling/package_release_candidate.sh` command with an immutable Wurst container
image, after source and world validation. It performs two clean campaign builds
and the release gates described below. Before upload,
`verify_ci_release_artifact.py` reopens the copied ZIP, checks the nested campaign
and maps, requires both embedded source revisions to match `GITHUB_SHA`, and records
that ZIP's SHA-256 and size in `artifact-evidence.json`.

Successful runs retain `AgeOfSailWorld-phase9-rc1.zip` and its evidence for 14 days
as the `age-of-sail-world-release-candidate` artifact. The ZIP contains the
`AgeOfSailWorldCampaign.w3n` campaign, every map configured by `physical-maps.json`,
English documentation, and build provenance. Maintainers can download it from
the **Artifacts** section of the GitHub Actions run. Standalone W3X/W3N packaging
is diagnostic build evidence; passing automated RC checks does not establish
client playability. Status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke` until the target-client smoke
is confirmed. CI output is never committed as source.

`wurst_run.args` pins the production compiler options and is copied into every
isolated build with its hash in provenance. Inlining and local optimization stay
enabled; identifier compression is disabled because the pinned compiler emitted
different generated names across clean builds. Determinism checks still compare
the exact decoded Lua and gameplay bytes. Only understood MPQ container metadata
is excluded from that comparison; uploaded files retain their exact byte hashes.
Source references and compiled call/registration matches are explicitly static
evidence. The RC gate separately executes the headless soak and campaign-save
fixtures. Declared journey itineraries are metadata, not evidence of executing
physical-map transitions or native Warcraft saves. None of these checks
establishes successful real-client execution.

Compiled origin-selection checks require the emitted `origin` command
registration, generated origin configuration and physical-map loading calls.
The pinned optimizer may inline `registerOriginSelection`; its diagnostic stack
annotation alone supplies no call or registration evidence. Regression checks
reject missing registrations or operations even when that annotation remains.

The map's source `main` must call `InitBlizzard()` before Wurst package
initializers. Wurst retains the source main body; it does not supply the missing
Blizzard initialization for an empty stub. Packaging reads the final MPQ's Lua
and rejects missing, misplaced or conditional initialization. These checks are
static. Complete placement records and the terrain-sized shadow raster are
also inspected, including in the selector. Fixtures extracted from artifact
#704 retain the missing initialization and invalid regional item-table reference.

## Runtime map pipeline

The scenario-configured `package.json` drives five explicit stages: contract
validation, deterministic Wurst/runtime-data generation, Wurst compilation,
folder-map assembly, and final archive inspection. Generated files carry SHA-256
provenance for every authoritative input and are checked immediately before
assembly, so stale or edited output cannot be packaged. The build works from an
isolated copy under `_build/`; the canonical folder map, Wurst sources, and
scenario JSON are never modified.

Run a clean build from this map project directory with:

```text
./tooling/package_release.sh
```

Every invocation removes the previous `_build/` tree. To clean without building:

```text
./tooling/package_release.sh clean
```

Those commands preserve the useful bootstrap-only developer workflow. The clean
command for the complete campaign is:

```text
./tooling/package_campaign.sh
```

It validates `physical-maps.json`, generates only each map's assigned runtime
entities and terrain payloads, compiles and inspects every map, then writes
`_build/release/AgeOfSailWorldCampaign.w3n`. Use
`./tooling/package_campaign.sh clean` to remove all intermediates and releases.
Physical-map IDs, source paths, region/instance/terrain assignments, package paths,
budgets, display name, description, chapter titles, and bootstrap selection are
scenario configuration; the
shared build code is scenario-neutral.

For the Phase 9 player candidate, run `./tooling/package_release_candidate.sh`.
It performs two clean campaign builds, compares normalized contents, enforces the
completed content/save/recovery/blocker gates, audits the payload, and writes
`_build/release/AgeOfSailWorld-phase9-rc1.zip`. The ZIP includes the campaign,
English player documentation, a checksummed artifact manifest, and reproducible
build provenance. `./tooling/package_release_candidate.sh clean` removes that ZIP.

Acceptance has four separate levels: source/static readiness, executed headless
production integration, built-artifact verification, and real-client status.
`runtime_acceptance.py --write` and `release_blocker_audit.py --write` without
execution/artifact inputs write honest blocked snapshots and return exit code 1.
This is the expected source-only state, not a request for incremental player QA.

The pinned interpreter runner inserts configured entry probes only into its
temporary Wurst assembly, records hits inside passing tests, and restores the
original sources before building. `scenario/runtime-execution.json` specifies
the production registration/adapter entries each required system must exercise
within one passing test. Uncovered entries remain blockers. Merely declaring a
probe or finding its function/test name does not supply execution evidence.

To evaluate a built campaign, supply `--execution-dir _build/wurst-tests`,
`--campaign _build/release/AgeOfSailWorldCampaign.w3n` and a full
`--source-revision` to either acceptance tool. Evidence binds the revision and
source-content digest, including dirty source changes. Each built map embeds
that identity; inspection records the exact campaign and nested-map hashes.
The RC packager and copied-ZIP upload verifier recompute acceptance from these
inputs. They block publication on incomplete/failing integration or artifact
evidence, regardless of saved PASS flags. The final ZIP includes the execution
transcript and both acceptance reports. Automated candidate readiness never
claims that Warcraft III or the declared campaign itineraries were executed;
real-client launch/save/travel validation remains explicitly separate.

Failures name their stage (`inputs`, `scenario validation`, `generation`,
`provenance`, `Wurst compilation`, `map assembly`, or `archive inspection`).

The command publishes `_build/release/AgeOfSailWorld.w3x`. Inspect it with
Wurst tooling or an MPQ-capable archive viewer: it must contain `war3map.lua`
and the `runtime/` provenance payload. The command performs those structural
and bootstrap-marker checks before publishing the release path.

Authoritative inputs, generated runtime data, compiler settings, build order,
and the release filename are deterministic. Wurst/StormLib controls MPQ block
ordering, compression, and archive metadata. The RC verifier compares decoded
members while excluding only understood container metadata; byte-for-byte `.w3x`
identity is not promised across different Grill, JVM, or StormLib versions.
Use the pinned CI container when comparing builds.
