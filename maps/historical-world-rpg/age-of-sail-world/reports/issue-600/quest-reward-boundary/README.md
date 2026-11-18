# Quest reward delivery boundary: focused validation

Source: `6a523d7f5e943b692856b004c0b2e74e09d2b5d6` (integrated reward boundary and command/restore test strengthening).

Production-aligned assembly typechecked successfully. Seven exact-package suites passed 89/89: QuestReward17, AuthoredQuest29, QuestTrade8, QuestConsultation7, ResearchRuntime20, ReligionRuntime6, RpgCommandOwner2. Each parsed result records exit0, no parser issues and unchanged post-typecheck verifier-input subsets. Five Python reward-generation tests also passed. This is focused evidence only, NOT a complete current-head execution gate, native acceptance, release approval or a claim that recovery timeouts are resolved. No acceptance reports are changed here.

`runner.py` archives the actual orchestration. Original bundled Java and compiler were extracted from the pinned immutable image, not run through Docker; the embedded result `executionImage` records the configured image identity, not container execution. `provenance.json` binds source, compiler/Grill/runtime hashes, stdlib revision and exact execution scope. `inputs.json` contains175 verifier inputs (including bootstrapped core JASS); `dependency-inputs.json` separately inventories stdlib content. Dependency URL casing was normalized before recording inputs, as documented in provenance.

Logs are deterministic gzip archives. Manifest `files` hashes are compressed/on-disk bytes; `rawTranscripts` hashes and sizes refer ONLY to decompressed original transcript bytes. Parsed suite JSONs are preserved unchanged. Driver exit0 records orchestration termination after checked typecheck, not suite success; Python exit0 is archived separately. Warnings in typecheck remain in the raw log.

Earlier fa6066 full-suite recovery/clock timeouts remain separate failed evidence and are not superseded by these focused passes. No Wurst execution was rerun to prepare this archive.

## Evidence scope clarification

These runners are immutable records of the original invocation, not supported replay entry points. Their literal sourceRevision was checked during archival reconciliation, not enforced by the script itself. Do not execute an archived runner against a moved checkout and attribute its output to that literal revision.

`inputsUnchanged` compares the verifier input subset captured **after typecheck** with that subset after each suite. It does not cover assembly or typecheck, which can bootstrap core JASS, or `_build/dependencies`. The separate stdlib inventory is a point-in-time archival content inventory, not evidence of unchanged dependencies throughout execution. `inputsVerifiedNow`, where present, means archival verification of the recorded verifier-input subset only.

The archived driver can return zero after recording a failed suite and breaking its loop. Driver zero proves orchestration termination, not successful or complete execution. Acceptance requires every requested package report, zero test returnCode, no parser issues, unchanged recorded inputs and a passing result for every expected test. Initial land-idle remains 17/18 failed despite driver zero. No historical runner, driver status, test result or transcript was rewritten by this clarification.

Future replay must use an explicit exact clean source revision, a fresh assembly with bootstrapped inputs, pre/post dependency hashes, actual pinned toolchain verification and nonzero termination for any failed/missing suite, parse error or input drift. No full/native acceptance follows from these focused archives.
