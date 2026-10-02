import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
import progression_catalog
from technology_institutions import TechnologyInstitutionRuntime

CATALOG = json.loads((ROOT / "scenario/progression/catalog.json").read_text(encoding="utf-8"))
WORLD = json.loads((ROOT / "scenario/world/world.json").read_text(encoding="utf-8"))


class ProgressionCatalogTests(unittest.TestCase):
    def validate_mutation(self, mutate):
        data = copy.deepcopy(CATALOG); mutate(data)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(progression_catalog.CatalogError):
                progression_catalog.validate(path, require_projection=False)

    def test_complete_catalog_covers_required_domains_and_projects_exactly(self):
        data = progression_catalog.validate()
        self.assertEqual({"military","naval","commercial","administrative","scientific","agricultural","industrial","logistical","exploration","medical","communications","institutional"},
                         {x["id"] for x in data["branches"]})
        self.assertGreaterEqual(len(data["technologies"]), 180)
        self.assertLessEqual(len(data["technologies"]), 250)
        self.assertGreaterEqual(len(data["institutions"]), 20)
        self.assertLessEqual(len(data["institutions"]), 30)
        unlocks = {tuple(unlock) for node in data["technologies"] + data["institutions"] for unlock in node["unlocks"]}
        self.assertTrue({("unit","common_sapper_corps"), ("unit","common_wagon_train"),
                         ("unit","ocean_cruising_frigate"), ("unit","armed_indiaman"),
                         ("policy","provincial_governors"), ("ability","global_expedition")} <= unlocks)
        self.assertEqual(WORLD, progression_catalog.project(data, WORLD))
        self.assertEqual(len(WORLD["polities"]), len(WORLD["polityResearchStates"]))
        self.assertEqual(len(WORLD["provinces"]), len(WORLD["provinceAdoptionStates"]))

    def test_rejects_cycle_missing_unlock_invalid_date_and_impossible_start(self):
        self.validate_mutation(lambda d: d["technologies"][0].update(prerequisiteIds=["mass_army_logistics"]))
        self.validate_mutation(lambda d: d["technologies"][0]["unlocks"].append(["unit","undeclared_unit"]))
        self.validate_mutation(lambda d: d["technologies"][0].update(preferredYear=1900))
        self.validate_mutation(lambda d: d["startingState"]["polityProfiles"][0]["completedTechnologyIds"].append("linear_tactics"))

    def test_campaign_boundary_costs_are_finite_and_monotonic(self):
        runtime = TechnologyInstitutionRuntime(WORLD, "1450-01-01")
        for node in ("standardized_charts", "newtonian_science", "steam_navigation"):
            early = runtime.cost_units(node, "1450-01-01")
            preferred_year = next(x for x in WORLD["technologies"] if x["id"] == node)["timeCost"]["preferredYear"]
            normal = runtime.cost_units(node, f"{preferred_year}-01-01")
            late = runtime.cost_units(node, "1820-12-31")
            self.assertGreater(early, normal)
            self.assertEqual(normal, late)
            self.assertLess(early, 10**15)

    def test_deterministic_uneven_global_diffusion_and_accelerated_equivalence(self):
        province_ids = [x["id"] for x in WORLD["provinces"]]
        representatives = [province_ids[i] for i in range(0, len(province_ids), max(1, len(province_ids)//7))][:7]
        def run(step, repeats):
            runtime = TechnologyInstitutionRuntime(WORLD, "1450-01-01")
            for _ in range(repeats):
                for index, province in enumerate(representatives):
                    runtime.advance_adoption(province, "renaissance_humanism", step * (index + 1))
            return [runtime.adoption_units(x, "renaissance_humanism") for x in representatives]
        yearly = run(.01, 370)
        accelerated = run(.1, 37)
        self.assertEqual(yearly, accelerated)
        self.assertEqual(sorted(yearly), yearly)
        self.assertEqual(yearly, run(.01, 370))

    def test_multi_century_complete_catalog_research_matches_accelerated_time(self):
        empty = next(x["polityId"] for x in WORLD["polityResearchStates"]
                     if not x["completedTechnologyIds"] and not x["establishedInstitutionIds"])
        nodes = {x["id"]:x for x in WORLD["technologies"] + WORLD["institutions"]}
        def run(step):
            runtime = TechnologyInstitutionRuntime(WORLD, "1450-01-01")
            for year in list(range(1450, 1821, step)) + ([1820] if (1820-1450) % step else []):
                changed = True
                while changed:
                    changed = False
                    completed = set(runtime.completed(empty))
                    for ident, node in sorted(nodes.items()):
                        if ident not in completed and node["timeCost"]["preferredYear"] <= year and set(node["prerequisiteIds"]) <= completed:
                            points = runtime.cost_units(ident, f"{year}-01-01") / 1_000_000
                            runtime.advance_research(empty, ident, points, f"{year}-01-01")
                            changed = True; break
            return runtime.completed(empty)
        yearly = run(1)
        self.assertEqual(tuple(sorted(nodes)), yearly)
        self.assertEqual(yearly, run(10))

    def test_every_branch_has_era_depth_and_cross_tree_dependencies(self):
        nodes = CATALOG["technologies"] + CATALOG["institutions"]
        by_id = {x["id"]: x for x in nodes}
        for branch in {x["id"] for x in CATALOG["branches"]}:
            branch_nodes = [x for x in nodes if x["branchId"] == branch]
            self.assertGreaterEqual(len(branch_nodes), 4, branch)
            self.assertGreaterEqual(max(x["preferredYear"] for x in branch_nodes) - min(x["preferredYear"] for x in branch_nodes), 100, branch)
        cross_tree = [x for x in nodes if any(by_id[p]["branchId"] != x["branchId"] for p in x["prerequisiteIds"])]
        self.assertGreaterEqual(len(cross_tree), 20)


if __name__ == "__main__":
    unittest.main()
