# Issue #438: production startup milestone diagnostic

Base: draft PR #536 head `40ef28865bc5ed0886bc60622a8cabfaff19084b`.
Scope: Austria selector → Victory → Continue → `EuropeCentralEast.w3x`.
This is an isolated, nonrelease diagnostic. It does not establish a repair.

The destination retains the normal registration, synchronous
`campaign.startup()`, save/cache writes, gameplay activation, and timer setup.
Regional maps emit these positive display milestones; the Austria handoff
targets the real Europe Central East map. The shared bootstrap compares map
identity with the authored selector ID, keeping scenario names in content:

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

## 2026-10-27 local execution

The isolated source commit is `3c14048a6e663d563947a8b2693ea4bc0be58adb`.
`python3 -m unittest tests.test_launch_diagnostics` passed all 18 tests,
including marker-removal negative controls. `git diff --check` passed.

The pinned Docker image was present, but three initial local package attempts stopped
at `grill install`, before Wurst compilation or campaign packaging. The first
could not connect to `github.com`; the next two supplied the workspace proxy
and CA certificate, and the third also supplied Java proxy properties. JGit
still timed out resolving `https://github.com/wurstscript/wurstStdlib2`.
The third terminal log is retained locally as
`/workspace/WarCraftMap-438-diagnostic-build-proxy.log`, SHA-256
`7e8265ca718eebaa582896623fd36fd019be55cea663d57155fb1075858d1aaa`.
No compiled marker, versioned W3N, artifact-gate pass, independent review or
native result is claimed from these attempts. The separate clone and branch
remain clean; the shared PR branch was not changed.

A final proxy check installed Git in the ephemeral container and configured
`http.proxy`. Native Git resolved the standard-library HEAD, but Grill's JGit
still failed its own dependency clone before compilation. The terminal log is
`/workspace/WarCraftMap-438-diagnostic-build-gitproxy-fixed.log`, SHA-256
`b5c61c853c246d774594bc8a55d0baf20c830bf13ce6bcfa9094512d36d82baf`.
An earlier attempt at that check was stopped
after discovering that the pinned image did not contain the Git CLI. No source
or toolchain policy was changed to make the dependency appear installed.

## Cloud preflight correction

The first isolated-head campaign run `40508212156` stopped before compilation
because source traceability was stale. Its report was regenerated with the
recorded revision label; `--check` passes while retaining 7,004 blockers.
The next campaign run `40508333094` passed source validation but stopped at
the stale runtime-acceptance source report. That report was regenerated and
independently compared with the recomputed audit; its 30 runtime failures are
still reported. The source-only release preflight now passes.

World-contract run `40508365257` caught a scenario ID literal in the shared
bootstrap. The diagnostic now compares the current map ID to the authored
selector ID, so all regional maps expose the same markers without embedding
Age of Sail content in the shared engine. The framework boundary audit passes.
The original Wurst run `40508178727` is still tied to an older diagnostic head
and must be treated separately from any final-head result. None of these
preflight corrections grants campaign publication or native acceptance.
