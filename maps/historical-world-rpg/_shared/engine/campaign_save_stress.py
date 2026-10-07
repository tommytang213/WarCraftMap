"""Deterministic Phase 7 campaign persistence stress workload."""
from __future__ import annotations

import copy, hashlib, json, time
from pathlib import Path

import campaign_save as saves
import autosave_scheduler
import cross_map_persistence as transfers
import large_world_stress as world

FORMAT = "warcraftmap_campaign_save_stress_v1"
SUMMARY_FORMAT = "warcraftmap_campaign_save_stress_summary_v1"
AUTHORITATIVE_DOMAINS = frozenset((*world.ENTITY_KINDS, "traditionTracks", "scheduledWork",
                                   "mapKnowledge", "treasures"))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def normalized_hash(state):
    """Hash authority only, independent of slot, timestamps, and presentation."""
    return hashlib.sha256(canonical(state)).hexdigest()


def complete_fixture(profile):
    """Return full current-schema authority, including migration-added domains."""
    fixture = world.generate_fixture(profile)
    fixture["mapKnowledge"] = {
        "version": 1, "regions": [], "settlements": [], "landmarks": [],
        "routes": [], "boundaries": [], "pointsOfInterest": [],
        "locations": {}, "searchAreas": {},
    }
    fixture["treasures"] = {
        "version": 1, "campaignSeed": "", "seedFingerprint": "",
        "resolved": {}, "knowledge": {}, "collectionCounts": {},
    }
    return fixture


def authoritative_domains(fixture):
    """Name every persisted domain so fixture omissions fail loudly as systems grow."""
    entities = fixture.get("entities", {})
    return frozenset((*entities.keys(), *(key for key in
        ("traditionTracks", "scheduledWork", "mapKnowledge", "treasures") if key in fixture)))


def apply_scripted_transition(fixture, cycle):
    """Drive event, battle, capture, quest, and region boundaries deterministically."""
    entities = fixture["entities"]
    war = entities["wars"][cycle % len(entities["wars"])]
    war["score"] += -1 if cycle % 2 else 1
    army = entities["armies"][cycle % len(entities["armies"])]
    army["strength"] = max(1, army["strength"] - (1 + cycle % 3))
    province = entities["provinces"][cycle % len(entities["provinces"])]
    captor = f"polity_{(cycle + 1) % len(entities['polities']):06d}"
    province["controllerId"] = captor
    if cycle % 4 == 3:
        province["ownerId"] = captor
        for settlement in entities["settlements"]:
            if settlement["provinceId"] == province["id"]:
                settlement["ownerId"] = captor
    quest = entities["quests"][cycle % len(entities["quests"])]
    quest["occurrences"] += 1
    fixture["activeRegionId"] = fixture["regions"][(cycle + 1) % len(fixture["regions"])]
    world.validate_fixture(fixture)


def load_profiles(path, world_profiles):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("format") != FORMAT: raise ValueError("unsupported campaign-save stress configuration")
    result = {}
    for name, item in raw.get("profiles", {}).items():
        if item.get("worldProfile") not in world_profiles: raise ValueError(f"{name}: unknown world profile")
        budgets = item.get("budgets", {})
        if set(budgets) != {"save_ms", "load_ms", "serialized_state_bytes", "state_growth_bytes"}: raise ValueError(f"{name}: incomplete budgets")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0 for v in budgets.values()): raise ValueError(f"{name}: invalid budgets")
        if any(isinstance(item.get(k), bool) or not isinstance(item.get(k), int) or item[k] < 1
               for k in ("cycles", "mapRevisits")): raise ValueError(f"{name}: invalid workload")
        result[name] = item
    return result


class Harness:
    def __init__(self, fixture):
        self.world, self.players = copy.deepcopy(fixture), {"main": {"characterId": "character_000000", "money": 1000}}
        self.runtime, self.safe = {}, True
        self.storage = saves.MemorySaveStorage()
        self.manager = saves.CampaignSaveManager(build_version="phase7.1", scenario_id="persistence_stress",
            scenario_version="1", storage=self.storage, capture_state=lambda: (self.world, self.players),
            validate_state=lambda w, p: world.validate_fixture(w), reconstruct_runtime=self._reconstruct,
            activate_state=self._activate, is_save_safe=lambda: self.safe)

    def _reconstruct(self, authority, players):
        # Presentation is derived and deliberately absent from persisted authority.
        return {"represented": world.active_representations(authority, 500)}

    def _activate(self, authority, players, runtime):
        self.world, self.players, self.runtime = authority, players, runtime


