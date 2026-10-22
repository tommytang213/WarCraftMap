# Issue 525 merge integration

The subsequent validation retry found a no-op version substitution in
`scienceActiveAbstractSaveMigrationCaptureAndMalformedLoadKeepAuthorityExact`:
the merged fixture replaced `v19|` with `v19|` before expecting rejection.
It now asserts the current save prefix and substitutes unsupported `v999|`,
then verifies unchanged live state. The focused assembly now includes the science
suite. All production implementation and merged banking/logistics behavior are
preserved. Fresh retry evidence is retained separately in `validation-repair.json`
and `validation-repair-wurst.json`; the results below describe the earlier run.

This retry passed pinned typechecking and **58/58 interpreter tests**, with
before/after hashes for 381 compiler inputs and individual production-probe
results retained. **54 focused Python tests**, **9 framework conformance tests**
and **88 audit regression tests** passed. The initial Python command also had one
framework module import error; rerunning that suite with `PYTHONPATH=tests`
resolved it. Framework packaging fixtures use a synthetic compiler and are not
additional pinned interpreter or native-client evidence. Framework boundary,
traceability freshness and generated-payload inspection passed for all 17 maps
and 794 administrative districts. All three acceptance reports were regenerated
against the retry source identity; release blockers remain for controller-owned
complete execution and packaged-campaign validation. No player QA is needed.

The six actual conflicts are resolved and staged, preserving administration,
banking and army-food logistics. No commit, push, GitHub mutation or player QA
was performed. The controller owns complete repository validation.

Both prior branches used military snapshot v18 and record `b` for different
ledgers. The integrated v19 codec keeps banking `b` and freight `z`, writes
municipal `u`, and requires complete current ledgers. Arity-based migration
preserves six-field municipal v18 and seven-field banking v18 records; absent
policies initialize inactive. Duplicate, missing, malformed and foreign-owner
records reject without changing live state. Existing v17 banking/freight and
older campaign migrations remain covered. The source-readiness contract,
release-save manifest and current-format test fixtures now use v19.

The automatically merged research-generation expectation omitted both new
administrative consumers. Its expected bindings now retain administration and
banking together. Runtime manifests retain both sets of production probes and
checks without duplicate system IDs.

Fresh validation uses the merged worktree, never predecessor execution artifacts:

- Pinned Wurst typechecking and **51/51 interpreter tests passed**, including
  registered archives/adoption/municipal actions, downstream economic differences,
  rejected prerequisites/resources/duplicates, office replacement, capture,
  representation loss, active/abstract parity, late load rollback, banking,
  freight, legacy migrations, research bills and shared framework cases.
- The new combined codec regression round-trips both ledgers at one settlement,
  migrates each independent v18 layout and checks atomic rejection.
- **45 focused Python tests passed** across administration, economy, civic and
  administrative contracts, progression, banking and save compatibility.
- Research generation **10/10**, runtime acceptance regressions **25/25**,
  requirement traceability **53/53** and release-audit regressions **10/10** passed
  after correcting the merged expectation and refreshing reports. Earlier runs
  found stale reports while integration inputs were changing; final results use
  the source identity in `integration-validation.json`.
- Framework conformance **9/9**, framework boundary and traceability freshness
  checks passed. Generated-payload
  inspection covers **17 physical maps and 794 administrative districts**.

`integration-validation.json` retains individual Wurst results and production
probe hits. The compiler digest matches the pinned toolchain and compiler input
hashes were unchanged during execution. Container validation used read-only source,
UID/GID 1001, disabled networking and container-private `/tmp` build storage.
Python packaging fixtures are not compiled map or native-client evidence.

All three official audits were regenerated for the same final source revision
and dirty-tree hash. Static readiness passes. Release findings remain open until
the controller supplies complete same-source execution and packaged-campaign
evidence and regenerates closure audits again on integrated main.
