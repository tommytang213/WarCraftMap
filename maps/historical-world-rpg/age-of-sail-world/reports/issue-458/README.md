# Issue #458: exact expandable military tradition XP

Military XP and weighted awards now use canonical decimal strings with exact
integer-only arithmetic. The installed death callback can commit an eligible
one-point loss at 2,147,483,647 and retain 2,147,483,648. Larger awards, totals
beyond 2^53 and carries across hundreds of digits remain exact. Controller and
category attribution, legal-target checks and consumed-loss replay protection
continue through the existing combat path.

Military snapshot v8 writes exact XP directly, migrates supported v1–v7 integer
records, and rejects malformed numbers in detached authority. The live campaign
codec retains large XP together with losses, ownership and orders. Tests cover
fresh services, physical-map travel, remote command, transfers, reconstruction,
illegal and stale deaths, native teardown, and rollback after late load failures.
Inspection displays the full XP. Native stat bounds never replace XP authority.
The scenario's placeholder health coefficient remains zero.

See [LIVE_COMBAT_TRADITION.md](../../docs/LIVE_COMBAT_TRADITION.md) for the
representation, migration and projection contract. The evidence covers
ROAD-0052.01, REQ-0154.01, REQ-0164.01 and the numerical obligation REQ-0158.01.
Authored live coefficients, qualitative milestone effects and non-kill adapters
remain open, along with the corresponding broader progression obligations.

The final pinned suite passed **436/436 tests** and explicit typecheck. All
**167 targeted Python tests** passed; the **48 traceability tests** also passed
after the evidence-link correction. Each framework consumer passed **2/2 tests**
and built its **three-map campaign**, retaining all **173 shared source hashes**.
The diagnostic Age of Sail campaign built **17 physical maps**. Scoped evidence
passes all four obligations with **16 receipts** and **nine exact award/total
vectors** checked against the headless integer oracle.

Validation uses the cached pinned Wurst compiler, Java and standard library,
copied into ignored storage inside this worktree. No container, service
installation, global tool change or player QA is required. The original and
content-mutated framework consumers build with identical shared sources.
[validation.json](validation.json) records the completed checks, source identity,
artifact digest and retained transcripts. [scoped-evidence.json](scoped-evidence.json)
binds the production callback receipts and Python integer-oracle comparisons to
the same-source diagnostic campaign.

Recheck or rebuild the evidence using the worktree-local toolchain:

```sh
python3 reports/issue-458/build-diagnostic.py \
  --grill "$PWD/_build/issue458-tools/grill" \
  --execution-dir _build/issue458-verified
python3 reports/issue-458/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/issue458-verified \
  --output-dir _build/issue458-evidence
```

The generated campaign remains in ignored `_build/release` storage. These
checks do not establish a native Warcraft launch or designate a release
candidate. `blocked_pending_real_forsaken_kingdom_launch_smoke` remains unchanged.
The outer worker performs the authoritative repository validation. No commit,
push, issue/PR action or publication is part of this work.
