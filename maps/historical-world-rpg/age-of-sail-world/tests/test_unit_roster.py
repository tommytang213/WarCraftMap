import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
import validate_unit_roster
from unit_roster import RosterCatalog, RosterError, RosterProjection

SOURCE = json.loads((ROOT / "scenario/rosters/foundation.json").read_text(encoding="utf-8"))


def references():
    progression = json.loads((ROOT / "scenario/progression/catalog.json").read_text())
    traditions = json.loads((ROOT / "scenario/military-traditions.json").read_text())
    world = json.loads((ROOT / "scenario/world/world.json").read_text())
    return {"technologies": {x["id"] for x in progression["technologies"]},
            "militaryTraditions": {x["id"] for x in traditions["traditions"]},
            "countries": {x["id"] for x in world["polities"]}}


def instance(ident="first_unit", archetype="pike_foot", strength=1000, region="europe"):
    return {"id":ident, "archetypeId":archetype, "representedStrength":strength,
            "regionId":region, "active":True, "morale":70, "discipline":65, "supply":80}


class UnitRosterTests(unittest.TestCase):
    def catalog(self, mutate=None):
        value = copy.deepcopy(SOURCE)
        if mutate: mutate(value)
        return RosterCatalog(value, references())

    def rejected(self, mutate, message=None):
        with self.assertRaisesRegex(RosterError, message or ".*"):
            self.catalog(mutate)

    def test_representative_categories_and_distinct_mechanics_are_valid(self):
        catalog = validate_unit_roster.load_catalog()
        categories = {x["category"] for x in catalog.generated_unit_data()}
        self.assertEqual({"infantry","cavalry","artillery","specialist","marine","transport","merchant","warship"}, categories)
        mechanics = {x["mechanic"] for x in catalog.abilities.values()}
        self.assertEqual({"passive","active","aura","formation","weapon","morale","discipline","resistance","counter","logistics","terrain","boarding","siege"}, mechanics)

    def test_inheritance_country_override_and_explicit_list_replacement(self):
        source = copy.deepcopy(SOURCE)
        child = copy.deepcopy(next(x for x in source["archetypes"] if x["id"] == "drilled_foot"))
        child.update(id="country_guard", name="Country Guard", countryId="england", upgradeToIds=[], replacementIds=[])
        source["archetypes"].append(child)
        catalog = RosterCatalog(source, references())
        resolved = catalog.archetypes["country_guard"]
        self.assertEqual(("england", ["matchlock"], ["steady_drill"]), (resolved["countryId"], resolved["weaponIds"], resolved["abilityIds"]))
        self.assertEqual("country_guard", resolved["id"])

    def test_historical_and_controlled_early_access(self):
        catalog = self.catalog()
        self.assertFalse(catalog.availability("drilled_foot", 1640, set()).available)
        early = catalog.availability("drilled_foot", 1640, {"flintlock_drill"})
        self.assertTrue(early.available and early.early_access)
        historical = catalog.availability("drilled_foot", 1700, {"flintlock_drill"})
        self.assertTrue(historical.available and not historical.early_access)
        self.assertEqual(100, historical.historical_modifier)

    def test_duplicate_cycle_invalid_category_and_missing_template_rejected(self):
        self.rejected(lambda d: d["weapons"].append(copy.deepcopy(d["weapons"][0])), "duplicate ID")
        self.rejected(lambda d: d["archetypes"][0].update(extends="pike_foot"), "inheritance cycle")
        self.rejected(lambda d: next(x for x in d["archetypes"] if x["id"] == "pike_foot").update(category="dragon"), "invalid category")
        self.rejected(lambda d: next(x for x in d["archetypes"] if x["id"] == "pike_foot").update(runtimeTemplateId="missing"), "runtime template")

    def test_incompatible_equipment_movement_ability_formation_ship_and_references_rejected(self):
        def mutate(field, value):
            return lambda d: next(x for x in d["archetypes"] if x["id"] == "pike_foot").update({field:value})
        self.rejected(mutate("movementClassId", "ocean_sail"), "movement")
        self.rejected(mutate("weaponIds", ["naval_guns"]), "incompatible weapon")
        self.rejected(mutate("abilityIds", ["broadside"]), "incompatible ability")
        self.rejected(mutate("formationIds", ["mounted_wedge"]), "formation")
        self.rejected(mutate("shipId", "armed_sailing_hull"), "ship")
        self.rejected(mutate("militaryTraditionIds", ["missing_tradition"]), "missing militaryTraditions")
        self.rejected(mutate("technologyIds", ["missing_technology"]), "missing technologies")

    def test_broken_ability_and_impossible_upgrade_chains_rejected(self):
        self.rejected(lambda d: next(x for x in d["archetypes"] if x["id"] == "pike_foot").update(abilityIds=["missing"]), "broken ability")
        self.rejected(lambda d: next(x for x in d["archetypes"] if x["id"] == "drilled_foot").update(upgradeToIds=["pike_foot"]), "cycle")
        self.rejected(lambda d: next(x for x in d["archetypes"] if x["id"] == "pike_foot").update(upgradeToIds=["armed_sailing_warship"]), "changes category")

    def test_projection_is_deterministic_bounded_and_strength_is_not_object_count(self):
        catalog = self.catalog(); units = [instance(strength=1000), instance("fleet", "armed_sailing_warship", 5000)]
        runtime = RosterProjection(catalog, units)
        first = runtime.project("europe", 5)
        runtime.lose_representations(); second = runtime.project("europe", 5)
        self.assertEqual(first, second)
        self.assertEqual(5, len(first))
        self.assertEqual(6000, sum(x["representedStrength"] for x in runtime.snapshot()["instances"]))
        self.assertEqual((), runtime.project("inactive_region", 5))

    def test_representation_loss_save_load_and_derived_modifiers_are_stable(self):
        runtime = RosterProjection(self.catalog(), [instance()])
        baseline = runtime.snapshot(); before = runtime.project("europe", 20)
        payload = json.dumps(baseline, sort_keys=True)
        self.assertNotIn("warcraftUnitTypeId", payload)
        self.assertNotIn("derived", payload)
        runtime.lose_representations(); runtime.restore(json.loads(payload))
        self.assertEqual(before, runtime.project("europe", 20))
        self.assertEqual(("steady_drill",), runtime.derived_modifiers("first_unit"))
        self.assertEqual(("steady_drill",), runtime.derived_modifiers("first_unit"))

    def test_generated_data_is_stable_and_inspectable(self):
        first = validate_unit_roster.load_catalog(); second = validate_unit_roster.load_catalog()
        self.assertEqual(first.digest(), second.digest())
        self.assertEqual(first.generated_unit_data(), second.generated_unit_data())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "units.json"
            self.assertEqual(0, validate_unit_roster.main(["--output", str(output)]))
            document = json.loads(output.read_text())
            self.assertEqual(first.digest(), document["digest"])
            self.assertEqual(104, len(document["units"]))


if __name__ == "__main__":
    unittest.main()
