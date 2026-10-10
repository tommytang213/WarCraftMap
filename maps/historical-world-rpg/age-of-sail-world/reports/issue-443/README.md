# Issue 443: Live army and fleet order persistence

Production regional startup now installs immediate, point and target order
callbacks through the shared compatibility boundary. Stable force and target
identities own committed orders. Current ownership, force category, physical map,
movement topology and military target rules gate mutation. Saves and retirement
capture local positions and completion/cancellation; reconstruction binds every
representation before replay. Callback generations and an issuance guard protect
reconstruction, repeated installation and failed-load rollback.

The military payload is v6. V1–v5 migrate, including both historical v4 settlement
layouts, existing recovery hints and legacy march/sail destinations. Target and
issuing-controller identities are new stable fields. Campaign envelopes 1–8 and
other domain schemas retain their contracts. See
[LIVE_MILITARY_ORDERS.md](../../docs/LIVE_MILITARY_ORDERS.md) for supported commands,
migration and native-boundary behavior.

`MilitaryOrderEventsTests.wurst` initializes a campaign with generated navigation
and ordinary Warcraft military projections. Its installed production callbacks
exercise land/naval movement, immediate and target orders, completion, cancellation,
missing targets, defenders, ownership changes, malformed arguments, stale/reentrant
callbacks, repeated reconstruction, saved allegiance and late failed-load rollback. Production
execution probes now observe these callbacks and their installer.

The final pinned interpreter run passes **373/373 tests**, including all seven
new order journeys. The targeted military, navigation, recovery, persistence and
framework Python suites pass **76/76**; a final persistence/compatibility rerun
passes **25/25**. Automation passes **144/144**. Both framework campaign variants
pass **2/2** pinned interpreter tests and compile.
All **17 physical maps** compile and pass archive inspection. The scoped audit
passes all three order-persistence obligations with **12 executed receipts** and
verifies immediate, point and target registrations in all **16 gameplay maps**.
The interpreter results and every diagnostic map share source digest
`16df8c17a1702adde7cc7438833f98b10dc9d9f70d61ece330302a13650a3aa7`.

The broad Python run completed 946 tests with one failure: its already-imported
save compatibility assertion still listed military versions 1–5 after the manifest
advanced to v6. The corrected assertion passes in the complete six-test
compatibility suite and in the final 25-test persistence rerun. The initial
transcript is retained as `full-python-initial.log.gz`.

Final results and source identities are retained in `validation.json`,
`scoped-evidence.json` and the compressed transcripts in this directory. The
scoped verifier reads the actual diagnostic campaign and follows the compiled
trigger/event aliases into all three registrations and the callback attachment.
It also checks executable receipts, save/restore references, native replay calls
and the artifact's exact source identity.

The nested `liveOrders` mappings cover only the order-persistence portions of
ROAD-0048.01, REQ-0233.01 and REQ-0234.01. The canonical report retains their full
obligation blockers. Physical remote-command transport (REQ-0300.01 and
ROAD-0062.01), other release blockers and native-client launch remain separate.
No player QA was requested. Interpreter tests, the native-save reconstruction
oracle and compiled registrations do not establish real-client gameplay.

The exact pinned compiler and bundled JRE were copied from the cached image into
ignored `_build/issue443-tools` storage. A cached standard library supplied offline
dependencies. Containers had no worktree mounts; all compilation ran locally.
`grill-offline.sh` records that local wrapper. From the repository root:

```sh
python3 maps/historical-world-rpg/_shared/tooling/run_wurst_tests.py \
  maps/historical-world-rpg/age-of-sail-world/package.json \
  --grill "$PWD/_build/issue443-tools/grill"
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-443/packaging-driver.py
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-443/verify-evidence.py \
  --artifact maps/historical-world-rpg/age-of-sail-world/_build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir maps/historical-world-rpg/age-of-sail-world/_build/wurst-tests \
  --output-dir maps/historical-world-rpg/age-of-sail-world/_build/issue443-evidence
```

The diagnostic driver uses the production assembly, materialization, pinned
compiler and archive inspection functions. It builds all physical maps after the
separate complete interpreter gate. Generated archives remain in ignored build
storage. No commits, pushes, GitHub changes, services or global tooling changes
were made.
