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