def _old_payload(raw, version):
    document = json.loads(raw)
    document["schemaVersion"] = version
    if version < 3: document["state"]["world"].pop("mapKnowledge", None)
    if version < 4: document["state"]["world"].pop("treasures", None)
    document["integrity"]["checksum"] = saves._checksum(document)
    return canonical(document)


def _manifest():
    return {"format":"warcraftmap_physical_maps_v1","formatVersion":1,"physicalMaps":[
        {"id":"map_a","packagePath":"Maps/MapA.w3x","assignments":{"logicalRegionIds":["map_a"],"regionalInstanceIds":["map_a"],"generatedTerrainIds":[]}},
        {"id":"map_b","packagePath":"Maps/MapB.w3x","assignments":{"logicalRegionIds":["map_b"],"regionalInstanceIds":["map_b"],"generatedTerrainIds":[]}},
        {"id":"map_c","packagePath":"Maps/MapC.w3x","assignments":{"logicalRegionIds":["map_c"],"regionalInstanceIds":["map_c"],"generatedTerrainIds":[]}}]}


def _content(map_id):
    return {"physicalMap":{"id":map_id,"logicalRegionIds":[map_id],"regionalInstanceIds":[map_id],"generatedTerrainIds":[]}}


def run(profile_name, config, world_profile):
    initial = complete_fixture(world_profile)
    if authoritative_domains(initial) != AUTHORITATIVE_DOMAINS:
        missing = sorted(AUTHORITATIVE_DOMAINS - authoritative_domains(initial))
        extra = sorted(authoritative_domains(initial) - AUTHORITATIVE_DOMAINS)
        raise AssertionError(f"authoritative domain coverage changed: missing={missing}, extra={extra}")
    uninterrupted = copy.deepcopy(initial)
    h = Harness(initial); first_save_size = None; max_size = 0
    hashes, save_times, load_times = [], [], []
    def checkpoint_round_trip(slot, label):
        """Exercise a non-autosave slot without advancing campaign authority."""
        expected = normalized_hash({"world": h.world, "players": h.players})
        h.manager.save(slot, label)
        h.world = {}
        h.manager.load(slot)
        if normalized_hash({"world": h.world, "players": h.players}) != expected:
            raise AssertionError(f"{slot.stable_id} reconstruction drift")

    # Recovery and player slots are independent of the rolling autosave cursor.
    for slot, label in ((saves.SaveSlot("session_start"), "session-start"),
                        (saves.SaveSlot("major_milestone"), "milestone"),
                        (saves.SaveSlot("manual", 1), "manual")):
        checkpoint_round_trip(slot, label)
    scheduler = autosave_scheduler.RollingAutosaveScheduler(h.manager, 1, now=0)
    autosave_ids = []
    for i in range(config["cycles"]):
        target = min(world_profile.duration, h.world["time"] + world_profile.step_size)
        world.advance(h.world, target, world_profile.step_size, world_profile.representation_limit)
        world.advance(uninterrupted, target, world_profile.step_size, world_profile.representation_limit)
        apply_scripted_transition(h.world, i)
        apply_scripted_transition(uninterrupted, i)
        if i and i % 7 == 0:
            checkpoint_round_trip(saves.SaveSlot("manual", i // 7 + 1), f"manual-{i:04d}")
        if i == config["cycles"] // 3:
            checkpoint_round_trip(saves.SaveSlot("session_start"), f"session-{i:04d}")
        if i == config["cycles"] // 2:
            checkpoint_round_trip(saves.SaveSlot("major_milestone"), f"milestone-{i:04d}")
        expected_slot = saves.SaveSlot("autosave", i % saves.AUTOSAVE_SLOT_COUNT + 1)
        started=time.perf_counter_ns(); attempt=scheduler.tick(i + 1, f"stress-{i:04d}"); save_times.append((time.perf_counter_ns()-started)/1e6)
        if attempt is None or attempt.status != "saved" or attempt.slot_id != expected_slot.stable_id:
            raise AssertionError(f"autosave wraparound drift at cycle {i}: {attempt}")
        slot = expected_slot; autosave_ids.append(attempt.slot_id)
        raw=h.storage.read(slot.stable_id)
        if first_save_size is None: first_save_size=len(raw)
        max_size=max(max_size,len(raw)); expected=normalized_hash({"world":h.world,"players":h.players})
        h.world={}; started=time.perf_counter_ns(); h.manager.load(slot); load_times.append((time.perf_counter_ns()-started)/1e6)
        if normalized_hash({"world":h.world,"players":h.players}) != expected: raise AssertionError("save/load reconstruction drift")
        hashes.append(expected)
    final_authority = {"world": h.world, "players": h.players}
    path_hashes = {"uninterrupted": normalized_hash({"world": uninterrupted, "players": h.players}),
                   "frequentlyResumed": normalized_hash(final_authority)}
    if len(set(path_hashes.values())) != 1:
        raise AssertionError("frequently resumed state differs from uninterrupted state")
    expected_slots={f"autosave_{i:02d}" for i in range(1,saves.AUTOSAVE_SLOT_COUNT+1)}
    if set(autosave_ids) != expected_slots or not expected_slots.issubset(h.storage._slots):
        raise AssertionError("workload did not populate every rolling autosave slot")
    entity_ids = [item["id"] for values in h.world["entities"].values() for item in values]
    if len(entity_ids) != len(set(entity_ids)):
        raise AssertionError("duplicate authoritative stable IDs detected")
    # Every supported source schema migrates without rewriting its stored bytes.
    migration_harness = Harness(final_authority["world"])
    migration_harness.players = copy.deepcopy(final_authority["players"])
    manual = saves.SaveSlot("manual", 1); manual_id = manual.stable_id
    migration_harness.manager.save(manual, "migration-source")
    current=migration_harness.storage.read(manual_id)
    for version in (1,2,3):
        old=_old_payload(current,version); migration_harness.storage._slots[manual_id]=old
        migration_harness.manager.load(manual)
        if migration_harness.storage.read(manual_id) != old: raise AssertionError("migration mutated source save")
        if normalized_hash({"world": migration_harness.world, "players": migration_harness.players}) != path_hashes["uninterrupted"]:
            raise AssertionError(f"schema {version} migration drift")
    path_hashes["migrated"] = normalized_hash({"world": migration_harness.world,
                                                "players": migration_harness.players})
    # Real transfer envelopes repeatedly visit all maps while carrying full authority.
    transfer_storage=transfers.MemoryTransferStorage(); active={"id":"map_a"}
    def activate_transfer(map_id, state, _runtime):
        active.update(id=map_id)
        h.world = copy.deepcopy(state["world"])
        h.players = copy.deepcopy(state["players"])

    tm=transfers.CrossMapTransferManager(scenario_id="persistence_stress",scenario_version="1",build_version="phase7.1",
        campaign_schema=saves.CURRENT_SCHEMA_VERSION,manifest=transfers.PhysicalMapManifest(_manifest()),storage=transfer_storage,
        capture_state=lambda:{"world":h.world,"players":h.players},load_destination_content=_content,activate=activate_transfer,
        adapters=[transfers.ReconstructionAdapter("authority_index",lambda s,c,a:tuple(sorted(s["world"].get("entities",{}))))])
    maps=("map_a","map_b","map_c")
    for i in range(config["mapRevisits"]): tm.transfer(active["id"],maps[(i+1)%3],{"boundaryId":f"boundary_{i:03d}"},f"stress-{i:03d}")
    resumed,destination=tm.resume()
    if normalized_hash(resumed)!=normalized_hash(final_authority) or destination!=active["id"]: raise AssertionError("cross-map reconstruction drift")
    path_hashes["crossMap"] = normalized_hash(resumed)
    if len(set(path_hashes.values())) != 1: raise AssertionError("persistence path hash mismatch")
    metrics={"save_ms":max(save_times),"load_ms":max(load_times),"serialized_state_bytes":max_size,
             "state_growth_bytes":max_size-first_save_size}
    failures=[f"{k}={v:.3f} exceeds {config['budgets'][k]}" for k,v in metrics.items() if v>config["budgets"][k]]
    return {"format":SUMMARY_FORMAT,"profile":profile_name,"normalizedHash":normalized_hash(h.world),"pathHashes":path_hashes,"cycles":config["cycles"],
        "mapRevisits":config["mapRevisits"],"autosaveSlots":sorted(expected_slots),
        "authoritativeDomains":sorted(AUTHORITATIVE_DOMAINS),"distinctCycleHashes":len(set(hashes)),
        "metrics":metrics,"budgets":config["budgets"],"passed":not failures,"failures":failures}
