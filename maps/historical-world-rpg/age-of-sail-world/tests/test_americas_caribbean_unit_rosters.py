import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))

import validate_unit_roster
from unit_roster import RosterError, RosterProjection


class AmericasCaribbeanRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = validate_unit_roster.load_catalog()
        cls.source = json.loads((ROOT / "scenario/rosters/americas-caribbean.json").read_text())
        cls.world = json.loads((ROOT / "scenario/world/world.json").read_text())

    def available(self, unit, year, country, technologies=(), equipment=(), reforms=(), resources=(), port=False):
        return self.catalog.availability(unit, year, set(technologies), country_id=country,
            equipment_ids=set(equipment), reform_ids=set(reforms), resource_ids=set(resources), has_port=port)

    def test_every_world_polity_has_direct_or_family_roster_coverage(self):
        self.assertEqual({x["id"] for x in self.world["polities"]}, {p for p, _ in self.catalog.assignments})
        self.assertEqual(7, len(self.catalog.roster_families))

    def test_all_americas_polities_have_direct_usable_assignments(self):
        politics = json.loads((ROOT / "scenario/politics/americas-caribbean-1450.json").read_text())
        expected = {x["id"] for x in politics["polities"]}
        direct = {(p, u) for a in self.source["assignments"] for p in a["polityIds"] for u in a["archetypeIds"]}
        self.assertEqual(expected, {p for p, _ in direct})
        for polity in expected:
            self.assertTrue(any(self.catalog.archetypes[unit]["availability"]["historicalStartYear"] == 1450
                for owner, unit in direct if owner == polity))

    def test_contact_technologies_and_resources_are_not_1450_defaults(self):
        gates = dict(technologies={"pike_and_shot"}, equipment={"traded_firearms"}, reforms={"contact_firearm_adoption"})
        self.assertFalse(self.available("contact_musket_company", 1450, "haudenosaunee_nations", **gates).available)
        self.assertFalse(self.available("contact_musket_company", 1650, "haudenosaunee_nations",
            technologies={"pike_and_shot"}, reforms={"contact_firearm_adoption"}).available)
        self.assertTrue(self.available("contact_musket_company", 1650, "haudenosaunee_nations", **gates).available)
        horse_gates = dict(equipment={"introduced_horses"}, reforms={"mounted_warfare_adoption"}, resources={"horses"})
        self.assertFalse(self.available("indigenous_horse_company", 1450, "mapuche_rewe_confederacies", **horse_gates).available)
        self.assertFalse(self.available("indigenous_horse_company", 1700, "mapuche_rewe_confederacies",
            equipment={"introduced_horses"}, reforms={"mounted_warfare_adoption"}).available)
        self.assertTrue(self.available("indigenous_horse_company", 1700, "mapuche_rewe_confederacies", **horse_gates).available)
        self.assertFalse(self.available("adopted_cannon_battery", 1700, "tawantinsuyu",
            technologies={"cast_cannon"}, reforms={"artillery_adoption"}).available)

    def test_country_port_upgrade_and_replacement_gates(self):
        self.assertTrue(self.available("pueblo_bow_guard", 1450, "pueblo_world").available)
        self.assertFalse(self.available("pueblo_bow_guard", 1450, "tlaxcallan_confederation").available)
        self.assertFalse(self.available("caribbean_war_pirogue", 1500, "taino_cacicazgos").available)
        self.assertTrue(self.available("caribbean_war_pirogue", 1500, "taino_cacicazgos", port=True).available)
        woodland = self.catalog.archetypes["woodland_war_party"]
        self.assertEqual(["contact_musket_company"], woodland["upgradeToIds"])
        self.assertEqual(["contact_musket_company"], woodland["replacementIds"])

    def test_required_terrain_siege_naval_boarding_and_amphibious_roles(self):
        expected = {"woodland_war_party":"woodland_ambush", "andean_sling_regiment":"mountain_warfare",
            "indigenous_horse_company":"plains_mobility", "mexica_eagle_warriors":"palisade_assault",
            "inuit_coastal_hunters":"kayak_seamanship", "lowland_forest_war_party":"river_canoe_logistics",
            "great_lakes_war_canoe":"canoe_boarding", "caribbean_canoe_marines":"amphibious_assault"}
        signatures = set()
        for unit, role in expected.items():
            row = self.catalog.archetypes[unit]
            self.assertIn(role, row["abilityIds"])
            self.assertGreater(row["cost"], 0); self.assertGreater(row["strategicStrength"], 0)
            self.assertIn(row["runtimeTemplateId"], self.catalog.templates)
            signatures.add((row["category"], tuple(row["abilityIds"]), row["movementClassId"]))
        self.assertEqual(len(expected), len(signatures))

    def test_abstract_local_reconstruction_and_runtime_bound_are_deterministic(self):
        forces = [
            {"id":"forest_force","archetypeId":"woodland_war_party","representedStrength":900,"regionId":"americas","active":True,"morale":74,"discipline":62,"supply":80},
            {"id":"canoe_force","archetypeId":"caribbean_war_pirogue","representedStrength":1200,"regionId":"caribbean","active":True,"morale":70,"discipline":58,"supply":75}]
        runtime = RosterProjection(self.catalog, forces)
        first = runtime.project("americas", 3); state = runtime.snapshot()
        runtime.lose_representations(); runtime.restore(state)
        self.assertEqual(first, runtime.project("americas", 3)); self.assertLessEqual(len(first), 3)
        self.assertEqual((), runtime.project("pacific", 3))
        self.assertIn("woodland_ambush", runtime.derived_modifiers("forest_force"))

    def test_invalid_import_reference_and_broken_upgrade_are_rejected(self):
        source = copy.deepcopy(self.catalog.source)
        next(x for x in source["archetypes"] if x["id"] == "contact_musket_company")["equipmentIds"] = ["unvalidated_import"]
        with self.assertRaisesRegex(RosterError, "missing equipment"): type(self.catalog)(source, self.catalog.references)
        source = copy.deepcopy(self.catalog.source)
        next(x for x in source["archetypes"] if x["id"] == "woodland_war_party")["upgradeToIds"] = ["great_lakes_war_canoe"]
        with self.assertRaisesRegex(RosterError, "changes category"): type(self.catalog)(source, self.catalog.references)

    def test_multi_century_snapshot_is_stable_and_not_cosmetic_duplication(self):
        ids = [x["id"] for x in self.source["archetypes"]]
        timeline = [sum(self.catalog.archetypes[x]["strategicStrength"] for x in ids
            if self.catalog.archetypes[x]["availability"]["historicalStartYear"] <= year <= self.catalog.archetypes[x]["availability"]["historicalEndYear"])
            for year in range(1450, 1821, 10)]
        self.assertGreater(max(timeline), min(timeline))
        signatures = [(x["category"], tuple(x["weaponIds"]), tuple(x["abilityIds"]), tuple(x["formationIds"]))
            for x in (self.catalog.archetypes[i] for i in ids)]
        self.assertEqual(len(signatures), len(set(signatures)))


if __name__ == "__main__": unittest.main()
