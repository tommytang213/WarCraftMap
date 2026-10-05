# Issue 382: authored recruitment windows in the live runtime

Production generation preserves all 107 authoritative character windows by
stable ID as validated Gregorian ordinal days in `RpgHero` and full dates in
`scenario-runtime.json`. Missing, malformed, reversed, or duplicate definitions
fail generation. Generation provenance is version 16.

`HeroRoster.recruit` checks the campaign state's bound live clock immediately
before first recruitment. Both boundary dates are inclusive. Rejected requests
leave ownership, assignments, progression, inventory, and resources unchanged;
the registered `/recruit` and `/hire` command paths report a bounded English
message. New campaigns select the first eligible generated character, so the
1450 start recruits Hang Tuah while Leonardo remains unavailable until
1470-01-01.

Windows are generated definitions, not saved mutable state. Campaign schema 6
and RPG schema 2 are unchanged. Restoring existing companions never invokes the
first-recruitment check, including when loading supported legacy campaign
envelopes. Ownership, remote assignments, progression, and Oathbound status
survive expiry, save/load, and reconstruction. Empty legacy RPG state still
initializes an eligible starting companion.

The regression tests dispatch production commands around both boundaries,
exercise fractional live ticks and large jumps, restore earlier clock dates,
reject duplicate recruitment, and load already recruited characters before or
after their windows in every supported campaign envelope. Generation tests
compare every authored window against both generated representations and cover
malformed dates, leap days, one-day windows, and invalid stable IDs.

Validation passed:

- **186/186 pinned Wurst tests**, including all 10 recruitment-window tests,
  startup, live clock, load rollback, and save compatibility. The pinned compiler
  digest and complete transcript were checked by the production execution gate:
  [results](issue-382/execution.json), [transcript](issue-382/execution.log.gz).
- **120 Python tests**: 5 generation regressions; 95 character availability,
  progression, clock, timeline, campaign-save, release-save compatibility,
  map/campaign-packaging, and execution-gate tests; and 20 runtime-acceptance tests.
  [Targeted suite](issue-382/targeted-python.log.gz),
  [runtime acceptance](issue-382/runtime-acceptance.log.gz).
- World, global-character projection, and canonical map-source validators.
- Real pinned-toolchain typecheck, map compilation, packaging, and archive
  inspection via `tooling/package_release.sh`:
  [build log](issue-382/pinned-wurst-package.log.gz).
  An independent MPQ read confirmed all 107 windows, generator version 16, and
  the English recruitment rejection message in the compiled Lua.
- All 56 executed project Wurst sources, including regenerated `ScenarioData`,
  and the explicit compiler options match the final worktree. The
  [validation summary](issue-382/validation.json) retains these hashes and the
  packaged map's digest. The generated map remains under ignored `_build/`.

Validation uses the pinned Wurst image with a read-only worktree mount. Sources
are copied into container-private `/tmp` and built as `wurstuser`; no container
changes worktree ownership or permissions. Headless results do not establish
native Warcraft launch or gameplay success. Release status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`.
