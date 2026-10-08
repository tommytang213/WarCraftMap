# Player recovery guide

This guide covers safe, supported recovery. These actions do not rewrite authoritative campaign progress, ownership, control, quests, or history.

## Saves and checkpoints

Create manual saves before risky decisions. The campaign also rotates through 15 timed autosaves (`autosave_01` through `autosave_15`), keeping older recovery points until their slots are reused. The support identifiers for these slots are `manual_N` and `autosave_01..autosave_15`. A separate `session_start` checkpoint and a separate `major_milestone` checkpoint do not consume autosave slots.

Use `/saves` to identify existing saves and their recorded physical maps. It lists
all 15 autosave positions, both checkpoints, and manual slots 1–10; missing slots
are omitted. `/saves manual 11` lists slots 11–20, and any positive first slot can
be used to inspect higher manual slots. `/saves autosave`, `/saves session_start`
and `/saves major_milestone` narrow the list. Unusable saves remain listed as
unavailable.

| Action | Command |
| --- | --- |
| Write a manual save | `/save N` |
| Restore a manual save | `/load N` or `/load manual N` |
| Restore one of the 15 autosaves | `/load autosave N` (1–15) |
| Restore the session checkpoint | `/load session_start` |
| Restore the milestone checkpoint | `/load major_milestone` |
| Resume an interrupted recovery handoff | `/load retry` |

Slot numbers are positive decimal integers without leading zeros, signs or
fractions. A malformed number is rejected; it never selects a different slot.
The support identifier `manual_01` is selected with `/load 1`.

Restoration loads the save's recorded physical map when needed, then restores
campaign progress and the party's recorded coordinates. It does not grant
starting supplies again or replay an already completed boundary arrival. Recovery
preserves the selected source slot and the existing session and milestone
checkpoints. Supported older saves without coordinates retain their documented
origin, boundary or settlement fallback; discarded movement cannot be recovered.

If destination startup is interrupted, `/load retry` reloads the retained request
through normal startup. `/load` and `/saves` remain available when gameplay startup
has stopped. Repeating a retry after successful activation has no additional
effect. A later new campaign start or milestone supersedes the old recovery
request. Reloading the destination after an interrupted acknowledgement can
reconstruct the retained checkpoint without applying starting grants.

If a save is requested during a transition, it is deferred and retried after the committed state is safe. If a load or transition is interrupted or rejected, retry from the active game or choose the latest suitable manual save, autosave, session-start checkpoint, or milestone checkpoint. A rejected load leaves both the active campaign state and the original stored save unchanged.

Incompatible, corrupt or incomplete saves are rejected with an English diagnostic
describing the envelope, schema, slot or destination problem. Do not edit, replace,
or delete the rejected save while seeking support.

## Recovery commands

- `/unstuck [all]` recovers stuck mobile units. With a selection, it moves only eligible player-controlled mobile units and skips buildings, walls, towers, city cores, destructibles, and system objects. With nothing selected, it tries the main character. If only ineligible objects are selected, nothing else is moved. `/unstuck all` considers physically active player-controlled mobile units in the current relevant region, never abstract or inactive-world entities.
- `/god [on|off]` toggles protection for every player-controlled runtime entity; `/god on` and `/god off` set it explicitly and safely when repeated. New, acquired, transferred, or reconstructed controlled entities inherit protection while it is enabled. The setting is player-wide but session-only: it starts OFF and resets to OFF after a campaign load.

`/unstuck` uses this exact fallback order for each eligible unit: nearest verified reachable safe position; verified last-known-safe position; valid connected recovery anchor; otherwise fail without moving the unit. Land and naval connectivity is checked, so units are not moved to disconnected land or decorative water.

Neither command changes authoritative progression. `/unstuck` changes only the current physical position of eligible representations, and `/god` is transient protection rather than saved campaign state. Use `/help unstuck` or `/help god` for the in-game command text.

## Missing objects, maps, and Warcraft saves

Campaign data uses stable identities; Warcraft units, structures, and other map objects are reconstructible representations. Missing or damaged runtime representations are rebuilt from authoritative state without inventing progress or changing ownership and control. Revisiting a physical map reconstructs its current campaign state, including changes made while that region was inactive. Cross-map travel commits a complete checkpoint before activating the destination; an interrupted arrival preserves the last committed map and state for a safe retry.

Native Warcraft save/load is supported and reconstructs transient runtime objects and timers from the saved authoritative data. For long-term or cross-release recovery, prefer the versioned campaign saves and checkpoints described above.

## What is not player recovery

Integrity reports, compatibility reports, stable-ID traces, reproduction fixtures, and package provenance are maintainer diagnostics. They may be attached to a support report, but players should not modify them. Editing save bytes, changing stable IDs, replacing package files, using developer/debug commands, or manipulating Warcraft objects through external tools is destructive or unsupported and can invalidate recovery guarantees.
