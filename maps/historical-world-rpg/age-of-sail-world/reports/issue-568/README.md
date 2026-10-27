# Issue #568: isolated Calculus scholarly-work verification

This source change recognizes the existing registered `calculus_methods` →
`modifier:progression_calculus_methods` → `research_generation_efficiency`
contract at 500 basis points. It adds no research consumer or gameplay
coefficient and preserves the Barometric and Chemical bindings.

The matched production test earns Calculus only in the treatment through
registered `/research`. Both arms use the same qualified London scholarly site
and `printed_observation_tables` target, pay its full authored research bill in
advance, and consume actual daily treasury and materials. Calculus makes 105
versus 100 work per funded day and completes 9000 work in 86 versus 90 funded
days. The test also removes a target prerequisite before completion and verifies
that paid work cannot grant the now-ineligible target; a completed target cannot
be purchased a second time. Other tests cover missing inputs, eligibility,
fractional work, additive Chemical sources, active/inactive parity, capture,
resumption, and late campaign-load rollback after completion.

`pinned-evidence.tar.gz` contains the complete pinned Wurst result, raw
transcript, and verification inputs for source revision
`51ce10d3b519652f5d574da24d9437cb914639a9`. The full Wurst suite passed
739/739, and extracted archive readback passed the repository verifier against
that exact revision, source tree hash, compiler digest, and log. The independent
source review at `06ed32a` found no concrete defect; `51ce10d` changes only
the three checked-in source-only audit snapshots.

The same pinned source revision passed a separate full 739/739 Wurst run and a
sequential campaign packaging retry: all 739/739 tests, all 17 physical maps,
and the 61,539,852-byte W3N, SHA-256
`f1f34e9cf91cbde6aab96a317f961e3369f3e834a768b98db76c3084106b0f0c`.
The first campaign attempt, concurrent with Python, timed out in unchanged
`TradeCommandTests.wurst:225` during batch 7. Its compressed transcript is
retained as `concurrent-campaign-timeout.log.gz`; the same test passed in the
separate full Wurst run and in the isolated campaign retry. The exact-revision
complete Python discovery passed 1,201/1,201 tests, including framework
fixture and mutation checks (3/3 each). Automation passed 215/215. Framework
boundary, world, geography, map source and checked-in audit freshness checks
passed. No player QA was required.

`audit-results.json.gz` contains all three reports regenerated with the verified
campaign and same-revision execution. The Calculus unbound finding is absent.
The release audit still has 187 findings, runtime acceptance passes with zero
failures but reports release readiness false, and traceability still has 8,363
publication blockers. These are unrelated to this ticket and do not establish
native-client or release readiness. The exact source revision and archive hashes
are recorded in `validation.json`. CI results will be tracked on the draft PR.

The checked-in audit snapshots remain source-only for freshness checks.
After integration, regenerate release-blocker, runtime-acceptance, and
requirement-traceability audits on the new main revision with the normal
verified evidence path before closing the issue. Unrelated release blockers
remain outside this ticket.
