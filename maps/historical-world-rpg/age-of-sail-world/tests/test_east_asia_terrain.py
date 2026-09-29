import copy, importlib.util, json, sys, unittest
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]; SHARED=PROJECT.parent/"_shared"; SOURCE=PROJECT/"scenario/terrain/east-asia.json"; GEOGRAPHY=PROJECT/"scenario/geography/east_asia.json"; WORLD=PROJECT/"scenario/world/world.json"
spec=importlib.util.spec_from_file_location("east_asia_terrain_generator",SHARED/"tooling/generate_regional_terrain.py"); generator=importlib.util.module_from_spec(spec); sys.modules[spec.name]=generator; spec.loader.exec_module(generator)

class EastAsiaTerrainTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=json.loads(SOURCE.read_text()); cls.geography=json.loads(GEOGRAPHY.read_text()); cls.regional=json.loads(WORLD.read_text())["regionalGeography"]
 def generate(self,source=None,authority=None): return generator.generate(copy.deepcopy(source or self.source),copy.deepcopy(self.regional),copy.deepcopy(authority or self.geography))
 def test_clean_generation_is_deterministic_normalized_and_complete(self):
  first=generator.canonical_bytes(self.generate()); second=generator.canonical_bytes(self.generate()); self.assertEqual(first,second); self.assertEqual(b"\n",first[-1:])
  result=json.loads(first); self.assertEqual({x["id"] for x in self.geography["instances"]},{x["id"] for x in result["instances"]}); self.assertEqual(6,result["statistics"]["instanceCount"])
 def test_authoritative_features_surfaces_and_map_scoped_budgets(self):
  generated={x["id"]:x for x in self.generate()["instances"]}
  for owner in self.geography["instances"]:
   item=generated[owner["id"]]; self.assertEqual([x["id"] for x in owner["features"]],[x["id"] for x in item["features"]]); self.assertGreater(item["surfaceCounts"]["land"],0)
   if owner["complexity"]["waterBodies"]: self.assertGreater(item["surfaceCounts"]["navigable_sea"],0)
   policy=next(x for x in self.source["instancePolicies"] if x["id"]==item["id"]); self.assertLessEqual(item["statistics"]["cellCount"],policy["budget"]["maximumCells"]); self.assertLessEqual(item["statistics"]["outputBytes"],policy["budget"]["maximumOutputBytes"])
  self.assertGreater(sum(x["surfaceCounts"]["decorative_water"] for x in generated.values()),0)
 def test_features_retain_authoritative_transform_orientation_and_adjacency(self):
  generated={x["id"]:x for x in self.generate()["instances"]}
  for owner in self.geography["instances"]:
   actual={x["id"]:x for x in generated[owner["id"]]["features"]}
   origin=owner["transform"]["sourceOrigin"]; scale=owner["transform"]["scale"]; offset=owner["transform"]["offset"]
   for feature in owner["features"]:
    expected=[[round((p[0]-origin[0])*scale[0]+offset[0],2),round((p[1]-origin[1])*scale[1]+offset[1],2)] for p in feature["points"]]
    self.assertEqual(expected,actual[feature["id"]]["points"])
 def test_movement_corridors_straits_island_routes_and_barriers(self):
  graph=self.generate()["navigation"]["connectivity"]
  for corridor in self.geography["requiredTraversalConnections"]:
   for movement in corridor["movementClasses"]: self.assertIn(corridor["toNodeId"],graph[movement][corridor["fromNodeId"]],corridor["id"])
  for movement in ("land","naval","amphibious"):
   self.assertEqual(["node_tibetan_barrier"],graph[movement]["node_tibetan_barrier"]); self.assertEqual(["node_gobi_isolated_water"],graph[movement]["node_gobi_isolated_water"]); self.assertEqual(["node_isolated_crater_lake"],graph[movement]["node_isolated_crater_lake"])
  self.assertIn("node_north_pacific",graph["naval"]["node_east_china_sea"]); self.assertIn("node_japan_coast",graph["amphibious"]["node_korea_land"])
 def test_every_seam_and_external_entry_is_deterministic_and_valid(self):
  anchors={x["id"]:x for x in self.generate()["transitionAnchors"]}
  for anchor in anchors.values():
   if anchor.get("pairId"): self.assertEqual(anchor["source"],anchors[anchor["pairId"]]["source"]); self.assertEqual(anchor["movementClasses"],anchors[anchor["pairId"]]["movementClasses"])
  self.assertEqual({"east_asia_west","east_asia_south","east_asia_east"},{x["globalAnchorId"] for x in anchors.values() if x.get("globalAnchorId")})
 def test_stale_or_invalid_authority_and_budgets_are_rejected(self):
  broken=copy.deepcopy(self.geography); broken["boundaryAnchors"][0]["source"]=[0,0]
  with self.assertRaisesRegex(generator.TerrainGenerationError,"seam correspondence"): self.generate(authority=broken)
  broken=copy.deepcopy(self.source); broken["instancePolicies"][0]["budget"]["maximumCells"]=1
  with self.assertRaisesRegex(generator.TerrainGenerationError,"east_asia_interior: cells budget exceeded"): self.generate(source=broken)

if __name__=="__main__": unittest.main()
