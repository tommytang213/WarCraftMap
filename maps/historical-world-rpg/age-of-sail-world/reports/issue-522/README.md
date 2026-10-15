# Issue #522: qualified Cast Cannon gameplay

The [scenario contract](../../docs/CAST_CANNON_COMBAT.md) binds the existing
`(modifier, progression_cast_cannon)` entitlement to +500 basis points of damage
rating for verified heavy shipboard cannon profiles. An otherwise identical
base-100 control receives 100 damage; the researched force delivers 105.
Research prerequisites, historical/ahead-of-time prices, equipment, conversion,
refits and military tradition remain separate.

The shared Wurst and Python adapters consume current controller membership and
validated weapon identity. Research does not require a tradition track. Ratings
add before one exact damage calculation; reserved source identities and existing
hit receipts prevent double application. Reconstruction, controller transfer,
abstract resolution, supported save envelopes and late-load rollback use the
same contribution. No new durable fields are introduced. Combat definition
catalogue v3 reads v1/v2 definitions through migrations.

**190/190 scoped pinned Wurst tests and 157/157 targeted Python tests passed**,
including all five new Cast Cannon production/save tests.

`validation.json` binds final verification and transcript hashes to the current
revision plus dirty source digest. The pinned toolchain was extracted from the
cached immutable image and executed locally using temporary tooling; the
worktree was never mounted writable into a container. Framework validation builds
both the original and content-mutated standalone campaigns, with two interpreter
tests in each and unchanged shared sources. Synthetic compiler fixtures in Python
tests are separate from that pinned execution evidence.

[Regional payload inspection](regional-payloads.json) covers all 17 physical map
payloads, including the intentionally minimal selector and 16 executable regional
consumers, with all 43 qualified profiles retained. It inspects generated Wurst
and runtime JSON; it does not claim compiled regional archive or native-client
launch verification. [Battle simulations](battle-simulations.json) retain passing
maximum land, naval and mixed deterministic profiles.

The regenerated release audit removes exactly
`RESEARCH-UNBOUND-CAST-CANNON-MODIFIER-PROGRESSION-CAST-CANNON` and retains all
239 other campaign blockers, including 218 unbound research consumers. Runtime
acceptance and requirement traceability were recomputed and retain their existing
blocked results. They do not substitute focused interpreter evidence for complete
campaign or native-launch acceptance. After merge, regenerate all three audits
on the new main revision as required by the issue.

Reproduce the scoped pinned typecheck and interpreter suite with:

```sh
python3 reports/issue-522/validate.py --grill /path/to/pinned/offline/grill
python3 reports/issue-522/inspect_payloads.py
```

The outer worker remains responsible for authoritative repository validation.
No commit, push, GitHub write, World Editor operation or player QA was performed.
