# Campaign-owner research commands

Local source: `251a325e060532b8638f422f1437baefadb678f1`, based on PR601 head `e0c1ac3c`. This follow-up is not included in that earlier head's checks.

The production resource adapter maps senders to the single campaign's persisted `player` research identity. `/research`, `/unlock` and `/institution` therefore require the campaign player before any resource access, cost calculation or shared research mutation. Direct controller-scoped runtime APIs remain unchanged; this is not a ban on AI/simulation research.

Two negative production-command cases exercise all three aliases for another player and a missing sender, proving unchanged resource reads/writes, gold, effects, serialized research and active quest objectives. The owner then pays once, acquires exactly one unlock with the correct controller/entitlements, completes the linked objective and preserves it through current-schema codec restoration. Existing valid owner fixtures now name `Player(0)` explicitly. Read-only screens, malformed parser cases, voyage helpers and direct controller APIs are untouched.

The first run passed 18 existing research tests but exposed a positive-test helper assumption: a successful unlock plus research-linked quest progression invokes two idempotent entitlement replacements, while the no-quest helper expected one. The corrected test checks both replacements, one payment/unlock, unchanged other-controller effects, exact entitlement identities and no one-time grants. Production behavior was not altered to satisfy the counter.

Original pinned compiler/bundled runtime validation then passed 20 research and 57 military tests at `b481b2f8`. After restoring additional explicit positive assertions, final `251a325e` passed all 20 research tests and both directly affected military save/rollback cases. Transcripts and input hashes retain actual tested identities. Independent static review approved the final source. These are focused checks, not a complete current-head execution gate; native acceptance and release blockers remain unresolved.
