# Issue #415: installed god-mode lifecycle and protection ownership

The installed adapter normalizes region-entry, summon, training, construction
and ownership events through the compatibility boundary. The production callback
rejects missing/removed recipients and retired trigger context. All controlled
unit categories share current-owner eligibility, including same-session
replacements. Reinstallation preserves the session controller, replaces obsolete
listeners and retains one campaign-load observer; a reused command registry can
also bind a fresh session after teardown.

`RuntimeProtection` tracks independent claims, including protection present before
god mode and script/capture protection applied afterward. Removing one claim
retains the others; missing representations retire their claims and handles.
Military capture still expires on its original gameplay-clock deadline. Successful
campaign-load commit resets god flags, while failed reconstruction and staged-load
abort preserve them. No save fields, schema changes or handle persistence were
introduced.

`InstalledGodModeTests.wurst` executes production chat and lifecycle trigger
actions with distinct native producer/recipient handles. It covers duplicate and
obsolete delivery, acquisition/loss of control, replacements, repeated installs,
reused command registries, native-bit repair, both protection-expiry orders,
multiple players and exact capture deadlines. Its load journeys use the production
codec and transaction manager and compare unchanged campaign state and source
slots. The existing god-mode, military, load-transaction and framework suites
remain regression coverage.

All ten child obligations under REQ-0208–REQ-0214 have explicit mappings. Four
executed cases per obligation and the reconstruction dependency produce 44
receipts. The scoped verifier checks those receipts and compiled registrations
against the same-source diagnostic campaign, while retaining unrelated inventory
blockers and the separate native-launch release gate:

```sh
python3 reports/issue-415/verify-evidence.py \
  --artifact <diagnostic.w3n> --execution-dir <wurst-tests> --output-dir <report>
```

`validation.json` and the compressed logs record the actual validation results,
pinned compiler identity, working-source digest and artifact hash. Container runs
used the pinned image as `wurstuser`, with the worktree mounted read-only and all
compilation in container-private `/tmp`. A private Python copy and the recorded
standard-library checkout supplied dependencies without changing host tooling.
The compiler's bundled core JASS was used offline. Preliminary runs exposed an
absent-hashtable-record interpreter case; the final receipts use the guarded
implementation and complete suite.

The W3N is a diagnostic artifact. Release status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`. No retail execution, player
QA, commits, pushes or GitHub changes are claimed.

PR #424's failed [Wurst run](https://github.com/tommytang213/WarCraftMap/actions/runs/37777578705)
and [campaign build](https://github.com/tommytang213/WarCraftMap/actions/runs/37777578859)
both reached 324/327 passing tests. Four campaign-load journeys hit the unchanged
20-second interpreter limit across those runs: founded-polity restoration, two
recovery/travel journeys, and full-group equipment restoration. Their timeout
stacks all entered `lastAuthorityValue`, which rescanned every domain payload for
each requested field. The installed god-mode tests passed in both failed runs.

The CI repair indexes semicolon offsets for the current immutable authority
document and discards the index when its text changes. Reads retain last-value
selection, empty values, the existing domain-boundary grammar and embedded trade
store separators. Clock, party-location and autosave validation reuse the same
index to reject absent or duplicate metadata. Four executed Wurst regressions
cover those rules, switching between equal-length documents, metadata rejection
followed by valid reads, and a payload with 300 embedded separators. Save
schemas, load assertions, capture deadlines and interpreter limits are unchanged.

The original validation files remain historical evidence. `repair-validation.json`
and the `repair-*` receipts record validation of the repaired source and its
diagnostic campaign. The same scoped verifier checks the ten god-mode obligations,
their reconstruction dependency, all 44 receipts and compiled registrations.

The repaired source passes 331 pinned Wurst tests, 923 scenario Python tests and
129 automation tests. Both framework campaign variants execute and package with
all 158 shared-source hashes verified. A separate comparison of the four timeout
journeys measures 9.6–12.9 seconds before the repair and 3.4–11.3 seconds afterward
on this environment, using the same pinned interpreter and unchanged assertions.
Those timings describe local validation, not a claim about GitHub runner speed.
