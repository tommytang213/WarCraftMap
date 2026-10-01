import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
from validate_unit_roster import load_catalog


class Phase8LandRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.progression = json.loads((ROOT / "scenario/progression/catalog.json").read_text())
        cls.families = json.loads((ROOT / "scenario/rosters/global-roster-families.json").read_text())
        cls.phase8 = json.loads((ROOT / "scenario/rosters/phase8-land-rosters.json").read_text())

    def test_layers_roles_evidence_and_assignment_are_complete(self):
        units = [self.catalog.archetypes[x["id"]] for x in self.phase8["archetypes"]]
        self.assertEqual({"common", "regional", "polity", "elite"}, {x["rosterLayer"] for x in units})
        roles = set().union(*(set(x["roleIds"]) for x in units))
        self.assertEqual({"infantry", "ranged", "firearm", "cavalry", "artillery", "siege",
                          "engineer", "marine", "militia", "garrison", "specialist", "transport", "support"}, roles)
        assigned = {unit for _, unit in self.catalog.assignments}
        self.assertTrue({x["id"] for x in self.phase8["archetypes"]} <= assigned)
        self.assertGreaterEqual(len(self.phase8["historicalEvidence"]), 4)
        report = json.loads((ROOT / "scenario/rosters/reports/phase8-land-coverage.json").read_text())
        land = [x for x in self.catalog.generated_unit_data()
                if x["category"] in {"infantry", "cavalry", "artillery", "specialist", "marine"}]
        self.assertEqual((len(self.catalog.generated_unit_data()), len(land), len({p for p, _ in self.catalog.assignments}),
                          len(self.catalog.assignments)),
                         (report["catalog"]["totalArchetypes"], report["catalog"]["landArchetypes"],
                          report["catalog"]["coveredPolities"], report["catalog"]["assignmentPairs"]))
        self.assertEqual({x["id"] for x in self.phase8["historicalEvidence"]}, set(report["evidenceIds"]))

    def test_every_region_has_broad_shared_and_regional_coverage(self):
        common = set(self.families["sharedLandArchetypeIds"])
        self.assertGreaterEqual(len(common), 13)
        for family in self.families["families"]:
            roster = common | set(family["archetypeIds"])
            roles = set().union(*(set(self.catalog.archetypes[x].get("roleIds", ())) for x in roster))
            self.assertTrue({"infantry", "cavalry", "artillery", "siege", "engineer", "marine",
                             "militia", "garrison", "specialist", "transport", "support"} <= roles,
                            family["id"])

    def test_representative_era_resolution_is_deterministic_and_context_gated(self):
        tech = {x["id"] for x in self.progression["technologies"]}
        institutions = {x["id"] for x in self.progression["institutions"]}
        context = dict(established_institution_ids=institutions,
                       equipment_ids=set(self.phase8["equipment"]) | {"matchlock_firearm", "flintlock_musket", "naval_ordnance"},
                       reform_ids=set(self.phase8["reforms"]) | {"standing_army_reform", "permanent_naval_board", "kapikulu_recruitment", "timar_system"},
                       resource_ids=set(self.phase8["resources"]) | {"grain", "flour", "ship_provisions"}, has_port=True)
        assignments = {}
        for polity, unit in self.catalog.assignments:
            assignments.setdefault(polity, set()).add(unit)
        fixtures = [(1450, "england"), (1550, "ottoman_empire"), (1650, "ming_empire"),
                    (1750, "france"), (1820, "joseon_kingdom"), (1820, "tawantinsuyu")]
        for year, polity in fixtures:
            kwargs = dict(context, country_id=polity)
            first = self.catalog.resolve_roster(assignments[polity], year, tech, **kwargs)
            self.assertEqual(first, self.catalog.resolve_roster(assignments[polity], year, tech, **kwargs))
            self.assertGreaterEqual(len(first), 6, (year, polity, first))
        self.assertFalse(self.catalog.availability("common_reformed_militia", 1700, tech,
            country_id="france", equipment_ids=context["equipment_ids"], reform_ids=set(),
            resource_ids=context["resource_ids"], established_institution_ids=institutions).available)

    def test_upgrade_and_replacement_chains_span_early_and_late_eras(self):
        pairs = (("common_feudal_levy", "common_reformed_militia"),
                 ("common_bow_skirmishers", "common_light_infantry"),
                 ("common_early_bombard", "common_siege_battery"),
                 ("european_pike_company", "european_musket_battalion"))
        for old, new in pairs:
            self.assertIn(new, self.catalog.archetypes[old]["upgradeToIds"])
            self.assertIn(new, self.catalog.archetypes[old]["replacementIds"])
            self.assertLess(self.catalog.archetypes[old]["availability"]["historicalStartYear"],
                            self.catalog.archetypes[new]["availability"]["historicalStartYear"])


if __name__ == "__main__":
    unittest.main()
