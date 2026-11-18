# Authored-catalogue soak baseline reconciliation

This is headless regression evidence, not content approval or native Warcraft acceptance.

- Reference source: `3cc55eb975812e4857ef47bccd506903201dda28`.
- Candidate source: `93718fbb133769c81b07b5aa7729c4df2ae7a467`.
- Profile: `complete_multi_century`, seeds 1450, 1588, 1701 and 1815.
- Both complete source trees were read from Git. `comparison.json` records SHA-256 and sizes for the configuration and every input.
- All historical reference states reproduce their configured golden hashes.
- Normal, accelerated and checkpoint/resume execution agree in both trees.
- All four candidate states differ only in `domains`, `fixtureHash` and `sourceCounts`; simulated progression is identical.
- Changed source inputs are `world` and `quests`. The world projection was reconciled with the authored catalogue in `54632a9`; the personal quest revisions are separately tracked source work.

The baseline update retains the full normalized-state hash, including catalogue provenance. It does not remove source fields, permit arbitrary hash mismatches or modify simulation logic. Both profiles use the corresponding newly observed hash. Their different stepping schedules remain tested for equivalent results.

Reproduce with complete checkouts:

```sh
python3 maps/historical-world-rpg/age-of-sail-world/tooling/compare_full_world_soak_states.py \
  --reference-config REFERENCE/maps/historical-world-rpg/age-of-sail-world/scenario/benchmarks/full-world-soak.json \
  --candidate-config CANDIDATE/maps/historical-world-rpg/age-of-sail-world/scenario/benchmarks/full-world-soak.json \
  --profile complete_multi_century
```

The archived candidate configuration precedes this baseline update, so `candidateGoldenMatched` is correctly false in this diagnostic. Subsequent validation must test the updated configuration. Issues #438 and #600, native campaign acceptance and all release blockers remain open.
