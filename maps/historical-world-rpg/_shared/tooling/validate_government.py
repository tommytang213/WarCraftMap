RANK_ORDER = {
    "none": 0, "knight": 1, "baron": 2, "count": 3, "marquess": 4,
    "duke": 5, "prince": 6, "king": 7, "emperor": 8,
}


def _number_in_range(value, low, high, context, fail, *, exclusive_low=False):
    valid_type = isinstance(value, (int, float)) and not isinstance(value, bool)
    low_ok = value > low if valid_type and exclusive_low else valid_type and value >= low
    if not valid_type or not low_ok or value > high:
        boundary = "greater than" if exclusive_low else "at least"
        fail(f"{context}: must be {boundary} {low} and at most {high}")


def _validate_holder(ref, context, polities, characters, fail, require_id):
    if not isinstance(ref, dict):
        fail(f"{context}: must be an object")
    kind, ident = ref.get("kind"), ref.get("id")
    require_id(ident, f"{context}.id")
    targets = {"polity": polities, "character": characters}
    if kind not in targets:
        fail(f"{context}: invalid holder kind {kind!r}")
    if ident not in targets[kind]:
        fail(f"{context}: missing {kind} {ident!r}")
    return kind, ident


def validate_allegiance_transition(current_polity_id, requested_polity_id, polities, fail):
    if current_polity_id not in polities:
        fail(f"current allegiance references missing polity {current_polity_id!r}")
    if requested_polity_id not in polities:
        fail(f"requested allegiance references missing polity {requested_polity_id!r}")
    if current_polity_id == requested_polity_id:
        fail("requested allegiance must differ from current allegiance")


def _reject_cycles(records, parent_field, label, fail):
    for start in records:
        seen = set()
        current = start
        while current is not None:
            if current in seen:
                fail(f"{label} hierarchy contains a cycle at {current!r}")
            seen.add(current)
            current = records[current].get(parent_field)


def validate_government(data, fail, require_id, unique_index, polities, provinces, settlements, characters):
    styles = unique_index(data.get("titleStyles", []), "titleStyles")
    grants = unique_index(data.get("titleGrants", []), "titleGrants")
    holdings = unique_index(data.get("territorialHoldings", []), "territorialHoldings")
    allegiances = unique_index(data.get("allegiances", []), "allegiances")

    for style_id, style in styles.items():
        domain = f"title style {style_id}"
        if style.get("polityId") not in polities:
            fail(f"{domain}: missing polity {style.get('polityId')!r}")
        tier = style.get("rankTier")
        if tier not in RANK_ORDER or tier == "none":
            fail(f"{domain}: invalid rankTier {tier!r}")
        for field in ("nativeName", "genericName"):
            if not isinstance(style.get(field), str) or not style[field].strip():
                fail(f"{domain}.{field}: must be non-empty")

    for grant_id, grant in grants.items():
        domain = f"title grant {grant_id}"
        style_id = grant.get("titleStyleId")
        if style_id not in styles:
            fail(f"{domain}: missing title style {style_id!r}")
        _validate_holder(grant.get("holder"), f"{domain}.holder", polities, characters, fail, require_id)
        if grant.get("allegiancePolityId") not in polities:
            fail(f"{domain}: missing allegiance polity {grant.get('allegiancePolityId')!r}")
        sovereign = grant.get("sovereign")
        if not isinstance(sovereign, bool):
            fail(f"{domain}.sovereign: must be boolean")
        grantor_id = grant.get("grantorTitleId")
        if sovereign and grantor_id is not None:
            fail(f"{domain}: a sovereign title cannot have a grantor")
        if not sovereign and grantor_id is None:
            fail(f"{domain}: a non-sovereign title requires a grantor")
        if grantor_id is not None:
            if grantor_id not in grants:
                fail(f"{domain}: missing grantor title {grantor_id!r}")
            child_rank = RANK_ORDER[styles[style_id]["rankTier"]]
            parent_style_id = grants[grantor_id].get("titleStyleId")
            if parent_style_id not in styles:
                fail(f"title grant {grantor_id}: missing title style {parent_style_id!r}")
            parent_rank = RANK_ORDER[styles[parent_style_id]["rankTier"]]
            if child_rank >= parent_rank:
                fail(f"{domain}: rank must be below its grantor's rank")
    _reject_cycles(grants, "grantorTitleId", "title", fail)

    seen_territories = set()
    for holding_id, holding in holdings.items():
        domain = f"territorial holding {holding_id}"
        territory = holding.get("territory")
        if not isinstance(territory, dict) or territory.get("kind") not in {"province", "settlement"}:
            fail(f"{domain}.territory: invalid territory reference")
        kind, ident = territory.get("kind"), territory.get("id")
        require_id(ident, f"{domain}.territory.id")
        targets = provinces if kind == "province" else settlements
        if ident not in targets:
            fail(f"{domain}: missing {kind} {ident!r}")
        territory_key = (kind, ident)
        if territory_key in seen_territories:
            fail(f"{domain}: duplicate territorial holding for {kind} {ident!r}")
        seen_territories.add(territory_key)
        _validate_holder(holding.get("legalOwner"), f"{domain}.legalOwner", polities, characters, fail, require_id)
        for field in ("controllerPolityId", "governingPolityId", "sovereignPolityId"):
            if holding.get(field) not in polities:
                fail(f"{domain}: {field} references missing polity {holding.get(field)!r}")
        _number_in_range(holding.get("autonomyPercent"), 0, 100, f"{domain}.autonomyPercent", fail)
        _number_in_range(holding.get("overlordTaxRatePercent"), 0, 100, f"{domain}.overlordTaxRatePercent", fail)
        _number_in_range(holding.get("upkeepRatePercent"), 0, 100, f"{domain}.upkeepRatePercent", fail, exclusive_low=True)
        overlord_id = holding.get("overlordHoldingId")
        obligations = holding.get("obligations")
        if not isinstance(obligations, list):
            fail(f"{domain}.obligations: must be an array")
        if overlord_id is None:
            if holding.get("overlordTaxRatePercent") != 0:
                fail(f"{domain}: independent holding cannot pay overlord tax")
            if obligations:
                fail(f"{domain}: independent holding cannot owe overlord obligations")
        elif overlord_id not in holdings:
            fail(f"{domain}: missing overlord holding {overlord_id!r}")
        for index, obligation in enumerate(obligations):
            odomain = f"{domain}.obligations[{index}]"
            if not isinstance(obligation, dict) or obligation.get("kind") not in {"levy", "service", "tribute", "custom"}:
                fail(f"{odomain}: invalid obligation")
            value = obligation.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                fail(f"{odomain}.value: must be a non-negative number")
            if obligation.get("kind") == "custom":
                require_id(obligation.get("contentId"), f"{odomain}.contentId")
    _reject_cycles(holdings, "overlordHoldingId", "territorial", fail)

    seen_subjects = set()
    for allegiance_id, allegiance in allegiances.items():
        domain = f"allegiance {allegiance_id}"
        subject = _validate_holder(allegiance.get("subject"), f"{domain}.subject", polities, characters, fail, require_id)
        if subject in seen_subjects:
            fail(f"{domain}: subject has more than one current allegiance")
        seen_subjects.add(subject)
        if allegiance.get("polityId") not in polities:
            fail(f"{domain}: missing polity {allegiance.get('polityId')!r}")

    return styles, grants, holdings, allegiances
