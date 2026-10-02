import copy
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "engine"))
import campaign_save
import new_campaign


class NewCampaignOriginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = json.loads((PROJECT / "scenario/world/world.json").read_text())
        cls.maps = json.loads((PROJECT / "physical-maps.json").read_text())
        cls.origins = new_campaign.NewCampaignOrigins(
            cls.world["polities"], cls.world["settlements"], cls.maps, page_size=9)

    def test_every_active_1450_polity_is_named_selectable_and_resolvable(self):
        self.assertEqual(len(self.world["polities"]), len(self.origins.options))
        self.assertEqual({p["id"] for p in self.world["polities"]},
                         {p.polity_id for p in self.origins.options})
        for option in self.origins.options:
            self.assertTrue(option.name)
            location = self.origins.resolve_start(option.polity_id)
            self.assertIn(location["settlementId"], {s["id"] for s in self.world["settlements"]})
            self.assertNotEqual("bootstrap_runtime_validation", location["physicalMapId"])

    def test_search_and_paging_use_player_facing_names(self):
        first = self.origins.page(page=1)
        second = self.origins.page(page=2)
        self.assertEqual(9, len(first.options))
        self.assertTrue(set(first.options).isdisjoint(second.options))
        ming = self.origins.page("great ming")
        self.assertEqual(["ming_empire"], [row.polity_id for row in ming.options])
        self.assertEqual(1, ming.pages)

    def test_representative_origins_resolve_across_world_regions(self):
        expected = {
            "england": "europe_west", "ming_empire": "east_asia",
            "marinid_morocco": "africa", "ottoman_empire": "europe_central_east",
            "malacca_sultanate": "southeast_asia",
            "mexica_tenochtitlan": "americas_north_central",
            "hawaii_chiefdom": "pacific_north",
        }
        for polity_id, map_id in expected.items():
            state = self.origins.begin(polity_id, {"characterId": "player"})
            self.assertEqual(polity_id, state["originPolityId"])
            self.assertEqual(polity_id, state["currentAllegiancePolityId"])
            self.assertEqual(map_id, state["startingLocation"]["physicalMapId"])
            self.origins.validate_player_state(state)

    def test_allegiance_changes_never_rewrite_origin_or_start_history(self):
        initial = self.origins.begin("england")
        changed = self.origins.change_allegiance(initial, "ming_empire")
        self.assertEqual("england", changed["originPolityId"])
        self.assertEqual(initial["startingLocation"], changed["startingLocation"])
        self.assertEqual("ming_empire", changed["currentAllegiancePolityId"])
        self.assertEqual("england", initial["currentAllegiancePolityId"])
        with self.assertRaisesRegex(new_campaign.OriginSelectionError, "immutable"):
            self.origins.begin("ming_empire", changed)

    def test_invalid_inactive_and_tampered_ids_fail_without_fallback(self):
        for polity_id in ("", "not_a_polity", None):
            with self.assertRaises(new_campaign.OriginSelectionError):
                self.origins.begin(polity_id)
        state = self.origins.begin("england")
        state["startingLocation"]["settlementId"] = "beijing"
        with self.assertRaisesRegex(new_campaign.OriginSelectionError, "does not match"):
            self.origins.validate_player_state(state)

    def test_save_load_and_schema_four_migration_preserve_identity_exactly(self):
        state = self.origins.change_allegiance(self.origins.begin("marinid_morocco"), "england")
        raw = campaign_save.serialize_save(build_version="test", scenario_id="age_of_sail",
            scenario_version="1", slot=campaign_save.SaveSlot("manual", 1), created_at="now",
            world_state={}, player_state={"main": state})
        loaded = campaign_save.load_save(raw)
        self.assertEqual(state, loaded["state"]["players"]["main"])
        self.origins.validate_player_state(loaded["state"]["players"]["main"])

        legacy = json.loads(raw); legacy["schemaVersion"] = 4
        legacy["integrity"]["checksum"] = campaign_save._checksum(legacy)
        migrated = campaign_save.load_save(json.dumps(legacy))
        self.assertEqual(state, migrated["state"]["players"]["main"])
        legacy_player = copy.deepcopy(state)
        for key in ("originPolityId", "currentAllegiancePolityId", "startingLocation"):
            legacy_player.pop(key)
        with self.assertRaises(new_campaign.OriginSelectionError):
            self.origins.validate_player_state(legacy_player)


if __name__ == "__main__": unittest.main()
