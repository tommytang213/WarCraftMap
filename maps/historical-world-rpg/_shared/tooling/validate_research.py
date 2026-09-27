"""Generic technology/institution graph and mutable-state validation."""


def validate(data, fail, require_id, unique_index, polity, province):
    branches = unique_index(data.get("researchBranches", []), "researchBranches")
    technologies = unique_index(data.get("technologies", []), "technologies")
    institutions = unique_index(data.get("institutions", []), "institutions")
    duplicate_ids = set(technologies) & set(institutions)
    if duplicate_ids:
        fail(f"research graph: duplicate ID {sorted(duplicate_ids)[0]!r}")
    nodes = {**technologies, **institutions}
    if nodes and not branches:
        fail("research graph: at least one branch is required")

    def references(values, domain, targets, nonempty=False):
        if not isinstance(values, list) or (nonempty and not values):
            fail(f"{domain}: must be a{' non-empty' if nonempty else 'n'} array")
        seen = set()
        for ident in values:
            require_id(ident, domain)
            if ident in seen:
                fail(f"{domain}: duplicate reference {ident!r}")
            if ident not in targets:
                fail(f"{domain}: missing reference {ident!r}")
            seen.add(ident)

    def number(value, domain, minimum, maximum=None, exclusive_maximum=False):
        invalid_max = maximum is not None and (value >= maximum if exclusive_maximum else value > maximum)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum or invalid_max:
            fail(f"{domain}: number outside allowed range")

    entry_nodes = set()
    dependents = {node_id: [] for node_id in nodes}
    for branch_id, branch in branches.items():
        entries = branch.get("entryNodeIds")
        references(entries, f"research branch {branch_id}.entryNodeIds", nodes, True)
        for node_id in entries:
            if nodes[node_id].get("branchId") != branch_id:
                fail(f"research branch {branch_id}: entry node {node_id!r} belongs to another branch")
        entry_nodes.update(entries)

    for node_id, node in nodes.items():
        domain = f"research node {node_id}"
        if node.get("branchId") not in branches:
            fail(f"{domain}: missing branch {node.get('branchId')!r}")
        prerequisites = node.get("prerequisiteIds")
        references(prerequisites, f"{domain}.prerequisiteIds", nodes)
        for prerequisite_id in prerequisites:
            dependents[prerequisite_id].append(node_id)
        cost = node.get("timeCost")
        if not isinstance(cost, dict):
            fail(f"{domain}.timeCost: must be an object")
        if isinstance(cost.get("preferredYear"), bool) or not isinstance(cost.get("preferredYear"), int):
            fail(f"{domain}.timeCost.preferredYear: must be an integer")
        number(cost.get("baseCost"), f"{domain}.timeCost.baseCost", 0)
        if cost.get("baseCost") == 0:
            fail(f"{domain}.timeCost.baseCost: must be greater than zero")
        number(cost.get("aheadOfTimeCostMultiplier"), f"{domain}.timeCost.aheadOfTimeCostMultiplier", 1)
        number(cost.get("additionalMultiplierPerYearAhead"), f"{domain}.timeCost.additionalMultiplierPerYearAhead", 0)
        if not isinstance(node.get("unlocks"), list):
            fail(f"{domain}.unlocks: must be an array")
        unlocks = set()
        for unlock in node["unlocks"]:
            if not isinstance(unlock, dict) or unlock.get("kind") not in {"unit", "building", "ability", "policy", "modifier"}:
                fail(f"{domain}: invalid unlock")
            require_id(unlock.get("contentId"), f"{domain}.unlock.contentId")
            key = (unlock["kind"], unlock["contentId"])
            if key in unlocks:
                fail(f"{domain}: duplicate unlock {key!r}")
            unlocks.add(key)

    visiting, visited = set(), set()
    def visit(node_id):
        if node_id in visiting:
            fail(f"research graph: cycle detected at {node_id!r}")
        if node_id in visited:
            return
        visiting.add(node_id)
        for prerequisite_id in nodes[node_id]["prerequisiteIds"]:
            visit(prerequisite_id)
        visiting.remove(node_id)
        visited.add(node_id)
    for node_id in nodes:
        visit(node_id)

    reachable, pending = set(entry_nodes), list(entry_nodes)
    while pending:
        for dependent_id in dependents[pending.pop()]:
            if dependent_id not in reachable and set(nodes[dependent_id]["prerequisiteIds"]) <= reachable:
                reachable.add(dependent_id)
                pending.append(dependent_id)
    if set(nodes) - reachable:
        fail(f"research graph: unreachable nodes {sorted(set(nodes) - reachable)!r}")

    polity_states = unique_index(data.get("polityResearchStates", []), "polityResearchStates")
    province_states = unique_index(data.get("provinceAdoptionStates", []), "provinceAdoptionStates")
    seen = set()
    for state_id, state in polity_states.items():
        polity_id = state.get("polityId")
        if polity_id not in polity or polity_id in seen:
            fail(f"polity research state {state_id}: invalid or duplicate polity {polity_id!r}")
        seen.add(polity_id)
        references(state.get("completedTechnologyIds"), f"polity research state {state_id}.completedTechnologyIds", technologies)
        references(state.get("establishedInstitutionIds"), f"polity research state {state_id}.establishedInstitutionIds", institutions)
        progress_ids = set()
        for progress in state.get("researchProgress", []):
            node_id = progress.get("nodeId") if isinstance(progress, dict) else None
            if node_id not in nodes or node_id in progress_ids:
                fail(f"polity research state {state_id}: invalid or duplicate node {node_id!r}")
            progress_ids.add(node_id)
            number(progress.get("progress"), f"polity research state {state_id}.{node_id}.progress", 0, 100, True)
    seen = set()
    for state_id, state in province_states.items():
        province_id = state.get("provinceId")
        if province_id not in province or province_id in seen:
            fail(f"province adoption state {state_id}: invalid or duplicate province {province_id!r}")
        seen.add(province_id)
        adoption_ids = set()
        for adoption in state.get("adoption", []):
            node_id = adoption.get("nodeId") if isinstance(adoption, dict) else None
            if node_id not in nodes or node_id in adoption_ids:
                fail(f"province adoption state {state_id}: invalid or duplicate node {node_id!r}")
            adoption_ids.add(node_id)
            number(adoption.get("level"), f"province adoption state {state_id}.{node_id}.level", 0, 100)
    return technologies, institutions
