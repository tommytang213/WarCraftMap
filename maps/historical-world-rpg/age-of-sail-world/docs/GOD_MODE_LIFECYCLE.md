# Session god-mode lifecycle

`/god` toggles player-wide protection; `/god on` and `/god off` set it
idempotently. Heroes, companions, ordinary units, summons, ships and structures
share the same current-owner predicate. AI and neutral ownership do not inherit
another player's mode. No unit-type catalogue or campaign-specific IDs are used.

`PlayerGodMode` installs one lifecycle trigger through `WC3Compatibility`.
Region entry uses `GetEnteringUnit`, summoning uses `GetSummonedUnit`, training
uses `GetTrainedUnit`, construction uses `GetConstructedStructure`, and ownership
transfer uses `GetTriggerUnit`. All player slots are subscribed, including
neutral previous owners. Missing and removed recipients reject before mutation;
events queued for retired listeners cannot affect a reconstructed adapter.
Repeated installation retains the session controller and one load subscription.
The installed periodic sweep reconciles current ownership and removes vanished
representations even when no removal event was delivered.

`RuntimeProtection` owns independent claims on each current representation.
God mode, capture immunity and other script protection use separate source IDs.
Every engine invulnerability write goes through `compatSetUnitProtection`;
`compatSetUnitInvulnerable` is the compatibility spelling for the script source.
Additional independent systems allocate their own positive source IDs and release
only those claims. An already invulnerable unclaimed object is attributed to the
script source. The native bit reflects whether any claim remains. A native bit
cleared during reconstruction is repaired while protection is still active.
Claims and unit references are retired on compatibility removal or the next
sweep after an external removal. These records are representation state, never
campaign authority.

Military capture continues to own its existing gameplay-clock deadline. Expiry
releases only the capture claim at the original deadline; toggling god mode
neither extends nor shortens it. Successful campaign loads clear all god flags
through the post-commit observer. Rejected or aborted loads retain the session.
Independent protection survives either order of release. God flags and handles
are excluded from campaign persistence; existing save schemas remain unchanged.

`InstalledGodModeTests` installs production chat and lifecycle actions and invokes
them through interpreter triggers. Recording native context gives producers and
recipients different identities, including stale and duplicate delivery. The
fixtures also execute the production protection registry, military adapter,
capture expiry, campaign codec and load transaction. Receipts map all ten child
obligations under REQ-0208–REQ-0214 and their reconstruction dependency.

Diagnostic artifact evidence is checked with
`reports/issue-415/verify-evidence.py`. This evidence does not establish retail
execution. The release block remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`; no player QA is requested.
