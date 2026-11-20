# Scoped authored research-reward batches

Final source ca166a31cbbd0a767c5ff25e1c373b6ddae2bc31. Only quests containing authored complete_research select the new generic batch path, currently two quests. Every eligible sibling outcome must be supported before any quest completion, XP, currency or research change. Reached-stage subset qualification matches the Python outcome model. Earned research targets are granted directly to campaign player, without payment or implicit prerequisite unlocks. Capacity, deduplication, known definitions and ordinary reward bounds are preflighted. Existing persisted quest completion and unlock keys provide replay protection without a save-schema migration.

Explicit /turnin and physical /interact share scoped owner/fresh-presence checks, transaction and postcommit player research synchronization. Blocked reward feedback remains visible even if another legitimate visit progressed. Both actual selected quests contain unsupported siblings and remain blocked atomically. Other 302 quests retain the legacy generic reward path; their authored rewards are NOT claimed implemented. No unspecified treasury amount is invented.

Validation:
- 02c compilation exposed a reserved keyword in a fixture; no test assertions ran.
- 644 passed 8/12; fixture issues involved restoring projection without the loader's reconciliation, a supposed XP overflow that was valid at zero, and unregistered command fixtures.
- ec0 corrected those fixtures and passed 10/12; historical-ready setup then proved to double-advance sole-successor stages already advanced by completeObjective.
- 9f33 corrects that setup and passes reward12, authored26 and research20.
- Final ca166 adds only a scoped ordinary-failure diagnostic and regression; reward13 and Python generation17 pass, with exact source/input/toolchain receipts. Independent static review approves the final source.
- Integrated final ca166 additionally passes reusable-framework boundary, canonical map-source validation, campaign quest13 and quest-event runtime8.

Failed development logs are retained alongside passing results, without promoting focused runs into a full-suite claim. Current-head CI, real Warcraft acceptance and broader authored reward delivery remain unresolved. See docs/authored-research-rewards.md for the cross-runtime contract and intentional scope boundary.

Traceability follow-up: source3fda69bf updates the existing earned-growth mapping to the real turnInQuest → commitQuestTurnIn → journal.turnIn chain. The mapping was independently reviewed without removing gates. An initial 54-case run against stale pre-refresh reports failed one test and one check; after regeneration, all54 pass and source freshness --check passes. Reports remain blocked (30 runtime,238 release,7004 traceability findings across643 obligations). Runtime/test source is unchanged from ca166.
