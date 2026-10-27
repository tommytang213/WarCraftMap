# Issue #438: production startup milestone diagnostic

Base: draft PR #536 head `40ef28865bc5ed0886bc60622a8cabfaff19084b`.
Scope: Austria selector → Victory → Continue → `EuropeCentralEast.w3x`.
This is an isolated, nonrelease diagnostic. It does not establish a repair.

The destination retains the normal registration, synchronous
`campaign.startup()`, save/cache writes, gameplay activation, and timer setup.
Only the real Europe Central East map emits these positive display milestones:

1. `destination-entry`: the destination's Wurst `init` function entered.
2. `startup-returned-success` or `startup-returned-failure`: the normal
   synchronous startup returned. The failure branch retains recovery commands.
3. `initializer-complete`: the existing initializer reached its final statement.
4. `recovery-callback-1s`: the existing one-second recovery timer callback
   entered for the first time. This is not the earliest engine/Wurst callback.

The diagnostic inserts no timer, changes no interval or save schema, and does
not skip initialization or scenario content. Each marker is gated by the
physical map ID. A visible marker is a positive observation at that stage;
no visible marker on a black display cannot distinguish non-entry from failed
text rendering/log delivery. A callback marker does not prove terrain or unit
control. Native acceptance still requires visible destination terrain and a
player-controlled unit responding to movement.

The staging profile `production-milestones-438` requires all milestone literals
in the compiled Austria destination Lua and records that Lua's SHA-256. The
normal campaign inspector also checks all 17 nested map hashes, physical-map
metadata and build identity. Negative controls remove each marker literal or
the diagnostic prefix and must fail staging; an empty destination must fail.
The existing staging guard rejects known failed W3N hashes. These checks are
static and cannot prove compiled control flow or native display delivery.

Do not request an unchanged Windows retest. Before one targeted native check,
the exact source must be committed and reviewed, built through the unchanged
Wurst/campaign gates, staged as a versioned W3N with source and archive hashes,
and independently inspected. The main-only launch-smoke workflow is not a
reason to merge the draft PR. Release gates and the 188 research-consumer gaps
remain untouched.
