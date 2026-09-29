import copy, importlib.util, json, sys, tempfile, unittest
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]; SHARED=PROJECT.parent/"_shared"; SOURCE=PROJECT/"scenario/terrain/southeast-asia.json"; GEOGRAPHY=PROJECT/"scenario/geography/southeast_asia.json"; WORLD=PROJECT/"scenario/world/world.json"
spec=importlib.util.spec_from_file_location("sea_generator",SHARED/"tooling/generate_regional_terrain.py"); generator=importlib.util.module_from_spec(spec); sys.modules[spec.name]=generator; spec.loader.exec_module(generator)

class SoutheastAsiaTerrainTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=json.loads(SOURCE.read_text()); cls.geography=json.loads(GEOGRAPHY.read_text()); cls.regional=json.loads(WORLD.read_text())["regionalGeography"]
 def generate(self,source=None,authority=None): return generator.generate(copy.deepcopy(source or self.source),copy.deepcopy(self.regional),copy.deepcopy(authority or self.geography))
 def test_clean_generation_is_deterministic_normalized_and_complete(self):
  a=generator.canonical_bytes(self.generate()); b=generator.canonical_bytes(self.generate()); self.assertEqual(a,b); self.assertEqual(b"\n",a[-1:])
  result=json.loads(a); self.assertEqual({x["id"] for x in self.geography["instances"]},{x["id"] for x in result["instances"]}); self.assertEqual(7,result["statistics"]["instanceCount"])
 def test_authoritative_features_ordering_surfaces_and_budgets(self):
  result=self.generate(); generated={x["id"]:x for x in result["instances"]}
  for source_instance in self.geography["instances"]:
   item=generated[source_instance["id"]]; self.assertEqual([x["id"] for x in source_instance["features"]],[x["id"] for x in item["features"]]); self.assertGreater(item["surfaceCounts"]["land"],0); self.assertGreater(item["surfaceCounts"]["navigable_sea"],0)
   policy=next(x for x in self.source["instancePolicies"] if x["id"]==item["id"]); self.assertLessEqual(item["statistics"]["cellCount"],policy["budget"]["maximumCells"]); self.assertLessEqual(item["statistics"]["encodedRuns"],policy["budget"]["maximumEncodedRuns"])
  self.assertGreater(sum(x["surfaceCounts"]["decorative_water"] for x in generated.values()),0)
 def test_movement_routes_barriers_and_named_long_distance_routes(self):
  nav=self.generate()["navigation"]; graph=nav["connectivity"]
  for corridor in self.geography["requiredTraversalConnections"]:
   for movement in corridor["movementClasses"]: self.assertIn(corridor["toNodeId"],graph[movement][corridor["fromNodeId"]],corridor["id"])
  for movement in ("land","naval","amphibious"):
   self.assertEqual(["node_arakan_barrier"],graph[movement]["node_arakan_barrier"]); self.assertEqual(["node_decorative_inland_water"],graph[movement]["node_decorative_inland_water"])
 def test_seams_and_external_entries_are_deterministic(self):
  anchors={x["id"]:x for x in self.generate()["transitionAnchors"]}
  for anchor in anchors.values():
   if anchor.get("pairId"): self.assertEqual(anchor["source"],anchors[anchor["pairId"]]["source"])
  self.assertEqual({"southeast_asia_west","southeast_asia_north","southeast_asia_east"},{x["globalAnchorId"] for x in anchors.values() if x.get("globalAnchorId")})
 def test_invalid_authority_and_map_scoped_budgets_are_rejected(self):
  broken=copy.deepcopy(self.geography); broken["boundaryAnchors"][0]["source"]=[0,0]
  with self.assertRaisesRegex(generator.TerrainGenerationError,"seam correspondence"): self.generate(authority=broken)
  broken=copy.deepcopy(self.source); broken["instancePolicies"][0]["budget"]["maximumCells"]=1
  with self.assertRaisesRegex(generator.TerrainGenerationError,"sea_mainland: cells budget exceeded"): self.generate(source=broken)

if __name__=="__main__": unittest.main()
