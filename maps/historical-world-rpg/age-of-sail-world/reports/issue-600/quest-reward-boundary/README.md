# Quest reward delivery boundary: focused validation

Source: `6a523d7f5e943b692856b004c0b2e74e09d2b5d6` (integrated reward boundary and command/restore test strengthening).

Production-aligned assembly typechecked successfully. Seven exact-package suites passed 89/89: QuestReward17, AuthoredQuest29, QuestTrade8, QuestConsultation7, ResearchRuntime20, ReligionRuntime6, RpgCommandOwner2. Each parsed result records exit0, no parser issues and unchanged frozen inputs. Five Python reward-generation tests also passed. This is focused evidence only, NOT a complete current-head execution gate, native acceptance, release approval or a claim that recovery timeouts are resolved. No acceptance reports are changed here.

`runner.py` archives the actual orchestration. Original bundled Java and compiler were extracted from the pinned immutable image, not run through Docker; the embedded result `executionImage` records the configured image identity, not container execution. `provenance.json` binds source, compiler/Grill/runtime hashes, stdlib revision and exact execution scope. `inputs.json` contains175 verifier inputs (including bootstrapped core JASS); `dependency-inputs.json` separately inventories stdlib content. Dependency URL casing was normalized before recording inputs, as documented in provenance.

Logs are deterministic gzip archives. Manifest `files` hashes are compressed/on-disk bytes; `rawTranscripts` hashes and sizes refer ONLY to decompressed original transcript bytes. Parsed suite JSONs are preserved unchanged. Driver exit0 covers the checked typecheck and serial orchestration; Python exit0 is archived separately. Warnings in typecheck remain in the raw log.

Earlier fa6066 full-suite recovery/clock timeouts remain separate failed evidence and are not superseded by these focused passes. No Wurst execution was rerun to prepare this archive.
