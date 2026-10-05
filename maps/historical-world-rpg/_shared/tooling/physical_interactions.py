"""Generate local RPG targets from stable records and materialized geography."""
import json

from materialize_physical_map import location_cell, physical_layout, settlement_placements

MOVEMENTS = {"land": 0, "naval": 1, "amphibious": 2, "flying": 3}


def interaction_locations(project, generated, world, maps, treasures, terrain_sources):
    zones = {row["id"]: row["movementClasses"] for row in world.get("navigationZones", [])}
    for path in terrain_sources:
        for row in json.loads(path.read_text()).get("navigationZones", []):
            zones.setdefault(row["id"], row["movementClasses"])
    result = []
    by_settlement = {}
    for physical in maps:
        if physical.bootstrap:
            continue
        width, height, cells, layouts = physical_layout(generated, physical)
        settlements = [s for s in world.get("settlements", [])
                       if s.get("regionalInstanceId") in physical.regional_instance_ids]
        placed = settlement_placements(project, physical, settlements, width, height, cells, layouts)
        for row in placed:
            record = dict(id=row["id"], eventId=row["id"], mapId=physical.id,
                          kind="settlement", world=row["world"], movements=[0, 2, 3])
            result.append(record)
            by_settlement[row["id"]] = record
        # Logical regions may span physical chapters. A chapter's own raster
        # bounds, never region knowledge or camera focus, authorize region clues.
        region_parts = {}
        for terrain_id in physical.terrain_ids:
            doc = json.loads((generated / f"terrain-{terrain_id}.json").read_text())
            region_parts.setdefault(doc['regionId'], []).extend(
                [row['id'] for row in doc['instances']] if doc.get('formatVersion') == 2 else [doc['regionId']])
        for region in physical.logical_region_ids:
            region_layouts = [layouts[part] for part in region_parts.get(region, []) if part in layouts]
            for ox, oy, iw, ih in region_layouts:
                result.append(dict(id=region, eventId=region, mapId=physical.id, kind="region",
                                   world=[0., 0.], movements=[0, 1, 2, 3],
                                   bounds=[(ox-width/2)*128., (oy-height/2)*128.,
                                           (ox+iw-width/2)*128., (oy+ih-height/2)*128.]))
        reserved = {tuple(row["cell"]) for row in placed}
        for candidate in sorted(treasures.get("candidateLocations", []), key=lambda row: row["id"]):
            if candidate["regionalInstanceId"] not in physical.regional_instance_ids or not candidate["accessible"]:
                continue
            if candidate["physicalMapId"] != physical.id and (candidate["physicalMapId"] in {m.id for m in maps} or len([m for m in maps if not m.bootstrap]) > 1):
                raise ValueError(f"interaction candidate {candidate['id']}: incompatible physical map")
            layout = layouts.get(candidate["regionalInstanceId"], next(iter(layouts.values())))
            allowed = zones.get(candidate["navigationZoneId"])
            surfaces = {1, 2}
            if allowed is not None:
                surfaces = ({1} if "land" in allowed else set()) | ({2} if "naval" in allowed else set())
                if not surfaces and ("amphibious" in allowed or "flying" in allowed):
                    surfaces = {1, 2}
            position = candidate["position"]
            cx, cy = location_cell((position["x"], position["y"]), layout, width, cells, surfaces, reserved)
            reserved.add((cx, cy))
            # Some candidate zone IDs are descriptive labels rather than
            # navigation definitions. They cannot override actual terrain.
            movements = {0 if cells[cy*width+cx] == 1 else 1, 2, 3}
            if allowed is not None:
                movements &= {MOVEMENTS[m] for m in allowed}
            result.append(dict(id=candidate["id"], eventId=candidate["id"], mapId=physical.id,
                               kind="treasure", world=[(cx+.5-width/2)*128., (cy+.5-height/2)*128.],
                               movements=sorted(movements)))
    for location in world.get("questLocations", []):
        settlement = by_settlement.get(location.get("settlementId"))
        if settlement is None:
            raise ValueError(f"quest interaction {location['id']} lacks a physical settlement anchor")
        result.append(dict(settlement, id=location["id"], kind="quest"))
    if len(result) > 4096 or len({(row['id'], row['mapId'], tuple(row.get('bounds', []))) for row in result}) != len(result):
        raise ValueError("interaction locations exceed capacity or duplicate identities")
    return result


def interaction_configuration(locations):
    lines = ["InteractionCatalog generatedInteractionCatalog = null", "",
             "function createGeneratedInteractions() returns InteractionCatalog",
             "\tlet catalog = new InteractionCatalog()"]
    for row in locations:
        args = ", ".join(json.dumps(row[key]) for key in ("id", "eventId", "mapId", "kind"))
        args += ", " + ", ".join(str(float(n)) for n in row["world"])
        record = f"new InteractionLocation({args})"
        if "bounds" in row:
            record += ".bounds(" + ", ".join(str(float(n)) for n in row["bounds"]) + ")"
        record += "".join(f".allow({m})" for m in row["movements"])
        lines.append(f"\tcatalog.add({record})")
    lines += ["\treturn catalog", "",
              "public function configureGeneratedInteractions(PhysicalInteractionContext context)",
              "\tif generatedInteractionCatalog == null",
              "\t\tgeneratedInteractionCatalog = createGeneratedInteractions()",
              "\tcontext.catalog = generatedInteractionCatalog"]
    return "\n".join(lines) + "\n"
