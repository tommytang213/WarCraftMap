# Character starting progression

The live recruitment path consumes `tooling/hero_progression_catalog.py::load_catalog()`.
Its existing historical profiles determine starting level, skill/mastery ranks
and personal-tree identity. `package.json` selects the scenario composer; the
shared packager validates its output and records the composer and all catalogue
inputs in generated provenance. Both `ScenarioData.wurst` and
`scenario-runtime.json` contain the resulting definitions. No historical identity
or starting-level formula lives in the shared Wurst runtime.

Characters outside the catalogue use their explicit `startingProgression`
definition, or the world's `level`, `skills` ratings, `masteries` ranks and
`signatureProgressionId` defaults. An unspecified start is level 1 with no ranks
or personal tree. Authored skill and mastery identifiers remain scenario data.

`HeroRoster.recruit` checks ownership, the authoritative campaign clock and the
full inclusive availability window before validating and copying a profile. The
persisted `recruited` flag protects the first grant. Neither rejection nor repeat
recruitment changes progression. Expiry of historical availability leaves
recruited authority intact. The automatic new-campaign companion uses this same
recruitment path.

Headless progression starts at cumulative `experience_for_level(startingLevel)`.
Live experience measures progress toward the next level, so that exact level
floor becomes **zero residual experience**. Starting ranks grant **zero unspent
skill, mastery or choice points**. Subsequent awards now follow the authoritative
curve and generated growth cadence described in [LIVE_HERO_GROWTH.md](LIVE_HERO_GROWTH.md).

`RpgHero.skillRank` and `masteryRank` expose live ranks; the existing signature
field owns the personal-tree identity. `/inventory HERO` shows level, experience,
points, ranks and personal tree. Equipment requirements, perk level checks and
experience rewards read the same initialized hero authority.

RPG domain schema **v4** adds skill/mastery rank maps to each hero record. Campaign
envelopes **1–8** remain compatible. Validation of every candidate record precedes
mutation; the campaign load transaction also restores prior ranks if projection
restoration fails. Travel and reconstruction carry earned progression and never
reapply starting profiles.

Migration from RPG v2/v3 preserves recorded level, experience, unspent points,
personal/signature progression, perks and ownership. Their absent rank maps become
empty; no retrospective grants are invented. The current writer uses v6, retaining
v4 ranks and v5 quest stages and appending choice points. Unrecruited
legacy records still receive the composed start on their first valid recruitment.
The empty v1 domain remains a new-campaign initialization path.

This closes the starting-profile data loss under REQ-0093.01 and contributes to
ROAD-0135. Deep progression choices/effects, broader multi-axis hero integration,
large local field performance and native Warcraft launch remain separate release
obligations. These automated checks require no player QA.
