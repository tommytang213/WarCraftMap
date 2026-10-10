"""Validate and project scenario-owned allocation definitions, not effects."""
from hero_starting_profiles import identity, index, integer


def allocation_definitions(catalog, starts):
    if catalog is None:
        catalog = {key: [] for key in ("skills", "masteries", "abilities", "perks", "personalTrees")}
        catalog["respec"] = {"supported": False}
    tables = {key: index(catalog.get(key), key) for key in
              ("skills", "masteries", "abilities", "perks", "personalTrees")}
    if catalog.get("respec", {}).get("supported") is not False:
        raise ValueError("live hero allocation does not support respecialization")

    def references(row, field, known):
        values = row.get(field, [])
        if not isinstance(values, list) or any(identity(v) not in known for v in values) or len(set(values)) != len(values):
            raise ValueError(f"invalid {field}: {row['id']}")
        return values

    for perk in tables["perks"].values():
        integer(perk.get("minimumLevel"), 1, 300, "perk minimum level")
        if identity(perk.get("abilityId")) not in tables["abilities"]:
            raise ValueError(f"unknown perk ability: {perk['id']}")
        references(perk, "prerequisitePerkIds", tables["perks"])
    visited, pending = set(), set()

    def visit(ident):
        if ident in pending:
            raise ValueError("cyclic perk prerequisites")
        if ident not in visited:
            pending.add(ident)
            for parent in tables["perks"][ident].get("prerequisitePerkIds", []):
                visit(parent)
            pending.remove(ident)
            visited.add(ident)

    for ident in tables["perks"]:
        visit(ident)
    for tree in tables["personalTrees"].values():
        nodes = references(tree, "perkIds", tables["perks"])
        if not nodes or any(not set(tables["perks"][p].get("prerequisitePerkIds", [])) <= set(nodes) for p in nodes):
            raise ValueError(f"personal tree has unreachable prerequisites: {tree['id']}")
    # Explicit starting ranks in catalogue-less reusable scenarios remain usable.
    for key, field in (("skills", "skillIds"), ("masteries", "masteryIds")):
        for ident in starts[field]:
            tables[key].setdefault(ident, {"id": ident, "name": ident.replace("_", " ")})
    for key, rows in tables.items():
        if len(rows) > 256:
            raise ValueError(f"too many allocation definitions: {key}")
    return {"respecSupported": False,
            **{key: [rows[ident] for ident in sorted(rows)] for key, rows in tables.items()}}


def allocation_wurst(definitions, escape):
    lines = []
    for key, kind in (("skills", "skill"), ("masteries", "mastery")):
        for row in definitions[key]:
            lines.append(f'\truntime.allocations.addRank("{kind}","{row["id"]}","{escape(row.get("name", row["id"]))}")')
    for row in definitions["abilities"]:
        lines.append(f'\truntime.allocations.addAbility("{row["id"]}","{escape(row.get("name", row["id"]))}")')
    for row in definitions["perks"]:
        required = "".join(f"~{p}~" for p in row.get("prerequisitePerkIds", []))
        lines.append(f'\truntime.allocations.addPerk("{row["id"]}","{row["abilityId"]}",{row["minimumLevel"]},"{required}")')
    for row in definitions["personalTrees"]:
        nodes = "".join(f"~{p}~" for p in row["perkIds"])
        lines.append(f'\truntime.allocations.addTree("{row["id"]}","{nodes}")')
    return lines
