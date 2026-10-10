# Remote military command maps

`/region DESTINATION` opens the physical terrain of a known, authorized command
location. DESTINATION can be a physical map ID, holding ID, mobile force ID or
logical region ID. A logical region spanning several physical maps is accepted
only when its current eligible holdings and forces identify one map. Otherwise,
use a physical map, holding or force ID. `/region return` loads the party's home
map. `/region retry` resumes an interrupted command handoff.

Discovery and permission remain separate. Current player-controlled holdings or
active, living player armies/fleets authorize their own map; knowledge, citizenship,
allegiance, legal title without control, and local AI defenders do not. Both
source departure and destination reconstruction validate current authority.

The party keeps its home map, coordinates, identities, assignments, equipment and
wounded deadlines. Remote startup creates no travelling-party replacements.
Destination military and holding projections use their own physical terrain.
Committed orders and the existing military/settlement, trade, quest and campaign
activity domains are captured in both directions. An entirely incapacitated
party can command remotely and return without creating field characters.

Remote command owns one modal pause token. Other UI owners remain independent.
The manual pause choice, fractional campaign time, event cursor, autosave slot and
remaining unpaused delay survive transport. A new map reconstructs the command
session's ownership; it does not serialize UI tokens or native handles. Returning
releases only the command session's token and preserves manual pause.

Live campaign schema 9 adds the versioned `commandContext` domain: active physical
command map, manual pause choice and known logical regions. Schemas 1–8 migrate to
the saved home map, initial scenario knowledge plus the home region, and manual
pause off. Existing valid context is preserved. No legacy movement or lost pause
history is invented. Party-location and military-order domain versions are unchanged.

The independent v1 `bootstrap/command_request` record carries an integrity-checked
`command_context` envelope and generated campaign/map identities. The existing
recovery envelope carrier is reused, with a distinct storage key and private slot.
The writer commits before invoking the physical loader and never retires source
projections on a failed write. Destination services wait for all registrations,
stage the ordinary load transaction, revalidate authority, acknowledge, then
publish. Rejection or interrupted acknowledgement rolls back and retains the
request. Consumed records remain usable after interruption before activation;
repeated startup or retry in an activated service has no additional effect.

Origin selection, boundary travel and explicit recovery supersede older command
requests through origin/recovery/milestone fingerprints. A save made remotely
loads its command map through the existing recovery action while preserving its
home party. Returning remains available after lost permission or failed startup.
Missing or invalid terrain is rejected before a loader call; a failed return
projection retains the checkpoint for retry or explicit save recovery.

`CommandMapTransportTests.wurst` exercises registered commands, fresh generated
registrations, physical load requests, native-order callbacks, storage failures,
permission loss, interrupted acknowledgement, saves, wounded parties and virtual
timers. The scoped diagnostic verifier checks the same source revision and built
chapter paths. Headless evidence does not certify native client launch or close
unrelated campaign simulation blockers. No player QA is required for this work.
