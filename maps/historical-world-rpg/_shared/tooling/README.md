# Shared Tooling

Reserved for build, validation, content-generation and simulation tools.

The development target is a reproducible source-to-map pipeline with minimal routine dependence on manual World Editor work.

Shared tooling includes `package_wurst_map.py`, the scenario-configured,
deterministic map build orchestrator and runtime-data generator. Map projects
supply paths and release metadata through their `package.json`; no Age of Sail
IDs or paths are embedded in the shared generator.

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
