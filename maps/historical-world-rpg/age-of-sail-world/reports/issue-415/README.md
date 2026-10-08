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
