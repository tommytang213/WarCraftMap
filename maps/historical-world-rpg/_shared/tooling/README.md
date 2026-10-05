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
# Physical boundary arrivals

`boundary_arrival.py` derives movement-specific, four-neighbour connectivity
from the same composed surface cells used to materialize WPM. Playable bounds
use each physical source map's W3I complementary camera margins and generated
W3E dimensions. Source triggers and destination interpolation share these bounds.
Each directed boundary resolves its destination edge and interval from its unique
reverse record; missing or ambiguous records fail configuration validation.
Registration requires completed boundary configuration, including an explicitly
empty catalogue for a supported single-map campaign.

The reusable `_shared/wurst/BoundaryArrival.wurst` resolver consumes the saved
destination-segment coordinate. Only the source travel coordinator applies
reverse, scale and offset, once; out-of-range results fail before saving. Existing
`boundary`/`position` fields remain the save authority, so no persisted fields or
campaign schema change are needed. Supported schemas 1–6 retain their migrations.

Arrival tolerance is **512 Warcraft world units** from the corresponding edge
point. Generated candidate rows are 192, 320 and 448 units inward, with 32 units
of terrain clearance. The nearest edge component must support the movement
class; candidate rows must belong to that component. Within a row, the exact
correspondence is tried first, followed by 32-unit pathing probes. Candidates
outside the tolerance or within any 128-unit edge trigger strip are forbidden.
Blocked, decorative and disconnected cells cannot provide a fallback arrival.
The destination rechecks native pathing before projecting the party.

The current campaign party projection recreates land heroes and therefore
requires land arrivals. It refuses sea-only arrivals; it cannot infer an embarked
party or teleport heroes to a port. The shared resolver also supports naval,
amphibious and flying navigation classes. Origin startup still uses its authored
starting location. The map's generic player-slot marker is not travel authority.

Campaign packaging recomputes these navigation records from the packaged WPM
and checks their edge metadata. A pathing change invalidates the generated
connectivity proof. Destination failure leaves the transfer checkpoint available
for retry, with startup and autosaves locked until reconstruction succeeds.
