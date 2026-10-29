# Carvel voyage verification (#571)

This implements the independent Carvel closure gate. Generated metadata requires
the exact typed modifier and 800-basis-point voyage hull metric. Packaging checks
the executable naval recipe and consumer catalogue against fresh generation,
including rejection of tampering with recomputed output hashes. The verifier
requires complete passing pinned execution for the audited revision/source digest,
all dedicated negative/persistence tests, and weather, hull-commit and persistence
probes in the isolated registered Carvel comparison. Commissioning, repair and
combined naval traces cannot substitute for that comparison.

The comparison earns only Carvel, reserves the same provisions, pays the same
maintenance and delivers identical weather to compatible hulls: four actual
100-integrity exposures cost 368 versus 400 integrity. Tests cover the 1460 service
boundary, incompatible/unrefitted hulls, the unchanged paid 30-day refit recipe,
calm/unfunded/unprovisioned days, fractional carry across save/resume and repeated
voyages, interruption, destruction, capture, player/AI and active/inactive parity,
migration and late campaign-load rollback.

The new mid-voyage tests exposed a persistence defect: a paid hull's voyage record
precedes its profile record in existing snapshots. Support validation now runs
after detached parsing has read every profile. Existing snapshots resume without
a format change; missing or incompatible profiles still reject atomically.

`validation.json` and compressed transcripts record focused developer validation.
The pinned image mounts this worktree read-only, copies a fresh production assembly
into container-private `/tmp/naval`, installs its declared Wurst dependency there
and runs `grill test` with the pinned compiler. All production code and sibling
test functions remain compiled; only annotations outside NavalServicesTests,
NavigationEfficiencyTests and the compatibility fixture are masked. Generation
and provenance verification run before assembly. No predecessor artifact is used.

Python commands (from the scenario directory):

```sh
python3 -m unittest discover -s tests -p 'test_naval*.py'
python3 -m unittest discover -s tests -p 'test_navigation_efficiency.py'
python3 -m unittest discover -s tests -p 'test_integration_evidence.py'
python3 -m unittest discover -s tests -p 'test_wurst_execution.py'
```

The framework boundary check runs from the repository root:

```sh
python3 maps/historical-world-rpg/_shared/tooling/audit_framework_boundary.py maps/historical-world-rpg
```

These are **focused results, not closure evidence**. After integrating current
main, the validation repair regenerated all three source-only audits against
`fd929bcec2a43ac20046931d91fc0ad7c15a74cf` and source digest
`b9dabb4404a1fdb5fe80beee8d9ae392390dcc6b19169ff3759ec3648ec664f7`.
The previous release-blocker/runtime freshness failures came from retaining the
pre-integration revision, digest and execution-contract hash. No gameplay source
or findings changed in this repair. Source-only reports still retain the Carvel
blocker because focused execution cannot establish closure.

As requested, complete repository validation remains with the controller. Run
the complete pinned suite on the integrated revision, regenerate release-blocker,
runtime-acceptance and requirement-traceability reports with its fresh execution
evidence, and require this exact finding to disappear:

`RESEARCH-UNBOUND-CARVEL-HULL-CONSTRUCTION-MODIFIER-PROGRESSION-CARVEL-HULL-CONSTRUCTION`

No commits, GitHub changes or incremental player QA were performed.

Integration repair checks passed: all 26 `test_naval*.py` tests, all 12 navigation
tests, all 13 integration-evidence tests, all 23 execution-protocol tests (synthetic
fixtures, not gameplay evidence), both previously failing checked-in
release/runtime report freshness tests, the requirement-traceability `--check`,
the framework boundary audit and `git diff --check`. The three reports share the
integrated revision/source digest above. The source-only release/runtime audits
still return failure for their documented publication blockers; that status is
independent of report freshness. Grill is unavailable in this environment, so no
new pinned Wurst execution is claimed for this report-only repair.
