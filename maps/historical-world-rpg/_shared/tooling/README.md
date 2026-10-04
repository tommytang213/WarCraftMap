# Shared Tooling

Reserved for build, validation, content-generation and simulation tools.

The development target is a reproducible source-to-map pipeline with minimal routine dependence on manual World Editor work.

Shared tooling includes `package_wurst_map.py`, the scenario-configured,
deterministic map build orchestrator and runtime-data generator. Map projects
supply paths and release metadata through their `package.json`; no Age of Sail
IDs or paths are embedded in the shared generator.

`run_wurst_tests.py CONFIG` generates and assembles a complete scenario and runs
`grill test` through `wurst_execution.py`. Run it with the pinned compiler from
the Wurst workflow; `SOURCE_REVISION` (or `--source-revision`) supplies the full
revision when the private container copy has no Git metadata. The gate checks
the compiler JAR digest, discovers source tests independently, requires one
passing result for every test plus matching summary/completion, and retains the
raw transcript and input hashes in `_build/wurst-tests/`. Missing tools,
assertions, interpreter errors, empty discovery and incomplete output fail.
Map and campaign packaging call the same gate before producing artifacts;
campaign tests use full generated data before physical-map localization.

`generate_regional_terrain.py` deterministically rasterizes scenario-owned regional geography. Registered terrain sources are hashed into build provenance, stale outputs are rejected, and normalized terrain inputs are packaged under `runtime/`.

Planned and implemented tooling:

- map build/pack pipeline
- schema/data validation
- technology graph validation
- quest/event reference validation
- world integrity validation
- long-run economy/timeline simulation
- save round-trip and migration tests
- generated developer/debug commands
- release packaging

`validate_world.py` also validates generic title rank/grant hierarchies, holder allegiances, territorial references, vassal cycles, and independent-versus-overlord taxation rules through `validate_government.py`.

`validate_assets.py` validates any scenario-neutral asset catalogue and a
scenario-owned historical-fit matrix. It resolves candidate locators and emits
stable coverage, unresolved-replacement, and resolved object/import manifests;
it contains no Age of Sail IDs.
