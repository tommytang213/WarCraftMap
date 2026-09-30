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


class AsiaPacificRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = validate_unit_roster.load_catalog()
        cls.source = json.loads((ROOT / "scenario/rosters/southeast-east-asia-pacific.json").read_text())

    def available(self, unit, year, country, technologies=(), equipment=(), reforms=(), resources=(), port=False):
        return self.catalog.availability(unit, year, set(technologies), country_id=country,
            equipment_ids=set(equipment), reform_ids=set(reforms),
            resource_ids=set(resources), has_port=port)

    def test_assignments_cover_mainland_maritime_frontier_and_pacific_polities(self):
        assigned = {polity for polity, _ in self.catalog.assignments}
        expected = {"ming_empire", "joseon_kingdom", "ashikaga_shogunate", "oirat_confederation",
            "jianzhou_jurchen", "dai_viet", "ayutthaya_kingdom", "majapahit_empire",
            "malacca_sultanate", "ternate_sultanate", "sulu_sultanate", "chamorro_chiefdoms",
            "marshallese_irooj_domains", "hawaii_chiefdom", "fijian_vanua", "maori_iwi_hapu"}
        self.assertTrue(expected <= assigned)
        self.assertGreaterEqual(len(assigned & expected), 16)

    def test_1450_baseline_and_later_gunpowder_progression_are_gated(self):
        self.assertTrue(self.available("ming_shenji_battalion", 1450, "ming_empire",
            technologies={"pike_and_shot", "professional_bureaucracy"},
            equipment={"matchlock_firearm"}, reforms={"wei_suo_mustering"}).available)
        self.assertFalse(self.available("japanese_teppo_ashigaru", 1450, "ashikaga_shogunate",
            technologies={"pike_and_shot"}, equipment={"matchlock_firearm"}).available)
        self.assertTrue(self.available("japanese_teppo_ashigaru", 1550, "ashikaga_shogunate",
            technologies={"pike_and_shot"}, equipment={"matchlock_firearm"}).available)
        self.assertFalse(self.available("jurchen_banner_cavalry", 1650, "jianzhou_jurchen",
            technologies={"professional_bureaucracy"}).available)
        self.assertTrue(self.available("jurchen_banner_cavalry", 1650, "jianzhou_jurchen",
            technologies={"professional_bureaucracy"}, reforms={"banner_army_reform"}).available)
        self.assertFalse(self.available("ming_treasure_junk", 1600, "ming_empire",
            technologies={"oceanic_seamanship", "cast_cannon"}, equipment={"naval_ordnance"},
            resources={"ship_provisions"}, port=True).available)

    def test_ports_resources_country_and_reconstruction_gates_are_deterministic(self):
        gates = dict(technologies={"oceanic_seamanship", "celestial_navigation"},
            resources={"ship_provisions"}, port=True)
        self.assertTrue(self.available("austronesian_voyaging_canoe", 1450, "tui_tonga_empire", **gates).available)
        self.assertFalse(self.available("austronesian_voyaging_canoe", 1450, "tui_tonga_empire",
            technologies=gates["technologies"], resources=gates["resources"], port=False).available)
        self.assertFalse(self.available("maori_taua", 1600, "fijian_vanua").available)
        self.assertTrue(self.available("maori_taua", 1600, "maori_iwi_hapu").available)

        force = {"id":"island_force", "archetypeId":"maori_taua", "representedStrength":900,
            "regionId":"pacific", "active":True, "morale":75, "discipline":68, "supply":82}
        runtime = RosterProjection(self.catalog, [force])
        first = runtime.project("pacific", 8)
        runtime.lose_representations()
        runtime.restore(runtime.snapshot())
        self.assertEqual(first, runtime.project("pacific", 8))
        self.assertEqual((), runtime.project("east_asia", 8))
        self.assertIn("island_defense", runtime.derived_modifiers("island_force"))

    def test_role_identities_and_runtime_templates_cover_required_forces(self):
        representatives = {
            "mainland":"mainland_elephant_corps", "frontier":"mongol_horse_archers",
            "siege":"joseon_hwacha_battery", "boarding":"moro_karakoa_marines",
            "amphibious":"maori_taua", "island_defense":"polynesian_island_guard",
            "voyaging":"austronesian_voyaging_canoe", "naval":"malaccan_lancaran",
        }
        signatures = set()
        for unit_id in representatives.values():
            unit = self.catalog.archetypes[unit_id]
            self.assertIn(unit["runtimeTemplateId"], self.catalog.templates)
            self.assertGreater(unit["cost"], 0)
            self.assertGreater(unit["strategicStrength"], 0)
            signatures.add((unit["category"], tuple(unit["abilityIds"]), unit["movementClassId"]))
        self.assertEqual(len(representatives), len(signatures))

    def test_invalid_navigation_upgrade_and_assignment_references_are_rejected(self):
        source = copy.deepcopy(self.catalog.source)
        next(x for x in source["archetypes"] if x["id"] == "austronesian_voyaging_canoe")["movementClassId"] = "foot"
        with self.assertRaisesRegex(RosterError, "movement"):
            type(self.catalog)(source, self.catalog.references)

        source = copy.deepcopy(self.catalog.source)
        next(x for x in source["archetypes"] if x["id"] == "polynesian_island_guard")["upgradeToIds"] = ["pacific_war_canoe"]
        with self.assertRaisesRegex(RosterError, "changes category"):
            type(self.catalog)(source, self.catalog.references)

    def test_long_timeline_and_local_battle_fixtures_are_stable(self):
        ids = [row["id"] for row in self.source["archetypes"]]
        totals = []
        for year in range(1450, 1821, 10):
            total = sum(self.catalog.archetypes[unit]["strategicStrength"] for unit in ids
                if self.catalog.archetypes[unit]["availability"]["historicalStartYear"] <= year
                <= self.catalog.archetypes[unit]["availability"]["historicalEndYear"])
            totals.append(total)
        self.assertEqual(totals, list(totals))
        self.assertGreater(max(totals), min(totals))

        fixtures = [
            ["mainland_elephant_corps", "dai_viet_handgunners", "joseon_hwacha_battery"],
            ["moro_karakoa_marines", "malaccan_lancaran", "moluccan_kora_kora"],
            ["polynesian_island_guard", "maori_taua", "pacific_war_canoe"],
        ]
        scores = [sum(self.catalog.archetypes[x]["strategicStrength"] -
            self.catalog.archetypes[x]["supply"] for x in force) for force in fixtures]
        self.assertEqual(scores, [sum(self.catalog.archetypes[x]["strategicStrength"] -
            self.catalog.archetypes[x]["supply"] for x in force) for force in fixtures])
        self.assertEqual(3, len(set(scores)))


if __name__ == "__main__":
    unittest.main()
