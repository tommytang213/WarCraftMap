#!/usr/bin/env python3
"""Deterministic, scenario-configured Warcraft folder-map build pipeline."""
from __future__ import annotations
import calendar, hashlib, json, re, shutil, subprocess, sys, zipfile
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from wurst_execution import WurstExecutionError, execute_tests, source_revision

class PackagingError(RuntimeError): pass
GENERATOR_VERSION = 14
GENERATED_WURST, GENERATED_DATA, PROVENANCE = "ScenarioData.wurst", "scenario-runtime.json", "provenance.json"

@dataclass(frozen=True)
class BuildConfig:
    project: Path; config_path: Path; source_map: Path; manifest: Path; wurst_source: Path
    scenario_file: Path; scenario_validator: Path; output: Path; output_stem: str
    package_name: str; metadata: dict[str, str]; bootstrap_markers: tuple[str, ...]
    regional_terrain: tuple[tuple[str, Path], ...]
    custom_2d_source: Path | None; custom_2d_builder: Path | None

def _inside(root: Path, value: object, label: str, boundary: Path | None = None) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise PackagingError(f"configuration: {label} must be a non-empty relative path")
    path = (root / value).resolve()
    try: path.relative_to((boundary or root).resolve())
    except ValueError as error: raise PackagingError(f"configuration: {label} escapes the project directory") from error
    return path

