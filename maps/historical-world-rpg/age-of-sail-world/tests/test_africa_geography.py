import copy, importlib.util, json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/geography/africa.json"
WORLD = ROOT / "scenario/world/world.json"
spec = importlib.util.spec_from_file_location("africa_geography", ROOT / "tooling/africa_geography.py")
geography = importlib.util.module_from_spec(spec); spec.loader.exec_module(geography)

class AfricaGeographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads(SOURCE.read_text()); cls.world=json.loads(WORLD.read_text())

    def test_coverage_global_references_and_determinism(self):
        instances, anchors = geography.validate(self.source, self.world)
        self.assertEqual((8, 27), (len(instances), len(anchors)))
        self.assertEqual({"africa_north","africa_east","africa_west"}, {a["globalAnchorId"] for a in anchors.values() if "globalAnchorId" in a})
        self.assertEqual(geography.generate(self.source,self.world), geography.generate(copy.deepcopy(self.source),copy.deepcopy(self.world)))

    def test_required_geography_has_single_authoritative_ownership(self):
        owned=[(f["id"],f["kind"]) for i in self.source["instances"] for f in i["features"]]
        self.assertEqual(len(owned),len({x[0] for x in owned}))
        declared={(feature_id,kind) for kind, ids in self.source["requiredFeatureIds"].items() for feature_id in ids}
        self.assertEqual(declared,set(owned))
        self.assertTrue({"lake","desert_barrier","strait","river","island"} <= set(self.source["requiredFeatureIds"]))

    def test_seams_movement_connectivity_distortions_and_budgets_are_enforced(self):
        broken=copy.deepcopy(self.source); broken["boundaryAnchors"][1]["source"][0] += 1; broken["boundaryAnchors"][1]["local"][0] += 2
        with self.assertRaisesRegex(geography.GeographyError,"seam discontinuity"): geography.validate(broken,self.world)
        broken=copy.deepcopy(self.source); broken["distortions"][0]["orientationDeltaDegrees"]=13
        with self.assertRaisesRegex(geography.GeographyError,"orientation exceeds"): geography.validate(broken,self.world)
        broken=copy.deepcopy(self.source); broken["instances"][0]["budget"]["maxFeatures"]=1
        with self.assertRaisesRegex(geography.GeographyError,"features exceed"): geography.validate(broken,self.world)
        broken=copy.deepcopy(self.source); broken["corridors"][0]["viaFeatureIds"]=["missing"]
        with self.assertRaisesRegex(geography.GeographyError,"feature reference"): geography.validate(broken,self.world)
        broken=copy.deepcopy(self.source); broken["boundaryAnchors"][0]["movementClasses"]=["teleport"]; broken["boundaryAnchors"][1]["movementClasses"]=["teleport"]
        with self.assertRaisesRegex(geography.GeographyError,"invalid movement classes"): geography.validate(broken,self.world)
        broken=copy.deepcopy(self.source); broken["corridors"][0]["movementClasses"]=["naval"]
        with self.assertRaisesRegex(geography.GeographyError,"endpoint movement classes"): geography.validate(broken,self.world)

    def test_global_land_and_maritime_graphs_are_connected(self):
        broken=copy.deepcopy(self.world)
        for edge in broken["regionalGeography"]["boundaries"]:
            if edge["id"] == "africa_middle_east_boundary":
                edge["movementClasses"].remove("land")
        with self.assertRaisesRegex(geography.GeographyError,"no global land connection"):
            geography.validate(self.source,broken)
        broken=copy.deepcopy(self.world)
        for edge in broken["regionalGeography"]["boundaries"] + broken["regionalGeography"]["routes"]:
            if edge["from"]["regionId"] == "africa" or edge["to"]["regionId"] == "africa":
                edge["movementClasses"]=[item for item in edge["movementClasses"] if item != "naval"]
        with self.assertRaisesRegex(geography.GeographyError,"no global naval connection"):
            geography.validate(self.source,broken)

    def test_trans_saharan_and_ocean_connections_are_explicit(self):
        ids={item["id"] for item in self.source["corridors"]}
        self.assertEqual({"corridor_western_trans_saharan","corridor_central_trans_saharan","corridor_red_sea","corridor_atlantic_coast","corridor_indian_ocean"},ids)
        maritime=[item for item in self.source["corridors"] if "naval" in item["movementClasses"]]
        self.assertEqual(3,len(maritime))

if __name__ == "__main__": unittest.main()
