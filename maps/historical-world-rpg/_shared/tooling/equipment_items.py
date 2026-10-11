"""Emit complete item definitions, with no inferred gameplay-stat bindings."""
import json

REQUIREMENT_LABELS = {
    "startYear": "From year", "endYear": "Through year", "regionIds": "Regions",
    "technologyIds": "Technologies", "institutionIds": "Institutions",
    "questFlagIds": "Quest flags", "eventFlagIds": "Event flags",
    "controllerIds": "Polities", "settlementIds": "Settlements", "requiredLevel": "Character level",
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def item_definitions_wurst(catalogue):
    # Unlike free-form display labels elsewhere in the generator, definition
    # strings must preserve authored newlines, quotes and backslashes exactly.
    def ws(value):
        return json.dumps(value, ensure_ascii=False)[1:-1]

    rarities = {row["id"]: row for row in catalogue.get("rarities", [])}
    lines = []
    for index, row in enumerate(catalogue.get("items", [])):
        variable = f"item{index}"
        comparison = row["comparison"]
        requirements = row["requirements"]
        provenance = row["provenance"]
        rarity = rarities[row["rarityId"]]
        # Preserve existing slot selection/eligibility semantics; retain the
        # complete authored list as definition metadata as well.
        slot = (comparison.get("slotIds") or [row["category"]])[0]
        lines.append(f'\tlet {variable}=new RpgItem("{ws(row["id"])}","{ws(row["name"])}","{ws(slot)}","{ws(row["rarityId"])}",{row["itemLevel"]})')
        strings = {
            "slotIds": canonical(comparison.get("slotIds", [])),
            "category": row["category"], "rarityName": rarity["name"],
            "setId": comparison.get("setId", ""),
            "provenance": canonical(provenance), "provenanceKind": provenance["kind"],
            "identityId": provenance.get("identityId", ""),
            "requirements": canonical(requirements),
            "requirementsText": "; ".join(f'{REQUIREMENT_LABELS.get(key, key)}: {", ".join(map(str, value)) if isinstance(value, list) else value}'
                                           for key, value in sorted(requirements.items())) or "None",
        }
        for field, value in strings.items():
            lines.append(f'\t{variable}.{field}="{ws(value)}"')
        numbers = {"rarityRank": rarity["rank"], "startYear": requirements.get("startYear", 0),
                   "endYear": requirements.get("endYear", 0), "requiredLevel": requirements.get("requiredLevel", 0),
                   "maxEnhancement": row["enhancement"]["maxRank"],
                   "maxRestoration": row["enhancement"]["maxRestoration"]}
        for field, value in numbers.items():
            lines.append(f'\t{variable}.{field}={value}')
        lines.append(f'\t{variable}.unique={str(row["unique"]).lower()}')
        for ident, value in sorted(comparison.get("majorStats", {}).items()):
            lines.append(f'\t{variable}.addStat("{ws(ident)}",{value})')
        for ident in comparison.get("effectIds", []):
            lines.append(f'\t{variable}.addEffect("{ws(ident)}")')
        for descriptor in comparison.get("conditionalEffects", []):
            lines.append(f'\t{variable}.addConditionalEffect("{ws(descriptor["id"])}","{ws(descriptor["condition"])}","{ws(canonical(descriptor))}")')
        for field, method in (("technologyIds", "Technology"), ("institutionIds", "Institution")):
            for ident in requirements.get(field, []):
                lines.append(f'\t{variable}.add{method}("{ws(ident)}")')
        lines.append(f'\truntime.inventory.registerItem({variable})')
    return lines
