import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))

import validate_unit_roster
from unit_roster import RosterProjection


class RegionalUnitRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = validate_unit_roster.load_catalog()
        cls.slice = json.loads((ROOT / "scenario/rosters/europe-africa-middle-east-india.json").read_text())

    def available(self, unit, year, country, technologies=(), institutions=(), equipment=(), reforms=(), resources=(), port=False):
        return self.catalog.availability(unit, year, set(technologies), country_id=country,
            established_institution_ids=set(institutions), equipment_ids=set(equipment),
            reform_ids=set(reforms), resource_ids=set(resources), has_port=port)

    def test_country_assignments_cover_three_regions_and_selective_small_polities(self):
        assigned = {p for p, _ in self.catalog.assignments}
        expected = {"england", "france", "swiss_confederacy", "venice", "ottoman_empire",
                    "vijayanagara_empire", "ethiopian_empire", "songhai_kingdom",
                    "mossi_kingdoms", "kongo_kingdom", "kilwa_sultanate"}
        self.assertTrue(expected <= assigned)
        self.assertGreaterEqual(len(assigned), 25)

    def test_representative_dates_and_alternate_history_require_every_gate(self):
        self.assertTrue(self.available("english_longbow_retinue", 1450, "england").available)
        self.assertFalse(self.available("english_longbow_retinue", 1600, "england").available)
        full = dict(technologies={"flintlock_drill", "linear_tactics"},
                    equipment={"flintlock_musket"}, reforms={"standing_army_reform"}, resources={"grain"})
        self.assertTrue(self.available("european_musket_battalion", 1650, "france", **full).early_access)
        self.assertFalse(self.available("european_musket_battalion", 1700, "france",
            technologies=full["technologies"], equipment=full["equipment"], reforms=full["reforms"]).available)
        ship = dict(technologies={"battlefleet_doctrine"}, institutions={"public_credit"},
                    equipment={"naval_ordnance"}, reforms={"permanent_naval_board"},
                    resources={"ship_provisions"}, port=True)
        self.assertTrue(self.available("british_ship_of_line", 1700, "england", **ship).available)
        self.assertFalse(self.available("british_ship_of_line", 1700, "france", **ship).available)
        self.assertFalse(self.available("british_ship_of_line", 1700, "england", **{**ship, "port": False}).available)
        self.assertTrue(self.available("european_musket_battalion", 1820, "austria", **full).available)

    def test_roles_balance_and_upgrade_paths_are_materially_distinct(self):
        units = self.catalog.generated_unit_data()
        categories = {x["category"] for x in units}
        self.assertEqual({"infantry","cavalry","artillery","specialist","marine","transport","merchant","warship"}, categories)
        signatures = {(x["category"], tuple(sorted(x["abilityIds"])), x["movementClassId"], x.get("shipId")) for x in units}
        self.assertGreaterEqual(len(signatures) / len(units), .75)
        for unit in units:
            self.assertGreater(unit["cost"], 0); self.assertGreaterEqual(unit["upkeep"], 0)
            self.assertGreaterEqual(unit["supply"], 0); self.assertGreater(unit["strategicStrength"], 0)
            self.assertLessEqual(unit["upkeep"], unit["cost"])
        pike = self.catalog.archetypes["european_pike_company"]
        self.assertEqual(["european_musket_battalion"], pike["upgradeToIds"])
        self.assertEqual(["european_musket_battalion"], pike["replacementIds"])

    def test_deterministic_land_siege_boarding_naval_and_mixed_fixtures(self):
        def score(ids, terrain):
            total = 0
            for ident in ids:
                unit = self.catalog.archetypes[ident]
                bonus = sum(12 for ability in unit["abilityIds"] if ability in terrain)
                total += unit["strategicStrength"] + bonus - unit["supply"]
            return total
        fixtures = {
            "land": (["swiss_pike_column", "french_gendarme"], {"pike_square", "cavalry_shock"}),
            "siege": (["field_artillery_battery", "vijayanagara_rocket_corps"], {"field_siege", "fortress_artillery"}),
            "boarding": (["venetian_galley", "shipboard_marines"], {"boarding_action", "galley_tactics"}),
            "naval": (["british_ship_of_line", "portuguese_carrack"], {"broadside", "line_of_battle"}),
            "mixed": (["ottoman_janissary_orta", "ottoman_sipahi", "mediterranean_galley"], {"volley_fire", "desert_mobility"}),
        }
        first = {name: score(*force) for name, force in fixtures.items()}
        self.assertEqual(first, {name: score(*force) for name, force in fixtures.items()})
        self.assertEqual(5, len(set(first.values())))

    def test_inactive_and_active_reconstruction_stays_bounded(self):
        instances = []
        for index, unit in enumerate(self.catalog.generated_unit_data()):
            instances.append({"id":f"regional_force_{index}", "archetypeId":unit["id"],
                "representedStrength":unit["strategicStrength"] * 20, "regionId":"europe" if index % 2 else "africa",
                "active":True, "morale":70, "discipline":65, "supply":80})
        runtime = RosterProjection(self.catalog, instances)
        before = runtime.snapshot(); first = runtime.project("europe", 48)
        self.assertLessEqual(len(first), 48)
        self.assertEqual((), runtime.project("middle_east_india", 48))
        runtime.lose_representations(); runtime.restore(before)
        self.assertEqual(first, runtime.project("europe", 48))
        self.assertEqual(before, runtime.snapshot())


if __name__ == "__main__":
    unittest.main()
