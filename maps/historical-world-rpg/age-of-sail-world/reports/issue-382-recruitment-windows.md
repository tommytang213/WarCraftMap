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

Validation of the original implementation passed:

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
  and the explicit compiler options matched that implementation snapshot. The
  [validation summary](issue-382/validation.json) retains these hashes and the
  packaged map's digest. The generated map remains under ignored `_build/`.

PR #387 CI was inspected after merge commit
`33e990d4e2cf9f2a42ced48b1ae9ec4240aa9715`. All four failed checks were cancelled
before executing any steps. Each has the same GitHub annotation:
"The job was not acquired by Runner of type hosted even after multiple attempts."
The runs are [37370020857](https://github.com/tommytang213/WarCraftMap/actions/runs/37370020857),
[37370026019](https://github.com/tommytang213/WarCraftMap/actions/runs/37370026019),
[37370020582](https://github.com/tommytang213/WarCraftMap/actions/runs/37370020582),
and [37370141123](https://github.com/tommytang213/WarCraftMap/actions/runs/37370141123).
`gh pr checks 387`, run/job metadata, and check annotations establish a hosted
runner acquisition failure, not a compiler or test failure. No implementation or
workflow change is warranted by that diagnosis.

Fresh validation of the merged worktree passed:

- **194/194 pinned Wurst tests**, including all 10 recruitment-window tests and
  the merged physical-interaction regressions:
  [results](issue-382/ci-revalidation-execution.json.gz),
  [transcript](issue-382/ci-revalidation-execution.log.gz).
- **124 Python tests** covering generation, character availability/progression,
  clock/timeline, campaign saves and legacy compatibility, map/campaign packaging,
  the execution gate, runtime acceptance, and physical interactions:
  [transcript](issue-382/ci-revalidation-python.log.gz).
- World, global-character projection, and canonical map-source validators.
- Pinned typecheck, execution, real map compilation and packaging:
  [build log](issue-382/ci-revalidation-package.log.gz).
  Independent MPQ inspection again matched all 107 authored windows and checked
  the compiled recruitment predicate and English temporal rejection message.
- All 58 project/shared Wurst sources, including regenerated `ScenarioData`,
  plus the compiler options match the executed inputs. The
  [revalidation summary](issue-382/ci-revalidation.json) records those hashes,
  the map digest, compiler identity, test modules, and CI diagnosis.

The temporary validation container was removed after copying its results into
the worktree. The generated map remains in ignored
`_build/issue-382-revalidation/` at the repository root.

Validation uses the pinned Wurst image with a read-only worktree mount. Sources
are copied into container-private `/tmp` and built as `wurstuser`; no container
changes worktree ownership or permissions. Headless results do not establish
native Warcraft launch or gameplay success. Release status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`.
