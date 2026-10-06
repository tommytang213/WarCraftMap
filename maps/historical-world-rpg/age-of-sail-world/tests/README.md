# Tests

Automated and developer-side verification for the Age of Sail scenario.

Priority areas:

- data integrity
- multi-century simulation
- city capture/rebuild
- safe navigation recovery
- campaign save/load round trips
- save migrations
- technology reachability
- government/title/land transitions
- ownership vs control transitions
- economy invariants
- native Warcraft save/load regression

Player testing is a late release gate, not the routine development loop.

`ManagementCommandTests.wurst` opens roster, inventory/equipment, journal,
technology and market views through production command registration with
recording output, pause, clock and gameplay-timer boundaries. It checks repeat
opens, switches, nested military/map/shared owners, duplicate closes, manual
pause, registration conflicts, passive output and deterministic event delivery
after closing. `CampaignLoadTransactionTests.wurst` and `CampaignStartupTests.wurst`
also dispatch these commands during successful/rejected loads, staged aborts,
repeated reconstruction and startup retry. See [MODAL_MANAGEMENT.md](../docs/MODAL_MANAGEMENT.md).
Recruitment fixtures bind an initialized campaign clock before recruiting;
generated characters use a date within their authored recruitment window.

The delayed combat callback regression uses one initialized siege with production
combat and timer logic, so its interpreter budget goes to deadline behavior.
The other combat journeys retain generated registration and startup coverage.
Generated RPG tests exercise every item comparison and partition hero, quest
and treasure records into deterministic batches after full production
registration. Together the batches cover every generated record through fresh
and repeated restoration, retaining populated equipment, research, quest rewards,
treasure and guidance in each snapshot. Combined full-world scale remains covered
by the repository's separate simulation and save-stress gates.
Snapshot scanning reads each record's fields once, without copying the remaining
document or rescanning field prefixes.
Record-boundary checks preserve empty optional fields and verify atomic rejection
of empty interior records and malformed suffixes. Catalogue cursors accelerate
canonical snapshots while stable-ID fallback still accepts reordered records;
duplicate-index tests cover hash collisions without merging distinct IDs.
The pinned interpreter's 20-second limit and complete-suite execution gate remain
unchanged.

`RpgInteractionTests.wurst` dispatches production interaction, turn-in, tracking
and remote-region commands with recording actor and map boundaries. It checks complete
authority equivalence on rejection, generated local coordinates, eligible reward
recipients, clue prerequisites, repeat collection, commit-time invalidation and
codec reconstruction. `test_rpg_interactions.py` compares those target definitions
with every materialized settlement and compatible treasure cell. See
`docs/RPG_PHYSICAL_INTERACTIONS.md` for the runtime contract.

Execute the complete Wurst suite with the pinned toolchain from the scenario
directory:

```sh
python3 ../_shared/tooling/run_wurst_tests.py package.json
```

`PlayableTradeTests.wurst` exercises store/commodity/origin FIFO provenance,
uncosted cargo, split transfers and sales, integer rounding, transaction rejection
and replay, and the production trade serializer inside campaign envelopes 1–6.
Literal legacy fixtures cover every supported aggregate layout.
`CampaignLoadTransactionTests.wurst` checks rollback with populated lots and
earned merchant standing. The versioned contract and migration limitation are
documented in [LIVE_TRADE_SAVE.md](../docs/LIVE_TRADE_SAVE.md).

