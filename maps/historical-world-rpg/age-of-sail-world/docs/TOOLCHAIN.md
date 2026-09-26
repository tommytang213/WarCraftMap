# Toolchain

## Target

- Warcraft III: latest supported Reforged 3.0.x client family.
- WurstScript as the source language/toolchain.
- Lua as the generated Warcraft scripting backend.
- Wurst project patch target: `v3.0`.
- Source-controlled map-folder workflow once the base terrain/map folder is created.

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

Once a valid source map/map-folder exists:

```text
grill build <source-map.w3x>
```

Build output is generated under `_build/`; generated output is not the editable source of truth.

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

A full map-build job will be added after the source map folder is committed.
