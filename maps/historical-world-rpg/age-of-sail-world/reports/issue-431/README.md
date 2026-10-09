# Issue 431: Authored historical research costs

Generator v21 preserves every authored time-cost field as exact decimals for
181 technologies and 25 institutions. The shared live calculation follows the
headless historical formula and its decimal precision. The native gold boundary
rounds millionths up to whole points and rejects overflow before mutation.
`pike_and_shot` now costs 864 gold in 1450, 728 in 1469 and 90 from 1470 onward.
See [the numeric and persistence contract](../../docs/HISTORICAL_RESEARCH_COSTS.md).

Registered commands retain all controller-specific prerequisites, insufficient
funds rejection and completion protection. Tests assert exact debit and effect
counts, rejection atomicity, changed clock dates and definitions, restored dates,
and continuation through all supported campaign envelope schemas. Existing
completions and save formats are unchanged.

The scoped evidence covers REQ-0037.01 and REQ-0038.01. ROAD-0045 receives the
historical-cost correction and four scoped command receipts; its broader
technology/institution integration remains blocked in traceability, as does
DEP-clock-research. No unrelated integration or native-launch blocker is cleared.

Final validation, bound to the revision and dirty source digest in
[validation.json](validation.json):

- **352/352 pinned Wurst tests passed**, including independent decimal fixtures,
  registered commands, prerequisite/controller isolation, save continuation and
  all supported campaign envelope versions. Compiler SHA-256 is
  `1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`;
  cached standard library revision is `110252dd8b19fe683505bfbbbd6b6a1f9f4dfd9e`.
- **936 scenario Python tests and 129 automation tests passed** through
  `automation/run_checks.sh`. Its Wurst branch was explicitly skipped because
  the full pinned suite, diagnostic typechecks/builds and framework packaging
  ran separately with the local offline compiler adapter.
- **125 targeted Python tests passed**, covering research, clock, generation,
  saves, compatibility, execution evidence and traceability. The 20 independent
  cost vectors include the preferred-year boundary, fractional coefficients,
  28-digit rounding and signed integer limits.
- **17 physical maps typechecked, compiled and passed archive inspection**.
  [Scoped evidence](scoped-evidence.json) verifies all 206 research definitions
  in each of the 16 gameplay maps: **3,296 complete compiled registrations**,
  exact authored cost fields, command/calculation calls, and current source
  identity. Both historical-cost requirements pass with eight executed command
  receipts; another four receipts document the narrower ROAD-0045 cost scope.
- Original and content-mutated framework campaigns each passed **2/2 Wurst
  tests** and compiled with unchanged shared sources. World/source validation,
  framework boundaries, traceability freshness and `git diff --check` passed.

The source release audit retains its same 21 findings. The full artifact report
still records 8,764 publication blockers and `candidateReady: false`.
Native-client execution remains unperformed. Python logs include intentional
failure output from negative compiler, packaging and temporary worker fixtures;
their unittest summaries report success.

The pinned compiler and bundled JRE were read from the cached container image
into ignored worktree storage, then executed locally. The standard library was
also reused from the cache. No writable source mount, global tooling change,
service installation, project commit, push, GitHub write or player QA was used.

Reproduce the scoped evidence after the pinned suite and diagnostic campaign build:

```sh
python3 reports/issue-431/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/wurst-tests \
  --output-dir _build/issue431-evidence
```

The verifier binds the full source revision and dirty input digest, validates
the pinned transcript, checks command and calculation calls in all sixteen
regional maps, and compares all four compiled cost fields for every authored
research node in each map. The twelve scoped receipts cannot clear the broader
roadmap or dependency blockers. Compressed logs and reports retain the final
automated validation results; generated game archives remain under `_build`.
