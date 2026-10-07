# Historical World RPG

Category for very long single-player historical sandbox/RPG maps.

## Structure

- `_shared/` — reusable engine and tooling shared by historical scenarios.
- `age-of-sail-world/` — first scenario/map project.
- `conformance-campaign/` — tiny content-only consumer proving the framework boundary.
- Future maps belong beside `age-of-sail-world/`, for example `roman-world/` or `three-kingdoms-world/`.

The architecture intentionally separates reusable simulation systems from timeline/location content so another historical setting can replace data and terrain without rebuilding the core systems.

See [_shared/README.md](_shared/README.md) for the mechanically checked layer
contract and the common campaign execution and packaging tests.
