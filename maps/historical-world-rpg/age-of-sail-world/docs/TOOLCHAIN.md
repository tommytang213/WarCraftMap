# Toolchain

## Target

- Warcraft III: latest supported Reforged 3.0.x client family.
- WurstScript as the source language/toolchain.
- Lua as the generated Warcraft scripting backend.
- Wurst project patch target: `v3.0`.
- Current bootstrap/source-controlled folder-map input at `map/AgeOfSailWorld.w3x/`; the final world target is a multi-map single-player custom-campaign package so each regional/subregional physical map receives its own terrain budget.

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

The `Age of Sail map artifact` workflow runs the repository-controlled
`./tooling/package_release.sh` command with an immutable Wurst container image,
after source and world validation. Successful workflow runs currently retain the packaged
`AgeOfSailWorld.w3x` for 14 days as the `age-of-sail-world-map` artifact. This is a
bootstrap/runtime-validation artifact, not the intended final whole-world release
format. The final release pipeline must package multiple physical regional/subregional
maps into a single-player custom-campaign experience and validate cross-map state
transfer and transitions. Maintainers can download CI artifacts from the **Artifacts**
section of the run's GitHub Actions summary. CI output is never committed as a release.

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

Failures name their stage (`inputs`, `scenario validation`, `generation`,
`provenance`, `Wurst compilation`, `map assembly`, or `archive inspection`).

The command publishes `_build/release/AgeOfSailWorld.w3x`. Inspect it with
Wurst tooling or an MPQ-capable archive viewer: it must contain `war3map.lua`
and the `runtime/` provenance payload. The command performs those structural
and bootstrap-marker checks before publishing the release path.

Authoritative inputs, generated runtime data, compiler settings, build order,
and the release filename are deterministic. Wurst/StormLib controls MPQ block
ordering, compression, and archive metadata that the repository tooling cannot
normalize, so byte-for-byte `.w3x` identity is not promised across different
Grill, JVM, or StormLib versions. Use the pinned CI container when archive-byte
comparison matters.
