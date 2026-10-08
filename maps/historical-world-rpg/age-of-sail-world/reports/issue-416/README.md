# Issue #416: abstract settlement authority

The production generator now registers every authored world settlement. Regional
physical placement is an optional refinement, not authority membership. The 33
previously omitted African and Southeast Asian settlements retain their authored
integration officials, goods, services and storage profiles. All 827 settlements
have live authority and market identities.

Capture eligibility and military projection are independent. The 33 abstract
settlements retain authoritative cores without permanent military objects; the 35
non-capturable communities retain their governance exceptions. Local interaction
anchors already used by the map materializer authorize services through the
existing physical actor, discovery, war, ownership and capacity checks. Repeated
reconstruction creates no abstract military objects or duplicate offices/stores.

Military domain v4 retains policy and migrates v1–v3 by registering absent
settlements from definitions while retaining existing mutable records. Current
snapshots missing configured settlement/office authority reject. Trade domain v3
adds discovery persistence and initializes missing catalogue records from immutable
defaults before applying saved balances, preserving additive store registration.
Campaign envelopes remain version 8 with schemas 1–8 supported.

The settlements census reads actual compiled authority registrations. Its separate
projection-policy comparison reads arguments to the consumed compiled policy
function and compares them with authored capture/governance/representation data.
The markets census also reads compiled registrations. Scoped mappings cover
REQ-0181.01 and REQ-0181.02; unrelated census and integration blockers remain.

Run the exact-artifact verifier after the diagnostic build:

```sh
python3 reports/issue-416/verify-evidence.py \
  --artifact _build/release/AgeOfSailWorldCampaign.w3n \
  --execution-dir _build/wurst-tests --output-dir _build/issue416-evidence
```

Validation evidence is recorded in `validation.json` and compressed logs. The
pinned compiler runs as `wurstuser`, with the worktree mounted read-only and all
builds in container-private `/tmp`. An isolated Python runtime and the recorded
WurstStdlib2 revision supply offline dependencies; Grill supplies its bundled
Warcraft 3.0 core JASS. No global tools or services are installed.

The final run passes all 335 Wurst tests and both scoped requirements. All 17
diagnostic maps were typechecked and built; each of the 16 regional scripts
contains all 827 settlement IDs in authority, markets and projection policies. The
original and content-mutated framework campaigns each pass two Wurst tests and
build three maps, with all 158 shared source hashes unchanged. Python validation
covers 928 current cases through the full run and corrected module reruns, plus
129 automation tests. `validation.json` records the initial failures and reruns.

The final audit-pattern and test-registration corrections leave all 1,734
packaged production/generation input hashes unchanged; see
`artifact-provenance.json`. The exact-artifact comparison resolves 43 scoped
blockers and retains every unrelated finding: 56 failing catalogues and 8,920
publication blockers remain. `scoped-evidence.json` enumerates all 33 restored
abstract IDs and the independently checked projection policies.

The W3N and embedded W3X files are diagnostic artifacts. Release status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`. No player QA, retail-client
execution, commits, pushes, or GitHub changes are claimed.