The same gate is required by `automation/run_checks.sh`, the Wurst workflow,
map/campaign packaging, and the RC upload verifier. See
`reports/issue-363-execution.md` for the failure classification and retained
execution evidence. Passing interpreter tests does not establish native-client
launch or gameplay success; release status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`.

The Phase 8 integrated release-blocker gate is repository controlled by
`scenario/release-blocker-gate.json`. It classifies campaign-blocking and
unclassified critical failures, runs the headless soak and production
campaign-save round-trip/migration fixtures, audits tracked reports and release
inputs, and verifies that checked-in machine/human reports are current.
Journey routes and system coverage are declared metadata; this command does
not execute physical-map transitions or native Warcraft saves:

```sh
python3 tooling/release_blocker_audit.py
```

Use `--write` only after resolving every reported campaign blocker. The command
cannot close the gate through an allowlist or severity downgrade.

Native Warcraft save/load uses `python3 tooling/run_native_save_regression.py`.
The default run executes the deterministic reconstruction oracle and reports a
clear runtime-unavailable skip. See `docs/WC3_COMPATIBILITY.md` for the pinned
3.0/Lua runner protocol and dedicated CI invocation.

Run the reusable timeline fixture command with, for example:

```sh
python3 tooling/simulate_timeline.py tests/fixtures/timeline/soak.json
```

The command accepts fixed `--seed`, `--start`, `--end`, and `--step` values,
repeatable `--checkpoint-at` values, `--resume`, `--compare-uninterrupted`, and
`--summary-out`. Output and failure diagnostics are canonical JSON.

The early Phase 5 local-battle gate is configured in
`scenario/benchmarks/local-battle.json`. Its maximum-reasonable land, naval,
and mixed profiles independently configure unit, formation, transient effect,
order, reinforcement, and represented-strength counts. The budgets are
provisional pre-content guardrails, not final target-hardware budgets. Run all
profiles headlessly with:

```sh
python3 tooling/run_local_battle_benchmark.py
```

The recording adapter uses deterministic work units as the frame/update-time
proxy. The Warcraft-facing adapter keeps unit/effect creation, order/pathing
calls, and elapsed-time measurement in `WC3Compatibility.wurst`. Benchmark
code is compile-covered but has no initializer and is not activated by the
release bootstrap.

Synthetic large-world validation runs the `small_correctness` profile in every
test pass. The documented maximum-reasonable profile contains 68,608 strategic
entities across every Phase 5 domain and runs in the dedicated stress job:

```sh
python3 tooling/run_large_world_stress.py --profile maximum_reasonable_world \
  --summary-out _build/stress/maximum-reasonable.json
```

Profiles and provisional simulation, persistence, state-size, and active-object
budgets live in `scenario/benchmarks/large-world.json`. Summaries are compact
canonical JSON; failures are capped and identify the invariant and stable ID.

Phase 7 campaign persistence stress uses the real campaign-save and cross-map
transaction managers, all rolling/recovery/manual slot types, supported schema
migrations, repeated map revisits, and normalized authority hashes. Run the
bounded CI profile with `python3 tooling/run_campaign_save_stress.py`; the
dedicated enlarged workload selects `--profile bounded_enlarged`. Finalized
save/load, serialized-size, and growth budgets are in
`scenario/benchmarks/campaign-save-stress.json`.

Final Phase 7 development and minimum-target gates live in
`scenario/benchmarks/final-budgets.json`. The manifest records workload
versions, environments, aggregation/variance policy, calibration samples, and
the retained Phase 6 archive/audio limits. Both bounded and extended CI use it:

```sh
python3 tooling/check_final_performance_budgets.py --profile development
python3 tooling/check_final_performance_budgets.py --profile minimum_target
```

The routine test suite also runs the bounded `smoke` profile from
`scenario/benchmarks/full-world-soak.json` against every configured authored
campaign source. The extended stress workflow runs the four-seed
`complete_multi_century` profile across 1450–1820. Both normal progression and
accelerated jumps execute the same logical schedule, and every run proves an
encoded checkpoint/resume path has the same normalized final state:

```sh
python3 tooling/run_full_world_soak.py --profile complete_multi_century \
  --summary-out _build/stress/full-world-multi-century.json
