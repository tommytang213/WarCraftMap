# Visual / Asset Pipeline

The player is not expected to create Warcraft models, textures, icons, object data, terrain, or World Editor content.

## What "objects visible in game" means

There are two separate layers:

### 1. Warcraft gameplay objects

Units, heroes, buildings, items, abilities, upgrades, destructibles and similar game objects are data definitions.

These should be generated/maintained from source wherever practical. Wurst's current object-editing tooling is specifically designed for this and exposes Warcraft asset IDs/paths so agents can create and update object definitions without manually clicking through World Editor.

Examples:

- an English Redcoat unit definition;
- a Portuguese Caravel;
- a London City Core;
- a bank/tavern/university building;
- a unique historical hero;
- an item's icon, model, stats and abilities.

This work can be handled by the development agents/Codex.

### 2. Visual art assets

The actual 3D model/texture/icon/sound is an asset, not the gameplay object definition.

Asset strategy, in order:

1. Prefer suitable built-in Warcraft III/Reforged assets where they fit.
2. Reuse stock models with safe object-level variation (scale, tint, attachment effects, animation choice, skin/model selection) when this produces acceptable historical readability.
3. Add custom textures/icons where stock art is insufficient.
4. Create/import custom 3D assets only where the game materially benefits from them.

Custom 3D art is a separate production pipeline from Wurst code. It can still be handled on the development side with scripted/agent-assisted modelling/conversion tooling, but it must be validated visually in Warcraft. The player will not be required to learn Blender, MDX tooling or World Editor.

## Source-control rules

- Imported assets belong under scenario-owned asset directories.
- Generated derivatives must be reproducible where practical.
- Keep source files for custom assets when licensing permits.
- Record source/licence/attribution for third-party assets.
- Do not silently copy assets from other custom maps.
- Built map imports are outputs; editable source assets are authoritative.

## Reuse across future timelines

Shared UI icons/effects and generic systems may live in shared assets.

Timeline-specific art belongs to the scenario. A Roman scenario should be able to replace Age-of-Sail unit/building art without changing the economy, relationship, title, save, technology-framework or city-capture code.

## Initial art direction

Early engine work should use stock placeholder assets where possible. Final art replacement is intentionally later so art production does not block simulation/system development.

Before the release candidate, placeholders that materially hurt readability or historical identity must be replaced or polished.

## Scenario visual-language source

The Europe, Africa, and Middle East–India slice is authored in
`scenario/visuals/europe-africa-middle-east-india.json`. Stable IDs describe role,
period, silhouette, team color, palette, stock model/skin, attachment set, scale,
animation, formation readability, rank distinction, and permitted fallback. The
deterministic inheritance order is archetype, regional family, polity, historical
period, then unit identity. This data changes presentation only; roster mechanics
and availability remain authoritative in `scenario/rosters/`.

`tooling/visual_language.py` validates references and historical-fit declarations,
then emits normalized date snapshots, Classic/Reforged object-data inputs, and a
labeled developer contact-sheet scene manifest under `scenario/visuals/generated/`.
Runtime code consumes generated model paths and never selects Age of Sail art in
the shared engine. Controller changes retain player team color; the compatibility
boundary selects Classic or Reforged paths. Placeholder assets name a custom-art
candidate and may not be introduced implicitly.

This is only the first regional slice. The overall country/unit visual-language
roadmap remains open until the remaining world regions are authored.

## Phase 6 catalogue authority

The pinned Warcraft III 3.0 stock surface used by this scenario is
`../../_shared/assets/warcraft-3.0-stock.json`. It is inspected from repository
runtime object IDs and pinned Blizzard game-data virtual paths, without World
Editor browsing. `scenario/visuals/historical-fit.json` is the generated,
scenario-owned historical assessment for every currently visualizable entity.
Regenerate it with `python3 tooling/build_asset_matrix.py`, then run the shared
validator to produce the deterministic reports under
`scenario/visuals/reports/`. Metadata resolution is used instead of a rendered
contact sheet because the repository toolchain does not contain a deterministic
CASC model renderer.

The completed country/unit pass is authoritative in
`scenario/visuals/country-unit-language.json`. It keeps regional families,
polity palettes, historical availability, technology progression, stock
fallbacks, and named-character production requirements in scenario data. The
shared resolver applies controller team color without erasing imported cultural
markings. `tooling/build_visual_language.py` regenerates the global snapshot and
the four stable regional preview-scene manifests; these metadata contact sheets
are used because no deterministic model renderer is available in the toolchain.

The settlement/building pass is authoritative in
`scenario/visuals/settlement-building-sets.json`. It covers every projected
stable settlement and defense layout and keeps City Cores, civilian services,
production, storage, port access, landmarks, and defenses semantically distinct.
`tooling/build_settlement_visuals.py` regenerates deterministic placement
manifests and structural regional preview scenes. Warcraft object instances are
replaceable representations derived from stable settlement/controller state.

## Custom 2D production

`scenario/visuals/custom-2d-assets.json` is the editable authority for the 16
priority-2 equipment and treasure icons where stock chest art caused a real
readability gap. The artwork is original geometric work licensed CC0-1.0; it
does not incorporate art from another map or an external collection. Run
`python3 tooling/build_custom_2d.py --check` to reproduce and validate 64 px,
straight-alpha, sRGB TGA32 command-button imports and the labelled 64/32 px
contact sheet under `_build/custom-2d/`.

The source records intended object uses, authorship, licence, attribution, and
the remaining lower-priority/model/sound/interface lanes. The generated import
manifest records source and derivative hashes, exact virtual paths, dimensions,
channels, compression and mipmap policy, byte size, and objective 32 px
transparency/contrast/clipping measurements. Folder-map assembly regenerates
these files, copies only the Warcraft imports plus their runtime manifest, and
exposes stable `kind:id` references in `custom2dAssets` within scenario runtime
data. Generated derivatives and contact sheets remain untracked build outputs.

## Audio pass

`scenario/audio/manifest.json` catalogues the stock Warcraft III 3.0 audio used
by the scenario, with fit, provenance, licence, attribution, technical metadata,
and budgets. `scenario/audio/profiles.json` owns the Age of Sail choices. Run
`python3 tooling/audio_pipeline.py --check` to validate references, loops,
loudness, imports, budgets, and machine-readable coverage/waveform summaries.
This pass uses stock audio only and therefore adds no imported archive or
decoded-audio memory cost.
