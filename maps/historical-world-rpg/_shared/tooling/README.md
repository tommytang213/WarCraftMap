# Shared Tooling

Reserved for build, validation, content-generation and simulation tools.

The development target is a reproducible source-to-map pipeline with minimal routine dependence on manual World Editor work.

Planned tooling:

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
