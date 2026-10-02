#!/usr/bin/env python3
"""Build the deterministic release-scale military catalogue.

The generated slice is scenario authority.  This recipe keeps the deliberately
regular global coverage reviewable without moving names or balance into code.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scenario/rosters/release-military-breadth.json"

REGIONS = {
    "europe": ("European", "scenario/politics/europe-1450.json"),
    "africa": ("African", "scenario/politics/africa-1450.json"),
    "middle_east_india": ("West and South Asian", "scenario/politics/middle-east-india-1450.json"),
    "southeast_asia": ("Southeast Asian", "scenario/politics/southeast-asia-1450.json"),
    "east_asia": ("East Asian", "scenario/politics/east-asia-1450.json"),
    "americas_caribbean": ("American and Caribbean", "scenario/politics/americas-caribbean-1450.json"),
    "pacific": ("Pacific", "scenario/politics/pacific-1450.json"),
}
ERAS = (
    ("late_medieval", "Late Medieval", 1450, 1549, None),
    ("gunpowder", "Gunpowder", 1550, 1649, "pike_and_shot"),
    ("professional", "Professional", 1650, 1749, "flintlock_drill"),
    ("linear", "Linear", 1750, 1799, "linear_tactics"),
    ("revolutionary", "Revolutionary", 1800, 1820, "mass_army_logistics"),
)
LAND_ROLES = (
    ("line", "Line Infantry", "infantry", "foot", "foot_company_runtime", "matchlock", "close_order", ("ordered_ranks", "volley_fire"), ("infantry", "firearm")),
    ("militia", "Militia Muster", "infantry", "foot", "foot_company_runtime", "polearm", "close_order", ("militia_muster", "rallying_presence"), ("infantry", "militia")),
    ("guard", "Guard Battalion", "infantry", "foot", "foot_company_runtime", "matchlock", "close_order", ("steady_drill", "rallying_presence"), ("infantry", "garrison")),
    ("ranger", "Ranger Company", "specialist", "foot", "specialist_runtime", "matchlock", "loose_order", ("forest_screen", "forced_march"), ("ranged", "specialist")),
    ("horse", "Mounted Regiment", "cavalry", "mounted", "mounted_company_runtime", "sabre", "mounted_wedge", ("cavalry_shock", "forced_march"), ("cavalry", "specialist")),
    ("battery", "Artillery Battery", "artillery", "wheeled", "gun_battery_runtime", "field_cannon", "gun_battery", ("field_siege", "counter_battery"), ("artillery", "siege")),
    ("engineers", "Engineer Corps", "specialist", "foot", "specialist_runtime", "matchlock", "loose_order", ("field_repair", "sapping"), ("engineer", "siege", "specialist")),
    ("marines", "Marine Company", "marine", "foot", "foot_company_runtime", "boarding_arms", "close_order", ("amphibious_assault", "boarding_action"), ("marine", "specialist")),
)
NAVAL_ROLES = (
    ("service", "Service Vessel", "transport", "coastal_sail", "small_ship_runtime", "unarmed_cargo", ("cargo_capacity", "shallow_draft")),
    ("fighting", "Fighting Vessel", "warship", "ocean_sail", "large_ship_runtime", "naval_guns", ("broadside", "boarding_action")),
)


def build():
    abilities = [
        {"id": "regional_adaptation", "mechanic": "terrain", "compatibleCategories": ["infantry", "cavalry", "artillery", "specialist", "marine", "transport", "merchant", "warship"]},
        {"id": "era_logistics", "mechanic": "logistics", "compatibleCategories": ["infantry", "cavalry", "artillery", "specialist", "marine", "transport", "merchant", "warship"]},
    ]
    for region in REGIONS:
        abilities.append({"id": f"{region}_operating_practice", "mechanic": "terrain", "compatibleCategories": ["infantry", "cavalry", "artillery", "specialist", "marine", "transport", "merchant", "warship"]})
    for era_id, _, _, _, _ in ERAS:
        abilities.append({"id": f"{era_id}_service_doctrine", "mechanic": "discipline", "compatibleCategories": ["infantry", "cavalry", "artillery", "specialist", "marine", "transport", "merchant", "warship"]})
    hulls, archetypes, assignments = [], [], []
    evidence_support = []
    region_units = {region: [] for region in REGIONS}
    for region_index, (region, (adjective, polity_source)) in enumerate(REGIONS.items()):
        polities = [p["id"] for p in json.loads((ROOT / polity_source).read_text())["polities"]]
        for era_index, (era_id, era_name, start, end, technology) in enumerate(ERAS):
            for role_index, (role_id, role_name, category, movement, template, weapon, formation, role_abilities, roles) in enumerate(LAND_ROLES):
                # Do not manufacture pre-contact mounted/gun formations merely
                # to make the regional matrix rectangular.
                if region == "pacific" and role_id in {"horse", "battery"} and era_id != "revolutionary":
                    continue
                if region == "americas_caribbean" and era_id == "late_medieval" and role_id in {"horse", "battery"}:
                    continue
                ident = f"release_{region}_{era_id}_{role_id}"
                layer = "elite" if role_id == "guard" else "regional"
                abilities_for_unit = [*role_abilities, "regional_adaptation", "era_logistics", f"{region}_operating_practice", f"{era_id}_service_doctrine"]
                row = {
                    "id": ident, "extends": "ordinary_land_base", "name": f"{adjective} {era_name} {role_name}",
                    "category": category, "rosterLayer": layer, "roleIds": list(roles), "movementClassId": movement,
                    "weaponIds": ["polearm" if era_id == "late_medieval" and category == "infantry" else weapon], "armorIds": ["riding_coat" if category == "cavalry" else "cloth_uniform"],
                    "abilityIds": abilities_for_unit, "formationIds": [formation], "runtimeTemplateId": template,
                    "strategicStrength": 330 + era_index * 92 + role_index * 13 + region_index * 3,
                    "cost": 95 + era_index * 38 + role_index * 17 + region_index, "upkeep": 7 + era_index * 4 + role_index,
                    "supply": 7 + role_index * 2 + era_index, "technologyIds": [technology] if technology else [],
                    "availability": {"historicalStartYear": start, "historicalEndYear": end,
                        "earlyAccessTechnologyIds": [technology] if technology else [], "earlyAccessYear": max(1450, start - (30 if technology else 0))},
                }
                if role_id == "battery": row["resourceIds"] = ["gunpowder", "iron"]
                if role_id == "horse": row["resourceIds"] = ["horses"]
                archetypes.append(row); region_units[region].append(ident); evidence_support.append(ident)
            for role_index, (role_id, role_name, category, movement, template, weapon, role_abilities) in enumerate(NAVAL_ROLES):
                ident = f"release_{region}_{era_id}_{role_id}"
                hull_id = f"release_{region}_{era_id}_{role_id}_hull"
                hulls.append({"id": hull_id, "category": category, "crewStrength": 28 + era_index * 32 + role_index * 90 + region_index})
                row = {
                    "id": ident, "name": f"{adjective} {era_name} {role_name}", "category": category,
                    "movementClassId": "coastal_sail" if era_id == "late_medieval" else movement,
                    "weaponIds": ["boarding_arms" if role_id == "fighting" and era_id == "late_medieval" else weapon], "armorIds": ["timber_hull"],
                    "abilityIds": [*role_abilities, "regional_adaptation", "era_logistics", f"{region}_operating_practice", f"{era_id}_service_doctrine"], "formationIds": [], "shipId": hull_id,
                    "strategicStrength": 125 + era_index * 115 + role_index * 260 + region_index * 4,
                    "runtimeTemplateId": template, "cost": 210 + era_index * 125 + role_index * 390 + region_index * 2,
                    "upkeep": 11 + era_index * 9 + role_index * 24, "supply": 13 + era_index * 8 + role_index * 22,
                    "availability": {"historicalStartYear": start, "historicalEndYear": end,
                        "earlyAccessTechnologyIds": [technology] if technology else [], "earlyAccessYear": max(1450, start - (30 if technology else 0))},
                    "upgradeToIds": [], "replacementIds": [], "militaryTraditionIds": ["sailing_naval_practice"],
                    "technologyIds": [technology] if technology else [], "countryId": None, "portRequired": role_id == "fighting",
                }
                archetypes.append(row); region_units[region].append(ident); evidence_support.append(ident)
        assignments.append({"polityIds": polities, "archetypeIds": region_units[region]})
    # Explicit, acyclic era replacement lineages. Old IDs remain loadable.
    by_id = {row["id"]: row for row in archetypes}
    for region in REGIONS:
        for role in [x[0] for x in LAND_ROLES] + [x[0] for x in NAVAL_ROLES]:
            lineage = [f"release_{region}_{era[0]}_{role}" for era in ERAS if f"release_{region}_{era[0]}_{role}" in by_id]
            for old, new in zip(lineage, lineage[1:]):
                by_id[old]["upgradeToIds"] = [new]; by_id[old]["replacementIds"] = [new]
    data = {
        "format": "age_of_sail_roster_slice_v1", "phase": "release_military_breadth",
        "abilities": abilities, "weapons": [], "armor": [], "formations": [], "ships": hulls,
        "equipment": [], "reforms": [], "resources": [], "archetypes": archetypes, "assignments": assignments,
        "historicalEvidence": [
            {"id": "release_global_land_breadth", "citation": "Jeremy Black, European Warfare, 1494-1660 (2002); John Thornton, Warfare in Atlantic Africa, 1500-1800 (1999); Kaushik Roy, Military Manpower, Armies and Warfare in South Asia (2015).", "note": "Supports regionally adapted militia, guards, cavalry, firearm, siege, engineer and professional formations across the campaign.", "supports": evidence_support[:280]},
            {"id": "release_global_maritime_breadth", "citation": "Lincoln Paine, The Sea and Civilization (2013); N. A. M. Rodger, The Command of the Ocean (2004).", "note": "Supports changing regional service craft and fighting vessels, port requirements, logistics, boarding and gunnery roles.", "supports": evidence_support[280:]},
        ],
        "coverage": {"regions": list(REGIONS), "snapshotYears": [1450, 1550, 1650, 1750, 1820], "playerFacingTarget": {"minimum": 350, "aspirational": 500}},
    }
    OUT.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    build()
