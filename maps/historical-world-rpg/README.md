# Historical World RPG

Category for very long single-player historical sandbox/RPG maps.

## Structure

- `_shared/` — reusable engine and tooling shared by historical scenarios.
- `age-of-sail-world/` — first scenario/map project.
- Future maps belong beside `age-of-sail-world/`, for example `roman-world/` or `three-kingdoms-world/`.

The architecture intentionally separates reusable simulation systems from timeline/location content so another historical setting can replace data and terrain without rebuilding the core systems.
