# Issue 527 implementation verification

Chemical Classification now supplies a separate 400-bp source to funded,
qualified scientific observations. The production work ledger commits 104 work
per day versus 100 in an identical control, and commits the completed technology
in 87 funded days versus 90. Calculus composes additively at 900 bp. The precise
activity, input, staff, cap and persistence contract is in
[CHEMICAL_CLASSIFICATION.md](../../docs/CHEMICAL_CLASSIFICATION.md).

- **Pinned Wurst typecheck and 61/61 real interpreter tests passed.** Packages:
  ScienceExplorationTests, ResearchRuntimeTests, ResearchCostTests,
  CampaignLoadTransactionTests and FrameworkConformanceTests. The compiler JAR
  SHA-256 is `1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.
  `focused-results.json` records cases, production probes, source identity and
  all input hashes; `focused-wurst.log.gz` preserves the real transcript.
- **168 Python tests passed:** science/research/save (41), economy simulations
  (18), framework conformance (9), packaging/definition checks (12), and audit
  regressions (88). Raw transcripts are retained as compressed logs. The
  framework/packaging tests' printed 683-case summaries use synthetic compiler
  fixtures and are not additional real Wurst execution evidence.
- All three official JSON reports were regenerated for this source identity:
  release-blocker, runtime-acceptance and requirement-traceability. Compressed
  source-audit snapshots and their index are retained here. They remain failed
  because complete-suite and packaged-campaign evidence belong to controller
  validation. This is not a blocker-closure or native-client acceptance claim.

The five new interpreter cases cover registered research followed by actual
scientific work and durable completion; absent equipment, staff and inputs;
missing technology and denied control; ordinary targets without the bonus;
additive named sources and their cap; exact fractional carry and duplicate grants;
early research at the full authored historical price; player/AI and active/abstract
parity; capture; successful resume; malformed restore; and late campaign-load
rollback of work, fractions, treasury, stock and earned effects. Existing science
migration and Calculus tests also pass. No persistence fields were added.

`validation.json` identifies the tested revision and dirty source tree. No
commit, push, GitHub mutation, global tooling change or player QA was performed.
The controller must run full repository validation and regenerate the official
reports on the integrated/main revision before claiming closure.

To reproduce, run `prepare-focused.py PATH_TO_CACHED_WURST_STDLIB_SOURCE` from the
scenario directory. It uses normal generation, definition verification and
assembly, removing only unselected test annotations in the disposable assembly.
The cached library is upstream source used as a compiler dependency; no
predecessor implementation, compiled artifact or execution report is reused.
Run the pinned image
`frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`
with networking disabled and `_build/issue-527/compile` mounted read-only at
`/source`. The image's default `wurstuser` (UID/GID 1001) must copy `/source` to
container-private `/tmp/chemical-validation` before running:

```sh
cd /tmp/chemical-validation
sha256sum /home/wurstuser/.wurst/wurst-compiler/wurstscript.jar
sha256sum -c inputs.sha256
grill typecheck
grill test
sha256sum -c inputs.sha256
```

No container wrote to this worktree or changed its ownership or permissions.
`record-focused.py` validates the transcript and both hash checks before recording
focused results. `record-audits.py` regenerates the three compressed source-audit
snapshots without treating focused execution as full-suite evidence.