def load_config(config_path: Path) -> BuildConfig:
    config_path = config_path.resolve()
    try: raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise PackagingError(f"configuration: cannot read {config_path}: {error}") from error
    if raw.get("formatVersion") != 2: raise PackagingError("configuration: formatVersion must be 2")
    project = _inside(config_path.parent, raw.get("projectRoot", "."), "projectRoot")
    release, scenario = raw.get("release"), raw.get("scenario")
    if not isinstance(release, dict) or not isinstance(scenario, dict): raise PackagingError("configuration: release and scenario metadata are required")
    stem, package_name = release.get("fileName"), scenario.get("wurstPackage")
    if not isinstance(stem, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", stem): raise PackagingError("configuration: release.fileName is unsafe")
    if not isinstance(package_name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", package_name): raise PackagingError("configuration: scenario.wurstPackage is invalid")
    markers, metadata = release.get("bootstrapMarkers"), release.get("metadata")
    if not isinstance(markers, list) or not markers or not all(isinstance(x, str) and x for x in markers): raise PackagingError("configuration: release.bootstrapMarkers must be a non-empty string list")
    if not isinstance(metadata, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()): raise PackagingError("configuration: release.metadata must contain strings")
    terrain = scenario.get("regionalTerrain", [])
    if not isinstance(terrain, list) or any(not isinstance(item, dict) for item in terrain): raise PackagingError("configuration: scenario.regionalTerrain must be an array")
    terrain_entries = []
    for item in terrain:
        terrain_id = item.get("id")
        if not isinstance(terrain_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", terrain_id): raise PackagingError("configuration: regional terrain id is invalid")
        terrain_entries.append((terrain_id, _inside(project, item.get("source"), f"regionalTerrain {terrain_id}.source")))
    if len({item[0] for item in terrain_entries}) != len(terrain_entries): raise PackagingError("configuration: regional terrain ids must be unique")
    custom = scenario.get("custom2d")
    if custom is not None and (not isinstance(custom, dict) or set(custom) != {"source", "builder"}):
        raise PackagingError("configuration: scenario.custom2d must contain source and builder")
    custom_source = _inside(project, custom["source"], "scenario.custom2d.source") if custom else None
    custom_builder = _inside(project, custom["builder"], "scenario.custom2d.builder") if custom else None
    return BuildConfig(project, config_path, _inside(project, raw.get("sourceMap"), "sourceMap"), _inside(project, raw.get("sourceManifest"), "sourceManifest"), _inside(project, raw.get("wurstSource"), "wurstSource"), _inside(project, scenario.get("data"), "scenario.data"), _inside(project, scenario.get("validator"), "scenario.validator", project.parent), _inside(project, raw.get("outputDirectory", "_build/release"), "outputDirectory") / f"{stem}.w3x", stem, package_name, metadata, tuple(markers), tuple(terrain_entries), custom_source, custom_builder)

def _fail(stage: str, message: object) -> PackagingError: return PackagingError(f"{stage} stage failed: {message}")
def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def _load_settlement_runtime_data(config: BuildConfig, world: dict) -> list[dict]:
    """Join world identity/control to authoritative regional physical placement."""
    world_by_id = {row["id"]: row for row in world.get("settlements", [])}
    integration_path = config.project / "scenario/integration/release-scale-settlements.json"
    integration = json.loads(integration_path.read_text(encoding="utf-8")) if integration_path.is_file() else {"settlements": []}
    integration_by_id = {row["settlementId"]: row for row in integration.get("settlements", [])}
    playable_ids = {row["settlementId"] for row in integration.get("settlements", [])
        if row.get("gameplayRoles", {}).get("physicalMap", {}).get("modelId") != "abstract_regional_projection"}
    if not integration_by_id:
        playable_ids = set(world_by_id)
    result = []
    for path in sorted((config.project / "scenario/settlements").glob("*-1450.json")):
        source = json.loads(path.read_text(encoding="utf-8"))
        stem = path.name.removesuffix("-1450.json")
        geography_path = next((item for item in (
            config.project / f"scenario/geography/{stem.replace('-', '_')}.json",
            config.project / f"scenario/geography/{stem}.json",
        ) if item.is_file()), None)
        if geography_path is None:
            raise PackagingError(f"generation: no geography authority for {path.name}")
        geography = json.loads(geography_path.read_text(encoding="utf-8"))
        instances = {row["id"]: row for row in geography.get("instances", [])}
        for authored in source.get("settlements", []):
            authoritative = world_by_id.get(authored["id"])
            if authoritative is None or authored["id"] not in playable_ids:
                continue
            position = authored.get("position") or authored.get("localPosition")
            if isinstance(position, dict): position = [position["x"], position["y"]]
            if position is None:
                transform = instances.get(authored["regionalInstanceId"], {}).get("transform", {})
                origin, scale = transform.get("sourceOrigin"), transform.get("scale")
                source_position, offset = authored.get("sourcePosition"), transform.get("offset", [0, 0])
                if not source_position or not origin or not scale:
                    raise PackagingError(f"generation: settlement {authored['id']} has no resolvable position")
                position = [(source_position[i] - origin[i]) * scale[i] + offset[i] for i in range(2)]
            defense = authored.get("defenseClass", authoritative.get("kind", "town"))
            strength = {"capital": 40, "fortified": 32, "fort": 32, "port": 24}.get(defense, 20)
            result.append({"id": authored["id"], "controllerId": authoritative["controllerPolityId"],
                "regionId": authored.get("physicalMapId", authored["regionalInstanceId"]),
                "x": round(float(position[0]) * 128.0, 3), "y": round(float(position[1]) * 128.0, 3),
                "strength": strength, "reserves": strength * 2, "manpower": strength * 4, "supply": strength * 3,
                "official": integration_by_id.get(authored["id"], {}).get("official", {
                    "characterId": "official_" + authored["id"], "displayName": "Local Council"})})
    missing = playable_ids - {row["id"] for row in result}
    if missing:
        raise PackagingError("generation: playable settlements lack runtime placement: " + ", ".join(sorted(missing)[:10]))
    if world_by_id and not result:
        raise PackagingError("generation: scenario contains settlements but generated Wurst would register zero settlements")
    return sorted(result, key=lambda row: row["id"])

def _load_country_interaction_runtime_data(config: BuildConfig, world: dict) -> dict:
    """Join the campaign authorities used by the headless polity systems.

    This is deliberately a join, not a second set of gameplay defaults.  Money
    and stock come from economy stores, wars from regional politics, and the
    shape/capacity of government rewards from current territory and research.
    """
    polity_ids = {row["id"] for row in world.get("polities", [])}
    settlements = {row["id"]: row["controllerPolityId"] for row in world.get("settlements", [])}
    economy_path = config.project / "scenario/economy/economy.json"
    economy = json.loads(economy_path.read_text(encoding="utf-8")) if economy_path.is_file() else {"catalog": {"stores": []}, "state": {"storeBalances": []}}
    store_owners = {}
    for store in economy.get("catalog", {}).get("stores", []):
        owner = store.get("owner", {})
        if owner.get("kind") == "settlement" and owner.get("id") in settlements:
            store_owners[store["id"]] = settlements[owner["id"]]
    treasury = {polity_id: 0 for polity_id in polity_ids}
    stock = {polity_id: 0 for polity_id in polity_ids}
    for balance in economy.get("state", {}).get("storeBalances", []):
        polity_id = store_owners.get(balance.get("storeId"))
        if polity_id:
            treasury[polity_id] += sum(int(row.get("amountMinor", 0)) for row in balance.get("currencies", []))
            stock[polity_id] += sum(int(row.get("quantityUnits", 0)) for row in balance.get("goods", []))
    holdings = world.get("territorialHoldings", [])
    territory_count = {polity_id: 0 for polity_id in polity_ids}
    for holding in holdings:
        owner = holding.get("legalOwner", {})
        if owner.get("kind") == "polity" and owner.get("id") in territory_count:
            territory_count[owner["id"]] += 1
    research = {row["polityId"]: row for row in world.get("polityResearchStates", [])}
    conflicts = []
    politics_paths = sorted((config.project / "scenario/politics").glob("*-1450.json"))
    for path in politics_paths:
        source = json.loads(path.read_text(encoding="utf-8"))
        for conflict in source.get("activeConflicts", []):
            parties = list(conflict.get("attackerPolityIds", [])) + list(conflict.get("defenderPolityIds", []))
            if all(party in polity_ids for party in parties):
                conflicts.append({"id": conflict["id"], "parties": parties})
    polities = []
    for polity in world.get("polities", []):
        polity_id = polity["id"]
        state = research.get(polity_id, {})
        # This contract is derived exclusively from live authorities.  It gives
        # every government a service reward whose cost scales with its actual
        # liquid economy, while institutional governments can also commission
        # offices.  Values are materialised so Warcraft and headless runs share
        # deterministic inputs rather than UI-only zeroes.
        rewards = [{"id": "service_stipend", "kind": "money", "threshold": 20,
                    "reputation": 0, "treasuryCost": max(1, min(240, treasury[polity_id] // 20)),
                    "foreignService": True}]
        if state.get("establishedInstitutionIds") or polity.get("sovereignTier") not in (None, "none"):
            rewards.append({"id": "government_commission", "kind": "office", "threshold": 60,
                            "reputation": 10, "treasuryCost": max(0, min(120, treasury[polity_id] // 50)),
                            "foreignService": False})
        polities.append({"id": polity_id, "treasury": treasury[polity_id], "stock": stock[polity_id],
                         "territoryCount": territory_count[polity_id], "rewards": rewards,
                         "technologies": state.get("completedTechnologyIds", []),
                         "institutions": state.get("establishedInstitutionIds", [])})
    if polity_ids and not any(row["rewards"] for row in polities):
        raise PackagingError("generation: authoritative country rewards produced zero runtime profiles")
    return {"polities": polities, "conflicts": conflicts,
            "sources": [economy_path, *politics_paths]}

def validate_inputs(config: BuildConfig, grill: str | None = None) -> str:
    required = {"source map folder": config.source_map, "source manifest": config.manifest, "Wurst source folder": config.wurst_source, "scenario data": config.scenario_file, "scenario validator": config.scenario_validator, "wurst.build": config.project / "wurst.build"}
    missing = [f"{label} ({path})" for label, path in required.items() if not path.exists()]
    missing.extend(f"regional terrain {terrain_id} ({path})" for terrain_id, path in config.regional_terrain if not path.is_file())
    if config.custom_2d_source and not config.custom_2d_source.is_file(): missing.append(f"custom 2D source ({config.custom_2d_source})")
    if config.custom_2d_builder and not config.custom_2d_builder.is_file(): missing.append(f"custom 2D builder ({config.custom_2d_builder})")
    if missing: raise _fail("inputs", "missing " + ", ".join(missing))
    build_text = (config.project / "wurst.build").read_text(encoding="utf-8")
    for setting in ("scriptMode: LUA", "wc3Patch: v3.0", f"fileName: {config.output_stem}"):
        if setting not in build_text: raise _fail("inputs", f"wurst.build must contain {setting!r}")
    try: manifest_metadata = json.loads(config.manifest.read_text(encoding="utf-8")).get("metadata")
    except (OSError, json.JSONDecodeError) as error: raise _fail("inputs", f"invalid source manifest: {error}") from error
    if manifest_metadata != config.metadata: raise _fail("inputs", "release metadata differs from the authoritative source manifest")
    executable = grill or shutil.which("grill")
    if not executable: raise _fail("inputs", "required tool 'grill' was not found on PATH")
    return str(Path(executable).resolve())

def validate_scenario(config: BuildConfig) -> None:
    result = subprocess.run([sys.executable, str(config.scenario_validator), str(config.scenario_file)], cwd=config.project, text=True, capture_output=True)
    if result.returncode: raise _fail("scenario validation", (result.stderr or result.stdout).strip() or f"validator exited {result.returncode}")

def generate(config: BuildConfig, generated: Path) -> None:
    try: world = json.loads(config.scenario_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise _fail("generation", error) from error
    generated.mkdir(parents=True, exist_ok=True)
    if config.custom_2d_builder:
        result=subprocess.run([sys.executable,str(config.custom_2d_builder),"--output",str(generated/"custom-2d"),"--check"],cwd=config.project,text=True,capture_output=True)
        if result.returncode: raise _fail("custom 2D generation", (result.stderr or result.stdout).strip())
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_regional_terrain import canonical_bytes, generate as generate_terrain
    terrain_outputs = {}
    terrain_authorities = []
    for terrain_id, terrain_path in config.regional_terrain:
        try:
            terrain_source = json.loads(terrain_path.read_text(encoding="utf-8"))
            authority = None
            if terrain_source.get("authority"):
                authority_path = _inside(config.project, terrain_source["authority"], f"regionalTerrain {terrain_id}.authority")
                authority = json.loads(authority_path.read_text(encoding="utf-8")); terrain_authorities.append(authority_path)
            terrain = generate_terrain(terrain_source, world["regionalGeography"], authority)
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
            raise _fail("terrain generation", f"{terrain_id}: {error}") from error
        output_name = f"terrain-{terrain_id}.json"
        (generated / output_name).write_bytes(canonical_bytes(terrain))
        terrain_outputs[terrain_id] = output_name
    domains = ("polities", "provinces", "settlements", "strategicUnits", "characters", "technologies", "institutions")
    settlement_runtime = _load_settlement_runtime_data(config, world)
    country_runtime = _load_country_interaction_runtime_data(config, world)
    runtime = {"schemaVersion": world["schemaVersion"], "sourceSha256": _sha(config.scenario_file), "timeline": world["timeline"], "events": world.get("events", []), "regionalGeography": world["regionalGeography"], "ids": {domain: [entry["id"] for entry in world.get(domain, [])] for domain in domains}, "polityDefinitions": world.get("polities", []), "provinceDefinitions": world.get("provinces", []), "provinceHoldings": [holding for holding in world.get("territorialHoldings", []) if holding.get("territory", {}).get("kind") == "province"], "militaryRuntimeTemplates": world.get("militaryRuntimeTemplates", []), "strategicUnits": world.get("strategicUnits", []), "armies": world.get("armies", []), "fleets": world.get("fleets", []), "defenseLayouts": world.get("defenseLayouts", []), "settlementRuntimeStates": settlement_runtime, "countryInteractionState": {key: value for key, value in country_runtime.items() if key != "sources"}}
    # These catalogues are optional for reusable scenarios, but when present
    # they are compiled into both the runtime payload and Warcraft bootstrap.
    # Source JSON remains authoritative; no release catalogue is duplicated in
    # hand-written Wurst.
    catalogue_paths = {
        "inventory": config.project / "scenario/inventory/player-use-catalog.json",
        "treasures": config.project / "scenario/treasures/age-of-sail.json",
        "religion": config.project / "scenario/religion.json",
        "piracy": config.project / "scenario/naval/piracy.json",
    }
    catalogues = {}
    for catalogue_id, catalogue_path in catalogue_paths.items():
        if catalogue_path.is_file():
            try: catalogues[catalogue_id] = json.loads(catalogue_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error: raise _fail("generation", f"{catalogue_id}: {error}") from error
            runtime[catalogue_id] = catalogues[catalogue_id]
    if config.custom_2d_source:
        custom=json.loads((generated/"custom-2d/custom-2d-imports.json").read_text(encoding="utf-8"))
        runtime["custom2dAssets"]={use:row["importPath"] for row in custom["assets"] for use in row["uses"]}
    (generated / GENERATED_DATA).write_text(json.dumps(runtime, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    movement = {"land": "MOVE_LAND", "naval": "MOVE_NAVAL", "amphibious": "MOVE_AMPHIBIOUS", "flying": "MOVE_FLYING"}
    recovery = ["\npublic function configureRecoveryScenario(UnstuckRecoveryService service)"]
    for index, zone in enumerate(world.get("navigationZones", ())):
        name = f"zone{index}"
        recovery.append(f'\tlet {name} = new RecoveryZone("{zone["id"]}")')
        for kind in zone["movementClasses"]: recovery.append(f"\t{name}.addMovement({movement[kind]})")
        for kind, destinations in zone.get("connections", {}).items():
            for destination in destinations: recovery.append(f'\t{name}.connect({movement[kind]}, "{destination}")')
        recovery.append(f"\tservice.addZone({name})")
    for index, point in enumerate(world.get("navigationSafePoints", ())):
        name, position = f"point{index}", point["position"]
        anchor = str(point["kind"] == "recovery_anchor").lower()
        recovery.append(f'\tlet {name} = new RecoveryPoint("{point["id"]}", "{point["zoneId"]}", {float(position["x"])}, {float(position["y"])}, true, {anchor})')
        for kind in point["movementClasses"]: recovery.append(f"\t{name}.addMovement({movement[kind]})")
        recovery.append(f"\tservice.addPoint({name})")
    for index, state in enumerate(world.get("activeUnitNavigationStates", ())):
        name, safe = f"entity{index}", state["lastSafePosition"]
        recovery.append(f'\tlet {name} = new RecoveryEntity("{state["unitId"]}", {movement[state["movementClass"]]}, "{state["currentZoneId"]}", true, true, false, false, true)')
        recovery.append(f"\tservice.addEntity({name})")
        recovery.append(f'\tservice.importLastSafe("{state["unitId"]}", "{safe["zoneId"]}", {float(safe["x"])}, {float(safe["y"])})')
    timeline = world["timeline"]
    timeline_lines = ["\npublic function configureCampaignTimeline() returns CampaignClock",
        f'\tlet clock = new CampaignClock({date.fromisoformat(timeline["startDate"]).toordinal()}, {date.fromisoformat(timeline["endDate"]).toordinal()}, {date.fromisoformat(timeline["initialDate"]).toordinal()}, 1.)']
    for era in timeline.get("eras", []):
        timeline_lines.append(f'\tclock.addEra("{era["id"]}", {date.fromisoformat(era["startDate"]).toordinal()}, {date.fromisoformat(era["endDate"]).toordinal()})')
    occurrences=[]
    for schedule in timeline.get("schedules", []):
        current=date.fromisoformat(schedule["firstDate"]); number=1; rule=schedule.get("recurrence")
        while True:
            occurrences.append((current, schedule["priority"], schedule["id"], number, schedule["eventId"]))
            if not rule or number >= rule.get("maxOccurrences", 2**31-1): break
            if rule["unit"] == "days":
                from datetime import timedelta
                following=current+timedelta(days=rule["interval"])
            else:
                months=rule["interval"]*(1 if rule["unit"] == "months" else 12)
                year,month0=divmod(current.year*12+current.month-1+months,12); month=month0+1
                following=date(year,month,min(current.day,calendar.monthrange(year,month)[1]))
            if following > date.fromisoformat(rule["untilDate"]): break
            current=following; number+=1
    for day,_,schedule,number,event in sorted(occurrences):
        timeline_lines.append(f'\tclock.addOccurrence("{schedule}", "{event}", {day.toordinal()}, {number})')
    timeline_lines.append("\treturn clock")
    def ws(value):
        return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    rpg = ["\npublic function configureGeneratedRpg(WarcraftRpgRuntime runtime)"]
    for index, row in enumerate(world.get("characters", ())):
        loyalty = row.get("loyalty", {})
        rpg += [f'\tlet hero{index}=new RpgHero("{ws(row["id"])}","{ws(row.get("displayName", row["id"]))}",\'Hpal\')',
                f'\thero{index}.loyalty={int(loyalty.get("score", 50))}',
                f'\thero{index}.professionId="{ws((row.get("professionIds") or [""])[0])}"',
                f'\thero{index}.personalQuestId="{ws((row.get("personalQuestIds") or [""])[0])}"',
                f'\thero{index}.regionId="{ws(row.get("regionId", ""))}"',
                f'\thero{index}.recruited={str(bool(row.get("recruited"))).lower()}',
                f'\truntime.heroes.register(hero{index})']
    research_rows = [("technology", row) for row in world.get("technologies", ())] + [("institution", row) for row in world.get("institutions", ())]
    for index, (research_kind, row) in enumerate(research_rows):
        cost = row.get("timeCost", {})
        unlock = (row.get("unlocks") or [{}])[0]
        rpg += [f'\tlet technology{index}=new RuntimeTechnology("{ws(row["id"])}","{ws(row.get("name", row["id"]))}",{int(cost.get("preferredYear", 0))},{int(cost.get("baseCost", 1))})',
                f'\ttechnology{index}.kind="{research_kind}"',
                f'\ttechnology{index}.prerequisiteId="{ws((row.get("prerequisiteIds") or [""])[0])}"',
                f'\ttechnology{index}.effectId="{ws(unlock.get("contentId", ""))}"',
                f'\ttechnology{index}.effectMagnitude=1', f'\truntime.technologies.register(technology{index})']
    for index, row in enumerate(world.get("quests", ())):
        journal = row.get("journal", {}); destinations = journal.get("destinations", {})
        destination = next(iter(destinations.values()), {})
        rpg += [f'\tlet quest{index}=new RuntimeQuest("{ws(row["id"])}","{ws(row.get("title", row["id"]))}","{ws(row.get("campaign", {}).get("chainKind", "campaign"))}")',
                f'\tquest{index}.giverId="{ws(journal.get("giver", {}).get("id", ""))}"',
                f'\tquest{index}.turnInId="{ws(journal.get("turnIn", {}).get("id", ""))}"',
                f'\tquest{index}.precision="{ws(destination.get("precision", "hidden"))}"',
                f'\tquest{index}.regionId="{ws(destination.get("regionId", ""))}"',
                f'\tquest{index}.destinationId="{ws(destination.get("locationId", destination.get("settlementId", "")))}"',
                f'\tquest{index}.rewardExperience=100', f'\truntime.journal.register(quest{index})']
    inventory = catalogues.get("inventory", {})
    item_sets = {item_id: row["id"] for row in inventory.get("equipmentSets", ()) for item_id in row.get("itemTypeIds", ())}
    for index, row in enumerate(inventory.get("items", ())):
        comparison = row.get("comparison", {}); stats = comparison.get("majorStats", {})
        power = sum(value for value in stats.values() if isinstance(value, int))
        requirements = row.get("requirements", {})
        rpg += [f'\tlet item{index}=new RpgItem("{ws(row["id"])}","{ws(row.get("name", row["id"]))}","{ws((comparison.get("slotIds") or [row.get("category", "item")])[0])}","{ws(row.get("rarityId", "common"))}",{int(row.get("itemLevel", 1))},{power})',
                f'\titem{index}.setId="{ws(item_sets.get(row["id"], ""))}"', f'\titem{index}.unique={str(bool(row.get("unique"))).lower()}',
                f'\titem{index}.startYear={int(requirements.get("startYear", 0))}', f'\titem{index}.endYear={int(requirements.get("endYear", 0))}',
                f'\titem{index}.technologyId="{ws((requirements.get("technologyIds") or [""])[0])}"',
                f'\titem{index}.institutionId="{ws((requirements.get("institutionIds") or [""])[0])}"', f'\truntime.inventory.registerItem(item{index})']
    for index, row in enumerate(inventory.get("equipmentSets", ())):
        thresholds = row.get("thresholds", []); first = thresholds[0] if thresholds else {}; last = thresholds[-1] if thresholds else {}
        rpg.append(f'\truntime.inventory.registerSet(new EquipmentSet("{ws(row["id"])}",{int(first.get("pieceCount", 0))},{len(first.get("effectIds", []))},{int(last.get("pieceCount", 0))},{len(last.get("effectIds", []))}))')
    treasure_data = catalogues.get("treasures", {}); candidates = {row["id"]: row for row in treasure_data.get("candidateLocations", ())}
    for index, row in enumerate(treasure_data.get("treasures", ())):
        choices = row.get("candidateLocationIds", []); resolved = choices[len(row["id"]) % len(choices)] if choices else ""
        candidate = candidates.get(resolved, {})
        rpg += [f'\tlet treasure{index}=new RuntimeTreasure("{ws(row["id"])}","{ws((row.get("anchorRegionIds") or [candidate.get("regionId", "")])[0])}","{ws(resolved)}")',
                f'\ttreasure{index}.clueCount={len(row.get("clueIds", []))}', f'\truntime.treasures.register(treasure{index})']
    templates = {row["id"]: row for row in world.get("militaryRuntimeTemplates", [])}
    military_lines = ["\npublic function configureMilitarySettlementScenario(MilitarySettlementRuntime runtime)"]
    for row in settlement_runtime:
        military_lines.append(f'\truntime.registerSettlement(new SettlementRuntimeState("{ws(row["id"])}", "{ws(row["controllerId"])}", "{ws(row["regionId"])}", \'htow\', \'hfoo\', {row["strength"]}, {row["reserves"]}, {row["manpower"]}, {row["supply"]}, {row["x"]}, {row["y"]}))')
        military_lines.append(f'\truntime.registerForce(new RuntimeForce("defense:{ws(row["id"])}:primary", "{ws(row["controllerId"])}", "{ws(row["regionId"])}", "siege", FORCE_DEFENSE, \'hgtw\', {row["strength"]}, {row["supply"]}, {row["x"] + 192.}, {row["y"]}))')
        official = row["official"]
        military_lines.append(f'\truntime.appoint("{ws(row["id"])}", new AdministratorState("{ws(official["characterId"])}", "{ws(official["displayName"])}", "Acting Administrator", "{ws(row["controllerId"])}", "{ws(row["regionId"])}", "{ws(row["id"])}", 50, 50, 40, 1))')
    traditions_path = config.project / "scenario/military-traditions.json"
    if traditions_path.is_file():
        tradition_data = json.loads(traditions_path.read_text(encoding="utf-8"))
        for controller in tradition_data.get("eligibleControllerIds", []):
            for tradition in tradition_data.get("traditions", []):
                milestone = (tradition.get("milestones") or [{}])[0]
                military_lines.append(f'\truntime.registerTradition(new TraditionState("{ws(controller)}", "{ws(tradition["categoryId"])}", 1, {int(milestone.get("threshold", 0))}, 0))')
    for row in world.get("strategicUnits", []):
        template = templates[row["runtimeInstantiation"]["runtimeTemplateId"]]
        kind = "FORCE_FLEET" if row["kind"] == "ship" else "FORCE_ARMY"
        category = "sailing_naval" if row["kind"] == "ship" else "land_formation"
        type_id = template["warcraftUnitTypeId"]
        supply = row.get("operationalState", {}).get("supply", 0)
        location = next((item for item in settlement_runtime if item["id"] == row["currentLocationId"]), settlement_runtime[0])
        military_lines.append(f'\truntime.registerForce(new RuntimeForce("{row["id"]}", "{row["controllerPolityId"]}", "{location["regionId"]}", "{category}", {kind}, \'{type_id}\', {row["representedStrength"]}, {supply}, {location["x"]}, {location["y"]}))')
    if len(military_lines) == 1:
        military_lines.append("\tskip")
    countries = ["\npublic function configureGeneratedCountryInteractions(PlayableCountryInteractionRuntime runtime)"]
    for row in country_runtime["polities"]:
        countries.append(f'\truntime.registerPolityResources("{ws(row["id"])}", {row["treasury"]}, {row["stock"]})')
        for reward in row["rewards"]:
            countries.append(f'\truntime.registerRewardProfile(new GovernmentRewardProfile("{ws(row["id"])}", "{ws(reward["id"])}", "{ws(reward["kind"])}", {reward["threshold"]}, {reward["reputation"]}, {reward["treasuryCost"]}, {str(reward["foreignService"]).lower()}))')
    for conflict in country_runtime["conflicts"]:
        for party in conflict["parties"]:
            countries.append(f'\truntime.setActiveConflict("{ws(party)}", "{ws(conflict["id"])}")')
    if len(countries) == 1:
        countries.append("\tskip")
    religion_lines = ["\npublic function configureGeneratedReligion(ReligionRuntime runtime)"]
    religion = catalogues.get("religion", {})
    for index, row in enumerate(religion.get("faiths", [])):
        curve = row["influenceCurve"]
        religion_lines.append(f'\tlet faith{index}=new RuntimeFaith("{ws(row["id"])}","{ws(row["name"])}",{int(curve["personalHalfSaturation"])},{int(curve["influenceHalfSaturation"])})')
        for benefit in row.get("benefits", []):
            religion_lines.append(f'\tfaith{index}.addBenefit(new ReligionBenefit("{ws(benefit["attributeId"])}",{int(benefit["capBasisPoints"])},"{ws(benefit["description"])}"))')
        religion_lines.append(f'\truntime.registerFaith(faith{index})')
    initial = religion.get("initialState", {})
    character = next(iter(initial.get("characters", [])), {})
    religion_lines.append(f'\truntime.characterId="{ws(character.get("characterId", "player_captain"))}"')
    religion_lines.append(f'\truntime.setCharacterFaith("{ws(character.get("primaryFaithId") or "")}",{int(character.get("personalInvestment", 0))})')
    for row in religion.get("conversionRules", []):
        religion_lines.append(f'\truntime.registerConversion(new ReligionConversionRule("{ws(row.get("fromFaithId") or "")}","{ws(row["toFaithId"])}",{int(row["costUnits"])},{int(row["cooldownTicks"])},{int(row.get("newInvestment", 0))},"{ws(row["reputationConsequences"])}"))')
    policies = {row["id"]: row for row in religion.get("policies", [])}
    for faith in religion.get("faiths", []):
        fid = faith["id"]
        population = sum(int(region["populationUnits"]) * next((int(x["shareBasisPoints"]) for x in region["composition"] if x["faithId"] == fid), 0) // 10000 for region in initial.get("regions", []))
        institutions = sum(int(x["influenceUnits"]) for x in initial.get("institutions", []) if x["faithId"] == fid and x["active"])
        government = sum(int(policies[x["policyId"]]["supportedInfluenceBasisPoints"]) for x in initial.get("polities", []) if fid in x["supportedFaithIds"])
        base = next((x for x in initial.get("influence", []) if x["faithId"] == fid), {})
        religion_lines.append(f'\truntime.setInfluence("{ws(fid)}",{population},{institutions},{government},{int(base.get("prestigeUnits", 0))},{int(base.get("eventUnits", 0))})')
    if len(religion_lines) == 1:
        religion_lines.append("\tskip")
    piracy_data = catalogues.get("piracy", {"rules": {}, "havens": []})
    piracy_rules = piracy_data.get("rules", {})
    piracy = ["\npublic function configureGeneratedPiracy(PiracyRuntime runtime)"]
    for row in piracy_data.get("havens", ()):
        piracy.append(f'\truntime.registerHaven("{ws(row["id"])}",{int(row.get("minimumNotoriety", 0))},"{ws(",".join(row.get("serviceIds", [])))}")')
    for row in piracy_data.get("governmentForms", ()):
        piracy.append(f'\truntime.registerGovernmentForm("{ws(row["id"])}","{ws(row.get("rulerTitle", ""))}")')
    if len(piracy) == 1:
        piracy.append("\tskip")
    piracy_factory = f'''\npublic function createGeneratedPiracyRuntime() returns PiracyRuntime
\treturn new PiracyRuntime(new PiracyRules({int(piracy_rules.get("repeatTargetCooldownTicks", 30))},{int(piracy_rules.get("foundingNotoriety", 20))},{int(piracy_rules.get("foundingWealthMinor", 5000))},{int(piracy_rules.get("foundingPrizes", 3))},{int(piracy_rules.get("bountyPerNotorietyMinor", 100))}))'''
    # Keep generated functions deliberately small.  A single function containing
    # every settlement/good pair is large enough to exhaust Grill's compiler heap
    # on the full world catalogue even though the resulting JASS is valid.
    trade_records = []
    goods_path = config.project / "scenario/economy/global-goods.json"
    settlement_sources = {}
    for path in sorted((config.project / "scenario/settlements").glob("*-1450.json")):
        region = path.name.removesuffix("-1450.json")
        for row in json.loads(path.read_text(encoding="utf-8")).get("settlements", []):
            settlement_sources[row["id"]] = (region, row)
    if goods_path.is_file():
        goods_catalog = json.loads(goods_path.read_text(encoding="utf-8"))
        goods = {row["id"]: row for row in goods_catalog.get("goods", [])}
        for settlement in settlement_runtime:
            region, row = settlement_sources[settlement["id"]]
            economy_identity = row.get("economy", {})
            production = economy_identity.get("production", row.get("productionRefs", []))
            imports = economy_identity.get("imports", row.get("importRefs", []))
            shortages = economy_identity.get("shortages", row.get("shortageRefs", []))
            defaults = goods_catalog.get("regionalDefaults", {}).get(region, {})
            basket = list(dict.fromkeys(production + imports + shortages + defaults.get("stapleGoodIds", [])))
            roles, services = set(row.get("roles", [])), set(row.get("services", []))
            if roles & {"trade_center", "trade_hub", "caravan_center"} or "warehouse" in services:
                basket += [x for x in defaults.get("tradeGoodIds", []) if x not in basket]
            basket = basket[:int(goods_catalog.get("performanceBudgets", {}).get("maximumGoodsPerSettlement", 12))]
            for good_id in basket:
                good = goods[good_id]
                stock = 320 if good_id in production else 180 if good_id in imports else 24 if good_id in shortages else 90
                if row.get("port") and good_id in imports: stock = stock * 13 // 10
                pressure = 1350 if good_id in shortages else 820 if good_id in production else 1000
                buy = max(1, int(good["basePriceMinor"]) * pressure // 1000)
                liquidity = max(1000, sum(max(1, int(goods[x]["basePriceMinor"])) * stock for x in basket if x in goods))
                trade_records.append(
                    f'\truntime.registerMarketProfile("{ws(settlement["id"])}","{ws(good_id)}",'
                    f'{stock},{liquidity},{buy},{1250 if good_id in production else 1000},'
                    f'{1250 if good_id in shortages else 1000},{350 if good_id in shortages else 0})')
            capacity = 24000 if "warehouse" in services else 120 if row.get("port") else 60
            trade_records.append(f'\truntime.registerStore(new TradeStore("warehouse:{ws(settlement["id"])}",{capacity},1000))')
        # Cargo belongs to authored vessels. One eligible player store is selected
        # at campaign start; stable IDs survive map transitions and save/load.
        for unit in world.get("strategicUnits", []):
            if unit.get("kind") == "ship":
                capacity = max(1, int(unit.get("representedStrength", 10)) * 20)
                trade_records.append(f'\truntime.registerStore(new TradeStore("cargo:{ws(unit["id"])}",{capacity},0))')
    runtime["tradeMarketCount"] = sum(1 for line in trade_records if "runtime.registerMarketProfile(" in line)
    if settlement_runtime and runtime["tradeMarketCount"] == 0:
        raise PackagingError("generation: playable settlements would receive no authoritative trade markets")
    trade_lines = []
    chunk_size = 160
    for start in range(0, len(trade_records), chunk_size):
        name = f"configureGeneratedTrade{start // chunk_size}"
        trade_lines += [f"\nfunction {name}(PlayableTradeRuntime runtime)", *trade_records[start:start + chunk_size]]
    trade_lines.append("\npublic function configureGeneratedTrade(PlayableTradeRuntime runtime)")
    if trade_records:
        trade_lines += [f"\tconfigureGeneratedTrade{i}(runtime)" for i in range((len(trade_records) + chunk_size - 1) // chunk_size)]
    else:
        trade_lines.append("\tskip")
    origin_configuration = "public function configureGeneratedOrigins(OriginCatalog controller)\n\tskip\n"
    arrival_configuration = "public function configureGeneratedArrivals(PlayableCampaignState state)\n\tskip\n"
    physical_manifest = config.project / "physical-maps.json"
    if physical_manifest.is_file():
        from package_wurst_campaign import campaign_arrival_configuration, campaign_origin_configuration, campaign_origin_records, position_campaign_origins, load_campaign_config
        campaign = load_campaign_config(physical_manifest)
        origins = campaign_origin_records(world, campaign.maps)
        arrivals = position_campaign_origins(config.project, generated, world, campaign.maps, origins)
        runtime["newCampaignOrigins"] = origins
        runtime["physicalMapArrivals"] = arrivals
        origin_configuration = campaign_origin_configuration(origins, campaign.maps)
        arrival_configuration = campaign_arrival_configuration(arrivals)
    wurst = f"// Generated by package_wurst_map.py v{GENERATOR_VERSION}; do not edit.\npackage {config.package_name}\n\nimport UnstuckRecovery\nimport CampaignTimeline\nimport CommandRouter\nimport WarcraftRpgRuntime\nimport MilitarySettlementRuntime\nimport PlayableCountryInteractions\nimport ReligionRuntime\nimport PlayablePiracy\nimport PlayableCampaignRuntime\nimport PlayableTrade\n\npublic constant int SCENARIO_SCHEMA_VERSION = {world['schemaVersion']}\npublic constant string PHYSICAL_MAP_ID = \"unpackaged\"\npublic constant string SCENARIO_SOURCE_SHA256 = \"{runtime['sourceSha256']}\"\n\n{origin_configuration}public function configureGeneratedPhysicalBoundaries(PhysicalBoundaryRegistry registry)\n\tskip\n" + "\n".join(recovery + timeline_lines + rpg + military_lines + countries + religion_lines + piracy + trade_lines) + piracy_factory + "\n"
    wurst += arrival_configuration
    (generated / GENERATED_DATA).write_text(json.dumps(runtime, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (generated / GENERATED_WURST).write_text(wurst, encoding="utf-8")
    input_paths = (
        config.config_path,
        config.manifest,
        config.scenario_file,
        config.scenario_validator,
        config.project / "wurst.build",
        *(path for path in (config.project / "wurst_run.args",) if path.is_file()),
        Path(__file__).resolve(),
        Path(__file__).resolve().with_name("generate_regional_terrain.py"),
        *(path for _, path in config.regional_terrain),
        *terrain_authorities,
        *((config.custom_2d_source, config.custom_2d_builder) if config.custom_2d_source else ()),
        *(path for path in catalogue_paths.values() if path.is_file()),
        *(path for path in (config.project / "scenario/economy/global-goods.json", config.project / "scenario/economy/playable-trade.json") if path.is_file()),
        *(path for path in country_runtime["sources"] if path.is_file()),
        *(config.project / "scenario/settlements").glob("*-1450.json"),
        *(config.project / "scenario/geography").glob("*.json"),
        *(path for path in (
            config.project / "scenario/integration/release-scale-settlements.json",
            config.project / "scenario/military-traditions.json",
            config.project / "physical-maps.json",
            Path(__file__).with_name("package_wurst_campaign.py"),
            Path(__file__).with_name("materialize_physical_map.py"),
        ) if path.is_file()),
    )
    inputs = {}
    for path in input_paths:
        try:
            key = str(path.relative_to(config.project.parent))
        except ValueError:
            # Unit tests load this shared module before copying a fixture project.
            # The reserved key also avoids encoding machine-specific absolute paths.
            key = f"@generator/{path.name}"
        inputs[key] = _sha(path)
    outputs = {name: _sha(generated / name) for name in (GENERATED_WURST, GENERATED_DATA, *terrain_outputs.values())}
    if config.custom_2d_source:
        for path in sorted((generated/"custom-2d").rglob("*")):
            if path.is_file(): outputs[path.relative_to(generated).as_posix()]=_sha(path)
    provenance = {"formatVersion": 1, "generatorVersion": GENERATOR_VERSION, "inputs": inputs, "outputs": outputs}
    (generated / PROVENANCE).write_text(json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8")

def verify_generated(config: BuildConfig, generated: Path) -> None:
    try: provenance = json.loads((generated / PROVENANCE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise _fail("provenance", f"missing or invalid {PROVENANCE}: {error}") from error
    if provenance.get("generatorVersion") != GENERATOR_VERSION: raise _fail("provenance", "generated data uses a different generator version")
    for relative, expected in provenance.get("inputs", {}).items():
        if relative.startswith("@generator/"):
            path = Path(__file__).resolve().with_name(relative.removeprefix("@generator/"))
        else:
            path = config.project.parent / relative
        if not path.is_file() or _sha(path) != expected: raise _fail("provenance", f"stale generated data: input changed: {relative}")
    for name, expected in provenance.get("outputs", {}).items():
        path = generated / name
        if not path.is_file() or _sha(path) != expected: raise _fail("provenance", f"stale generated data: output changed: {name}")

def _run(stage: str, command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode: raise _fail(stage, f"command exited {result.returncode}: {' '.join(command)}\n{(result.stderr or result.stdout).strip()}")

def _assemble(config: BuildConfig, root: Path, generated: Path, terrain_ids: tuple[str, ...] | None = None, *, include_tests: bool = True) -> Path:
    compile_root = root / "compile"
    shutil.copytree(config.source_map, compile_root / "map" / config.source_map.name)
    shutil.copytree(config.wurst_source, compile_root / "wurst",
                    ignore=None if include_tests else shutil.ignore_patterns("*Tests.wurst"))
    shutil.copy2(config.project / "wurst.build", compile_root / "wurst.build")
    if (config.project / "wurst_run.args").is_file():
        shutil.copy2(config.project / "wurst_run.args", compile_root / "wurst_run.args")
    shutil.copy2(generated / GENERATED_WURST, compile_root / "wurst" / GENERATED_WURST)
    runtime_dir = compile_root / "map" / config.source_map.name / "runtime"; runtime_dir.mkdir()
    shutil.copy2(generated / GENERATED_DATA, runtime_dir / GENERATED_DATA); shutil.copy2(generated / PROVENANCE, runtime_dir / PROVENANCE)
    selected = set(terrain_ids) if terrain_ids is not None else {terrain_id for terrain_id, _ in config.regional_terrain}
    for terrain_id, _source in config.regional_terrain:
        if terrain_id not in selected:
            continue
        shutil.copy2(generated / f"terrain-{terrain_id}.json", runtime_dir / f"terrain-{terrain_id}.json")
    if config.custom_2d_source:
        custom=generated/"custom-2d"
        shutil.copy2(custom/"custom-2d-imports.json",runtime_dir/"custom-2d-imports.json")
        for path in sorted((custom/"imports").rglob("*")):
            if path.is_file():
                target=compile_root/"map"/config.source_map.name/path.relative_to(custom/"imports")
                target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
    return compile_root

def _find_archive(root: Path) -> Path:
    files = [p for p in root.rglob("*.w3x") if p.is_file()]
    if not files: raise _fail("map assembly", "Wurst produced no .w3x archive")
    return max(files, key=lambda p: p.stat().st_mtime_ns)

def _inspect(config: BuildConfig, archive: Path, compile_root: Path, terrain_ids: tuple[str, ...] | None = None) -> None:
    data = archive.read_bytes()
    if len(data) < 4 or data[:4] not in (b"MPQ\x1a", b"HM3W", b"PK\x03\x04"): raise _fail("archive inspection", f"unrecognized Warcraft archive: {archive}")
    lua = ""
    packaged_source_sha = None
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zipped:
            selected = set(terrain_ids) if terrain_ids is not None else {terrain_id for terrain_id, _ in config.regional_terrain}
            names = set(zipped.namelist()); expected = {"war3map.w3i", "war3map.w3e", "war3map.wpm", "war3map.lua", f"runtime/{GENERATED_DATA}", f"runtime/{PROVENANCE}", *(f"runtime/terrain-{terrain_id}.json" for terrain_id in selected)}
            if config.custom_2d_source:
                expected.add("runtime/custom-2d-imports.json")
                custom=json.loads(zipped.read("runtime/custom-2d-imports.json"))
                expected.update(row["importPath"].replace("\\","/") for row in custom["assets"])
            if expected - names: raise _fail("archive inspection", "missing entries: " + ", ".join(sorted(expected - names)))
            if any(name.startswith(("tests/", "fixtures/", "scenario/", "wurst/")) for name in names): raise _fail("archive inspection", "development-only source or fixtures were packaged")
            lua = zipped.read("war3map.lua").decode("utf-8", errors="replace")
            try:
                packaged_source_sha = json.loads(zipped.read(f"runtime/{GENERATED_DATA}"))["sourceSha256"]
            except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as error:
                raise _fail("archive inspection", f"invalid generated runtime provenance: {error}") from error
    else:
        candidates = list(compile_root.rglob("war3map.lua")) + list(compile_root.rglob("*_compiled.lua")) + list(compile_root.rglob("output.lua"))
        if candidates: lua = max(candidates, key=lambda p: p.stat().st_mtime_ns).read_text(encoding="utf-8", errors="replace")
    if not lua: raise _fail("archive inspection", "generated Lua runtime code is missing")
    absent = [marker for marker in config.bootstrap_markers if marker not in lua]
    if absent: raise _fail("archive inspection", "Lua is missing marker(s): " + ", ".join(absent))
    # ScenarioData used to retain a megabyte-scale JSON string solely because
    # this source digest happened to occur inside it.  The runtime payload is
    # now an archive resource, so validate its authoritative-source identity at
    # that boundary instead of requiring an otherwise-unused Lua literal.
    if packaged_source_sha is not None and packaged_source_sha != _sha(config.scenario_file):
        raise _fail("archive inspection", "generated runtime source digest does not match the authoritative scenario")

def clean(config: BuildConfig) -> None:
    root = config.project / "_build"
    if root.exists(): shutil.rmtree(root)

def run_execution_tests(config: BuildConfig, executable: str, revision: str | None = None) -> dict:
    """Run the full unlocalized suite once, including generated scenario records."""
    root = config.project / "_build/wurst-tests"
    if root.exists(): shutil.rmtree(root)
    generated = root / "generated"
    generate(config, generated); verify_generated(config, generated)
    compile_root = _assemble(config, root, generated)
    _run("Wurst test dependency installation", [executable, "install"], compile_root)
    try:
        return execute_tests(compile_root, executable, root, source_revision(config.project, revision))
    except WurstExecutionError as error:
        raise _fail("Wurst execution", error) from error

def build(config_path: Path, grill: str | None = None, clean_first: bool = True) -> Path:
    config = load_config(config_path); executable = validate_inputs(config, grill)
    if clean_first: clean(config)
    validate_scenario(config); root = config.project / "_build"; generated = root / "generated"
    generate(config, generated); verify_generated(config, generated); compile_root = _assemble(config, root, generated)
    _run("Wurst dependency installation", [executable, "install"], compile_root)
    _run("Wurst compilation", [executable, "typecheck"], compile_root)
    try:
        execute_tests(compile_root, executable, root / "wurst-tests", source_revision(config.project))
    except WurstExecutionError as error:
        raise _fail("Wurst execution", error) from error
    _run("map assembly", [executable, "build", str(Path("map") / config.source_map.name)], compile_root)
    archive = _find_archive(compile_root / "_build"); _inspect(config, archive, compile_root)
    config.output.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(archive, config.output)
    print(f"release archive: {config.output}"); return config.output

def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) not in (1, 2) or (len(argv) == 2 and argv[0] != "clean"): print("usage: package_wurst_map.py [clean] CONFIG", file=sys.stderr); return 2
    try:
        config_path = Path(argv[-1]); clean(load_config(config_path)) if len(argv) == 2 else build(config_path)
    except (PackagingError, OSError) as error: print(f"packaging failed: {error}", file=sys.stderr); return 1
    return 0
if __name__ == "__main__": raise SystemExit(main())
