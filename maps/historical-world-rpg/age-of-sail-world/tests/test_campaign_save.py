import copy
import json
import sys
import unittest
from pathlib import Path

CATEGORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CATEGORY_ROOT / "_shared" / "engine"))
import campaign_save

WORLD_STATE = {
    "calendar": {"year": 1588, "day": 203},
    "polities": {"england": {"treasury": 12000, "atWarWith": ["spain"]}},
    "settlements": {"london": {"legalOwnerPolityId": "england", "controllerPolityId": "england", "prosperity": 72}},
    "fleets": {"english_channel_fleet": {"shipIds": ["ark_royal"], "position": {"navigationZoneId": "english_channel", "x": 41.5, "y": -3.25}, "runtimeState": "abstract"}},
}
PLAYER_STATE = {"mainPlayer": {"characterId": "player_captain", "allegiancePolityId": "england", "money": 430, "inventoryItemIds": ["brass_spyglass"], "reputation": {"england": 34, "spain": -12}}}


def make_save(slot=campaign_save.SaveSlot("autosave", 15)):
    return campaign_save.serialize_save(
        build_version="0.1.0+test", scenario_id="age_of_sail_world", scenario_version="0.1.0",
        slot=slot, created_at="2026-09-27T12:00:00Z", world_state=WORLD_STATE, player_state=PLAYER_STATE,
    )


class CampaignSaveTests(unittest.TestCase):
    def test_representative_world_and_player_state_round_trip(self):
        loaded = campaign_save.load_save(make_save())
        self.assertEqual(WORLD_STATE, loaded["state"]["world"])
        self.assertEqual(PLAYER_STATE, loaded["state"]["players"])
        self.assertEqual((2, "0.1.0+test"), (loaded["schemaVersion"], loaded["buildVersion"]))
        self.assertEqual({"id": "age_of_sail_world", "version": "0.1.0"}, loaded["scenario"])
        self.assertEqual("autosave_15", loaded["slot"]["id"])
        self.assertEqual(64, len(loaded["integrity"]["checksum"]))

    def test_serialization_is_deterministic_and_copies_input_state(self):
        world = copy.deepcopy(WORLD_STATE)
        kwargs = dict(build_version="1", scenario_id="age_of_sail_world", scenario_version="1", slot=campaign_save.SaveSlot("manual", 2), created_at="2026-09-27T12:00:00Z", world_state=world, player_state=PLAYER_STATE)
        raw = campaign_save.serialize_save(**kwargs)
        self.assertEqual(raw, campaign_save.serialize_save(**kwargs))
        world["calendar"]["year"] = 9999
        self.assertEqual(1588, campaign_save.load_save(raw)["state"]["world"]["calendar"]["year"])

    def test_slot_layout_has_all_required_slot_classes(self):
        slots = campaign_save.slot_layout(3)
        self.assertEqual(15, len([slot for slot in slots if slot.kind == "autosave"]))
        self.assertEqual(["manual_01", "manual_02", "manual_03"], [slot.stable_id for slot in slots if slot.kind == "manual"])
        self.assertIn(campaign_save.SaveSlot("session_start"), slots)
        self.assertIn(campaign_save.SaveSlot("major_milestone"), slots)
        with self.assertRaises(campaign_save.SaveError):
            campaign_save.SaveSlot("autosave", 16)

    def test_transient_warcraft_handles_are_rejected(self):
        world = copy.deepcopy(WORLD_STATE)
        world["fleets"]["english_channel_fleet"]["unitHandle"] = 1234
        with self.assertRaisesRegex(campaign_save.SaveError, "transient Warcraft handles"):
            campaign_save.serialize_save(build_version="1", scenario_id="age_of_sail_world", scenario_version="1", slot=campaign_save.SaveSlot("session_start"), created_at="2026-09-27T12:00:00Z", world_state=world, player_state=PLAYER_STATE)

    def test_failed_load_does_not_change_source_bytes(self):
        tampered_document = json.loads(make_save())
        tampered_document["state"]["players"]["mainPlayer"]["money"] = 999999
        tampered = json.dumps(tampered_document).encode()
        source_before = bytes(tampered)
        with self.assertRaises(campaign_save.IntegrityError):
            campaign_save.load_save(tampered)
        self.assertEqual(source_before, tampered)

        future = json.loads(make_save())
        future["schemaVersion"] = 99
        future["integrity"]["checksum"] = campaign_save._checksum(future)
        future_raw = json.dumps(future).encode()
        with self.assertRaises(campaign_save.IncompatibleSaveError):
            campaign_save.load_save(future_raw)
        self.assertEqual(json.dumps(future).encode(), future_raw)

    def test_synthetic_version_zero_migrates_without_mutating_old_document(self):
        old = json.loads(make_save(campaign_save.SaveSlot("major_milestone")))
        old["schemaVersion"] = 0
        old["state"]["player"] = old["state"].pop("players")["mainPlayer"]
        old["integrity"]["checksum"] = campaign_save._checksum(old)
        snapshot = copy.deepcopy(old)

        def migrate_v0(document):
            document["state"]["players"] = {"mainPlayer": document["state"].pop("player")}
            document["schemaVersion"] = 1
            return document

        registry = campaign_save.MigrationRegistry()
        registry.register(0, migrate_v0)
        loaded = campaign_save.load_save(json.dumps(old), registry)
        self.assertEqual((2, PLAYER_STATE), (loaded["schemaVersion"], loaded["state"]["players"]))
        self.assertEqual(snapshot, old)

    def test_missing_or_invalid_migration_is_rejected(self):
        old = json.loads(make_save())
        old["schemaVersion"] = 0
        old["integrity"]["checksum"] = campaign_save._checksum(old)
        with self.assertRaises(campaign_save.IncompatibleSaveError):
            campaign_save.load_save(json.dumps(old))
        registry = campaign_save.MigrationRegistry()
        registry.register(0, lambda document: document)
        with self.assertRaises(campaign_save.IncompatibleSaveError):
            campaign_save.load_save(json.dumps(old), registry)


if __name__ == "__main__":
    unittest.main()
