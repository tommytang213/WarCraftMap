# Toolchain

## Target

- Warcraft III: latest supported Reforged 3.0.x client family.
- WurstScript as the source language/toolchain.
- Lua as the generated Warcraft scripting backend.
- Wurst project patch target: `v3.0`.
- Current bootstrap/source-controlled folder-map input at `map/AgeOfSailWorld.w3x/`; the final world target is a multi-map single-player custom-campaign package so each regional/subregional physical map receives its own terrain budget.
- Browser-parsed map metadata is locked to W3I v33 with embedded game version
  `3.0.0.24268`; source and packaged maps are parsed by
  `tooling/forsaken_kingdom_map.py`, not accepted from the patch label alone.

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

GitHub CI performs Wurst typechecking using the official/community Wurst Docker workflow. It refreshes Wurst before checking so the CI toolchain understands the currently pinned `v3.0` target.

CI validates the folder structure and performs a full Wurst build from the canonical source path, but does not retain `_build/` as source.

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