```

`CampaignStartupTests.wurst` executes the production selector writer, registration
order, regional consumer and campaign codec through recording cache, loader and
projection ports. It covers generated European, Asian and African origins,
including a starting settlement without a military city record; interrupted
commits/acknowledgements; invalid and consumed requests; unrelated older milestones;
and populated/legacy transfers. Authored origin positions share the settlement
materialization calculation. Transfers resolve the saved correspondence against
the generated destination edge and connected pathing, without a military city
object. Fixtures execute every generated
registration, then bound the authority population before exercising the lifecycle to stay within
the pinned interpreter's 20-second limit per test. No authority domain, codec step,
registration phase or lifecycle callback is replaced. Catalogue-wide and scale
checks remain separate repository gates. Packaging regressions also compare every
origin's generated coordinates with its materialized settlement and check that the
campaign chapter selects `wurst-bootstrap/Bootstrap.wurst` using the tested shared
writer.

`CampaignLoadTransactionTests.wurst` uses the production save manager, codec and
populated campaign domains with recording native boundaries. Checksummed candidates
change valid RPG/military records before an invalid religion, diplomacy, trade or
pirate-territory record. Late ordinary-polity, extension and party failures verify
complete authority and projection rollback, retained identity/command context,
no success observers, byte-identical source slots and original subsequent saves.
Reentrant saves are deferred through observer delivery. Successful retry and
repeated reconstruction verify the same projections and resources. Startup tests
also inject projection, session, milestone and acknowledgement failures while
restoring a bound checkpoint, then retry the retained selector handoff.
The equipment rollback regression executes the production Warcraft projector
through recording object identities and life writes, including later equipment
removal and reconciliation after failed loads and successful retries. Rejected loads
and aborted staged loads also restore clock day, cursor, fraction and speed, retain
the original timer, and restart it only on commit; startup failure/retry fixtures
carry a changed clock through the recoverable handoff.

`CampaignTimelineTests.wurst` executes the production clock and campaign codec with
recording listeners/timers: exact real round trips, simultaneous occurrences,
fractional ticks, large jumps, deferred saves, malformed records, inconsistent
cursors, changed generated schedules and timer reconstruction. `CampaignStartupTests`
also advances the generated production clock through all slot types and independently
constructed destination/return clocks, asserting time before party reconstruction
and timer activation. `PlayableCampaignRuntimeTests` migrates and repeatedly resaves
every supported live schema (1–6). These are interpreter lifecycle checks, not native
client launch evidence; release status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`.

`RecruitmentWindowTests.wurst` dispatches the registered recruitment command
against the live campaign clock, including the generated Leonardo record at
1450, both inclusive full-date boundaries, leap days, large jumps, duplicate
requests, restored dates, and already recruited companions in every supported
campaign envelope. Remote-companion reconstruction executes the production RPG
path without creating native units. Startup fixtures retain a generated
1450-eligible hero alongside Leonardo and verify that only the eligible hero
starts recruited. `test_recruitment_generation.py` compares all authored character
windows by stable ID with generated Wurst and JSON, and rejects malformed dates,
reversed windows and invalid identities at generation time.

Recruitment windows are generated definition data, not new save fields. Campaign
schema 6 and RPG schema 2 remain unchanged, and ownership carried by older campaign
envelopes still restores without a date eligibility check. The legacy empty `rpg=v1`
domain initializes an eligible starting companion. Generation provenance advances to version 16.
The shared window predicate gates first recruitment only; existing ownership,
assignments and progression survive the closing date.

Boundary correspondence regressions execute production registration, travel,
codec and destination startup at 0.25, 0.37 and 0.5 on the same generated route.
They cover reversed travel, partial intervals, unequal dimensions, scale/offset,
return journeys, all supported transfer schemas, malformed location tuples,
unavailable arrivals and failed saves. Origin startup also checks incomplete
registration and a configured empty boundary catalogue. `BoundaryArrivalTests.wurst` tests
movement-specific connectivity and bounded native-pathing rejection through a
recording port. Numerical coordinate comparisons allow 0.01 world units for
Warcraft float rounding, separate from the declared navigation snap tolerance.
`test_boundary_arrival.py` checks generated arrivals against materialized MPQ
terrain/pathing on every physical map and rejects tampered packaged pathing.
