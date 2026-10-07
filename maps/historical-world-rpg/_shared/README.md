# Reusable gameplay framework

The content-only [Reed and Stone campaign](../conformance-campaign/README.md)
is an executable boundary contract for the architecture in
[DESIGN_LOCK.md](../age-of-sail-world/docs/DESIGN_LOCK.md). It is a deliberately
small invented test setting, not another game or a historical design proposal.

| Layer | Authority and responsibility |
| --- | --- |
| `_shared/engine/` | Scenario-neutral headless mechanisms, simulations and persistence contracts. |
| `_shared/wurst/` | Production campaign registration, gameplay authorities, UI and Warcraft adapters. Object handles are reconstructible projections. |
| `_shared/wurst-bootstrap/` | The common minimal origin selector and native campaign handoff. |
| `_shared/contracts/` | Versioned data and persistence shapes. |
| `_shared/tooling/` | Catalogue-to-Wurst generation, terrain/pathing materialization, pinned compiler gate, W3X and W3N packaging and inspection. |
| `_shared/wurst-tests/` | Common production-adapter conformance contract and recorded native ports. |
| `<campaign>/scenario/` | Polities, settlements, goods, characters, quests, dates/events, terrain, inventory and presentation content. |
| `<campaign>/package.json`, `physical-maps.json` | Catalogue paths, physical assignments, release identity and cache namespace. |
| `<campaign>/conformance.json` | Stable IDs selecting representative authored records for the same tests. No mechanism implementations. |

Age of Sail's former `wurst/` and selector source paths are symlink aliases to
the canonical shared packages so existing source audits and developer links keep
working. They contain no private implementation. Assembly rejects a different
implementation under a shared package name. The alternate campaign contains no
Wurst or Python source and does not import Age of Sail. The two projects share
only the neutral editor container layout; their terrain, pathing and physical
objects are generated from their own terrain and placement inputs.

`package.json` explicitly supplies settlement/geography pairs, polity catalogues,
optional RPG catalogues, initially known regions and the save-cache filename.
`ScenarioData` and `ScenarioSettings` are generated interfaces. Physical-to-logical
map mappings come from the campaign manifest. There is no setting switch in the
runtime. Age of Sail retains `AgeOfSailCampaign.w3v` and save schemas 1–7; this
change does not change saved authority or require a save migration. Inventory validation receives commodity IDs from the scenario goods catalogue
instead of a historical commodity blacklist; the item data schema is unchanged.

Run the boundary audit from the repository root:

```sh
python3 maps/historical-world-rpg/_shared/tooling/audit_framework_boundary.py
```

The audit derives IDs and names from both campaigns and their content mutation
rules, includes legacy namespace aliases declared in `framework-scenarios.json`,
checks executable Python and Wurst strings/identifiers (including escaped and
adjacent Python literals), rejects scenario
runtime forks and content-only campaign scripts, and detects substantial copied
blocks even in renamed files with added imports.
Comments and docstrings are documentation, not executable dependencies. Exact
token exceptions in `contracts/framework-boundary-exceptions.json` distinguish
homonyms such as the Python `split` operation from the settlement Split, and
Warcraft's native gold resource from the commodity. Exceptions cannot exempt a
whole module or every use of a name. Static copy detection is a regression guard,
not a proof against arbitrary semantic rewrites; the no-code fixture rule and
shared production execution contract provide the other checks.

Legacy content format names remain at scenario call sites. The shared visual
resolver and audio validator accept an explicit format identifier, so existing
Age of Sail catalogues keep their schema while new consumers use neutral formats.

The common Wurst contract executes generated registration and origin handoff,
physical RPG interaction, inventory grant, conserved trade/cargo, conflict-driven
settlement control, time/event delivery, transactional save/load, and a physical
map checkpoint followed by reconstruction in a new runtime. Only native storage,
pathing, unit observations and presentation are recorded. After full production
registration it retains a bounded subset of authored records to stay within the
pinned interpreter's 20-second per-test deadline. The full catalogues still pass
the existing generation, contract and scale tests.

CI and `automation/run_checks.sh` run the audit, all Python tests, the complete
Age of Sail Wurst suite including the common contract, and pinned fixture builds.
`validate_framework_fixture.py` packages both the original and an ID/price-mutated
fixture through `build_campaign`, including the same compiler execution gate,
each map's typecheck/build, binary inspections and final campaign inspection.
The shared runtime contract checks the selected inventory item, the commodity's
authored base price and conservation of currency through the purchase, including
the mutated prices. Both consumers pin the same compiler options in `wurst_run.args`.
Validation verifies unchanged framework hashes and writes `_build/conformance-report.json`.
Mutation inputs and compiler evidence remain under the fixture's `_build/mutation/`.
Headless packaging tests use an explicitly synthetic compiler for orchestration;
they do not stand in for pinned Wurst execution or native Warcraft gameplay.
