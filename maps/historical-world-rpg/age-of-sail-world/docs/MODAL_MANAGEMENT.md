# Management commands and pause ownership

Management commands pause the single-player campaign until their close action
is used. Text disappearing from the chat display does not close management.

| View | Open or switch | Close |
| --- | --- | --- |
| Remote command | `/region REGION`, map, holding or force ID | `/region return` |
| Roster | `/roster` (`/heroes`, `/companions`) | `/rpg-close` |
| Inventory/equipment | `/inventory [HERO]` (`/equipment`, `/items`) | `/rpg-close` |
| Journal | `/journal` (`/quests`) | `/rpg-close` |
| Technology/institutions | `/technology` (`/institutions`) | `/rpg-close` |
| Settlement market | `/trade inspect`, `/trade open`, `/trade markets`, `/trade commodities MARKET`, `/trade stores` (`/market`) | `/trade close` |

The four RPG views share one session. Reopening a view, selecting another hero,
or switching between those views retains that session's single pause owner.
The market has its own session; reopening it retains one owner. Opening both
RPG and market management requires closing both. Existing army/fleet/settlement
management closes with `/management-close`, and maps close with `/map close`.
Each close releases only its own owner. The final close restores the manual
pause state from before the first management screen opened.

`/trade select MARKET COMMODITY`, `/trade store STORE`, `/trade move SOURCE DESTINATION QUANTITY`,
`/trade buy QUANTITY`, `/trade sell QUANTITY`, recruitment, equipment actions,
research, quest actions, help, and passive notifications do not acquire ownership.
Actions issued inside management leave the existing session open. Screen output
and command help describe the available close and switch actions. Registration
errors stop bootstrap; RPG registration installs the close action before any
command that can open an RPG view.

See [local market and cargo commands](LIVE_TRADE_COMMANDS.md) for eligible listings,
physical access and selection requirements. These use the same market session.

`ManagementScreenSession` retains a token from the existing
`ManagementScreenPauseController`; it does not introduce a pause authority.
The installed campaign clock subscribes to that same controller, including its
current pause state when bound. Timer-driven and direct campaign advancement
both respect pause, preserving fractional days and scheduled-event cursors.
Military gameplay timers already subscribe to this boundary and remain stopped
until the final modal/manual pause releases them. Reinstalling a clock removes
its previous subscription and timer rather than accumulating listeners.

Sessions, tokens and listeners remain transient. Campaign schema 9 records the
manual pause choice and active physical command map; destination startup rebuilds
one remote-command owner. See [remote command maps](REMOTE_COMMAND_MAPS.md).
Trade save schema versions remain unchanged.
A committed campaign reconstruction closes the old RPG and market sessions.
Validation failures, reconstruction failures, and staged-load aborts retain
their sessions and reachable close commands. New campaign initialization retires
the previous market view; successful startup retires the previous RPG view.
Calling startup again on an already-started campaign preserves newly opened UI.
Other owners and any pre-existing manual pause continue to hold the shared pause.

`ManagementCommandTests.wurst` dispatches the production registrations through
recording output, pause, clock and gameplay-timer ports. Load-transaction and
startup tests exercise those commands with populated campaign authority and
production reconstruction/rollback. Run the pinned execution and packaging
checks described in [tests/README.md](../tests/README.md).

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
