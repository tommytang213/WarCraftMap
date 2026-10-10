# Hero point allocation

Earned skill, mastery and choice points belong to each recruited character.
Use these registered commands; `/help COMMAND` also describes each action.

| Command | Behavior |
| --- | --- |
| `/progression HERO` | Inspect ranks, remaining balances, selected perks, personal-tree requirements and ability references. Opens RPG management and pauses the campaign. |
| `/improveskill HERO SKILL` | Spend one skill point for one skill rank, up to 100. |
| `/improvemastery HERO MASTERY` | Spend one mastery point for one mastery rank, up to 100. |
| `/chooseperk HERO PERK` | Spend one choice point for an unchosen personal-tree perk after its minimum level and every prerequisite are met. |
| `/rpg-close` | Close RPG management. Other management owners and a pre-existing manual pause retain their pause. |

Inspection lists stable IDs to use in actions. Successful allocation reports
the resulting ranks, selections and remaining balances. Spend actions retain an
open management session and do not open a new one on their own. Unknown or
unrecruited characters, other player slots, invalid IDs, insufficient matching
points, capped ranks, wrong trees, unmet prerequisites and repeated selections
reject before authority changes. Costs and eligibility come from generated
definitions and character authority; commands accept no overrides.
Respecialization is unavailable, as authored.

The single-player strategic roster owns progression independently of Warcraft
unit handles. Recruited reserve, remote and wounded characters can allocate;
spending neither heals a character nor changes its recovery deadline or
assignment. Starting profiles still grant no unspent points. Earned growth
continues to use the validated reward path from #449.

`hero_allocations.py` validates and generates skills, masteries, abilities,
perks, minimum levels, prerequisites and personal-tree membership into
`ScenarioData.wurst` and `scenario-runtime.json.heroAllocationDefinitions`.
Generation rejects invalid references, cycles and unreachable tree prerequisites.
Shared code contains no historical identities or scenario balance data.
Generator provenance advances to **25**.

Perk selection persists a selected ability entitlement. `hasSelectedAbility`
resolves known selected perks through their current personal tree and generated
ability references. It does not call Warcraft ability natives or apply an effect.
Ability-effect consumers remain blocked; command output states this explicitly.
Other progression axes, relationships, reward-source integrations and native
client launch remain outside allocation closure under ROAD-0051, REQ-0091.02
and REQ-0092.01. Their compound release obligations remain open.

## Persistence

The durable contract remains **RPG v6**: rank maps, selected perk IDs, personal
tree and all three balances already exist. No new durable fields, schema bump,
retrospective grants, charges or refunds are needed. Campaign envelopes and the
headless progression schema are unchanged.

Supported v2/v3 records retain their recorded levels, balances, ownership and
selections with empty missing rank maps; v4/v5 also retain ranks. Missing choice
balances remain zero through the existing v6 migration. Opaque legacy perk IDs
and personal-tree values remain recorded, without inventing definitions or
ability effects. Known already-selected perks cannot charge or select again.
The empty v1 domain keeps its existing new-campaign initialization. Reconstruction
copies allocations without calling reward, purchase or starting-profile grants.
All candidate validation precedes mutation, and the campaign transaction restores
authority and projections after reconstruction failure.

`HeroAllocationTests.wurst` and the generated `HeroAllocationVectorsTests.wurst`
earn points through the registered authored quest path, then dispatch production
allocation commands. Python generates expected success/rejection vectors from
`hero_progression.py`, including every personal tree, prerequisite order, zero
balances and rank 99-to-100. Recording adapters also cover ownership, malformed
arguments, collisions, pause nesting, accomplished starts, multiple characters,
partial investment, legacy migration, wounded reconstruction and rollback.
No player QA is required.
