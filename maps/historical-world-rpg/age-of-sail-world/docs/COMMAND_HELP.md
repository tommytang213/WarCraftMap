# Installed command help

`_shared/wurst/CommandRouter.wurst` owns command registration, help, installation
and the chat callback for both the minimal selector and regional maps. The
selector's seven-package dependency graph is unchanged. Gameplay registrations
remain in their existing shared systems; no scenario data was moved into the
router.

`installCommandRegistry(registry)` selects `WarcraftCommandChatNatives` and calls
the same installation overload used by the recording fixture. Only native chat
registration, listener retirement and event context are replaceable. Installation
creates the trigger, registers `/` for every player slot and attaches `routeChat`
with `TriggerAddAction`. The callback reads the event player/text through that
boundary and accepts only the currently installed trigger. Reinstallation first
retires the previous listener with `DestroyTrigger`; uninstall also clears the
active registry before retirement. A queued obsolete callback cannot dispatch
to either the old or the new registry.

Help is a read-only presentation of registered metadata. Listing commands,
pagination, canonical/alias topics, errors and replay neither execute command
handlers nor mutate campaign authority or write campaign storage. No help page,
listener, callback, output or visibility state belongs in a save. Registry
metadata and listeners are reconstructed on each map/session. This introduces no
save schema change or migration. Numeric pages are bounded before conversion so
large inputs cannot overflow into valid pages; zero and negative pages report
the same English bounds message.

`InstalledCommandHelpTests.wurst` starts a campaign through the existing startup
fixture and uses the production help factory and recovery, RPG, origin and save
registrations. Extra developer/internal sentinel commands exercise both hidden
visibility classes, since there is no authored developer command catalogue in
the release. The recording boundary retains subscriptions and supplies event
context; the pinned interpreter's `TriggerEvaluate` invokes the exact action
attached by production `TriggerAddAction`. It is an interpreter delivery aid,
not a claim that retail `TriggerEvaluate` executes actions. Every case checks
the complete campaign snapshot, storage write count and hidden-handler count.

The six mappings REQ-0203.01, REQ-0204.01, REQ-0205.01, REQ-0205.02, REQ-0206.01
and REQ-0207.01 each require a receipt for success, rejection, stale registration
and replay. Receipts are printed only after output and authority assertions.
Source references distinguish the injected installation overload from its
native wrapper. Compiled evidence requires the native registration and the
specific `routeChat` action connection in each regional map. Python negative
fixtures remove either connection while retaining passing handler results and
even synthetic adapter receipts; reachability must still fail.

Run the normal pinned campaign builder and framework conformance gate, then
regenerate the exact-artifact report with:

```sh
python3 tooling/requirement_traceability_audit.py --write --check
python3 tooling/requirement_traceability_audit.py --write --check \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution _build/wurst-tests/results.json \
  --transcript _build/wurst-tests/execution.log \
  --source-revision "$(git rev-parse HEAD)" \
  --output _build/release/requirement-traceability
```

The checked-in source report intentionally has no execution or artifact inputs;
it must continue to report those missing inputs. The issue-411 evidence snapshot
records the implementation's base revision, dirty-source digest, pinned results,
exact diagnostic artifact digest and scoped checks. It does not authorize a
release: all unrelated requirements, content census, retail launch and archive
compatibility blockers retain their existing gates. No player QA is required.
