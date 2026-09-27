# Toolchain

## Target

- Warcraft III: latest supported Reforged 3.0.x client family.
- WurstScript as the source language/toolchain.
- Lua as the generated Warcraft scripting backend.
- Wurst project patch target: `v3.0`.
- Source-controlled folder-map input at `map/AgeOfSailWorld.w3x/`.

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

Build the validated canonical input into the release-named archive:

```text
./tooling/package_release.sh
```

This repository-controlled command validates `map/map-source.json` and every required folder-map component, checks that the project remains pinned to the Lua backend and `wc3Patch: v3.0`, then runs `grill install`, `grill typecheck`, and `grill build map/AgeOfSailWorld.w3x`. It fails with a specific message if Grill, an authoritative input, the archive, the generated `war3map.lua`, or the expected bootstrap payload is absent. The inspected release is written to `_build/release/AgeOfSailWorld.w3x`.

The reusable command implementation lives in `_shared/tooling/package_wurst_map.py`; `package.json` supplies this scenario's paths, release name, and bootstrap markers. The authoritative inputs are the folder map, `wurst/`, `scenario/`, `wurst.build`, and generated object data inside the folder map. `_build/`, Grill caches, and packed `.w3x` files are disposable and ignored by Git.

Wurst/StormLib controls MPQ block ordering, compression, and archive metadata. Those details are not all exposed for normalization, so byte-for-byte archive identity is not promised across Grill, JVM, or StormLib versions. The repository makes source paths, compiler target, backend, build sequence, and final filename deterministic; use the same pinned toolchain image when byte comparison matters.

No World Editor is needed. To inspect a release, use an MPQ-capable archive viewer or Wurst tooling, confirm `war3map.lua` exists, and search it for the bootstrap log text. The packaging command performs those payload checks against the generated script before publishing the release path. No player gameplay check is required.

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

CI validates the folder structure and runs the same release-packaging entry point, but does not retain `_build/` as source.
