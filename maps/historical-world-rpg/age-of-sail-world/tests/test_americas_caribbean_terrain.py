import copy, importlib.util, json, sys, time, unittest
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]; SHARED=PROJECT.parent/"_shared"
SOURCE=PROJECT/"scenario/terrain/americas-caribbean.json"; GEOGRAPHY=PROJECT/"scenario/geography/americas_caribbean.json"
WORLD=PROJECT/"scenario/world/world.json"; MAPS=PROJECT/"physical-maps.json"
spec=importlib.util.spec_from_file_location("americas_terrain_generator",SHARED/"tooling/generate_regional_terrain.py")
generator=importlib.util.module_from_spec(spec); sys.modules[spec.name]=generator; spec.loader.exec_module(generator)

class AmericasCaribbeanTerrainTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=json.loads(SOURCE.read_text()); cls.geography=json.loads(GEOGRAPHY.read_text())
  cls.regional=json.loads(WORLD.read_text())["regionalGeography"]; cls.maps=json.loads(MAPS.read_text())
 def generate(self,source=None,authority=None): return generator.generate(copy.deepcopy(source or self.source),copy.deepcopy(self.regional),copy.deepcopy(authority or self.geography))
 def test_clean_generation_is_deterministic_normalized_complete_and_fast(self):
  started=time.perf_counter(); first=generator.canonical_bytes(self.generate()); elapsed=(time.perf_counter()-started)*1000
  self.assertEqual(first,generator.canonical_bytes(self.generate())); self.assertEqual(b"\n",first[-1:]); self.assertLess(elapsed,self.source["budgets"]["maximumGenerationMilliseconds"])
  result=json.loads(first); self.assertEqual({x["id"] for x in self.geography["instances"]},{x["id"] for x in result["instances"]}); self.assertEqual(8,result["statistics"]["instanceCount"])
 def test_authoritative_features_surfaces_and_map_scoped_budgets(self):
  generated={x["id"]:x for x in self.generate()["instances"]}
  policies={x["id"]:x for x in self.source["instancePolicies"]}
  for owner in self.geography["instances"]:
   item=generated[owner["id"]]; policy=policies[item["id"]]
   self.assertEqual([x["id"] for x in owner["features"]],[x["id"] for x in item["features"]]); self.assertGreater(item["surfaceCounts"]["navigable_sea"],0)
   self.assertLessEqual(item["statistics"]["cellCount"],policy["budget"]["maximumCells"]); self.assertLessEqual(item["statistics"]["outputBytes"],policy["budget"]["maximumOutputBytes"])
  self.assertGreater(sum(x["surfaceCounts"]["land"] for x in generated.values()),0); self.assertGreater(sum(x["surfaceCounts"]["decorative_water"] for x in generated.values()),0)
  for physical in self.maps["physicalMaps"]:
   assigned=physical["assignments"]["regionalInstanceIds"]
   cells=sum(generated[x]["statistics"]["cellCount"] for x in assigned if x in generated)
   output=sum(generated[x]["statistics"]["outputBytes"] for x in assigned if x in generated)
   self.assertLessEqual(cells,physical["terrainBudget"]["maximumCells"],physical["id"]); self.assertLessEqual(output,physical["terrainBudget"]["maximumOutputBytes"],physical["id"])
 def test_landmarks_orientation_adjacency_and_coastlines_retain_authority(self):
  generated={x["id"]:x for x in self.generate()["instances"]}
  for owner in self.geography["instances"]:
   actual={x["id"]:x for x in generated[owner["id"]]["features"]}; origin=owner["transform"]["sourceOrigin"]; scale=owner["transform"]["scale"]; offset=owner["transform"]["offset"]
   for feature in owner["features"]:
    expected=[[round((p[0]-origin[0])*scale[0]+offset[0],2),round((p[1]-origin[1])*scale[1]+offset[1],2)] for p in feature["points"]]
    self.assertEqual(expected,actual[feature["id"]]["points"])
 def test_all_movement_corridors_passages_rivers_islands_and_barriers(self):
  graph=self.generate()["navigation"]["connectivity"]
  self.assertEqual({"land","naval","amphibious","flying"},set(graph))
  for corridor in self.geography["requiredTraversalConnections"]:
   for movement in corridor["movementClasses"]: self.assertIn(corridor["toNodeId"],graph[movement][corridor["fromNodeId"]],corridor["id"])
  for movement in graph:
   for node in ("node_rockies_barrier","node_andes_barrier","node_isolated_crater_lake"): self.assertEqual([node],graph[movement][node])
  self.assertIn("node_caribbean_islands",graph["naval"]["node_north_atlantic"]); self.assertIn("node_magellan_sea",graph["naval"]["node_north_pacific"])
 def test_seams_and_cross_region_entries_are_aligned_valid_and_deterministic(self):
  anchors={x["id"]:x for x in self.generate()["transitionAnchors"]}
  for anchor in anchors.values():
   if anchor.get("pairId"):
    pair=anchors[anchor["pairId"]]; self.assertEqual(anchor["source"],pair["source"]); self.assertEqual(anchor["movementClasses"],pair["movementClasses"])
  self.assertEqual({"americas_caribbean_east","americas_caribbean_west"},{x["globalAnchorId"] for x in anchors.values() if x.get("globalAnchorId")})
 def test_stale_authority_invalid_seams_and_budgets_are_rejected(self):
  broken=copy.deepcopy(self.geography); paired=next(x for x in broken["boundaryAnchors"] if x.get("pairId")); paired["source"]=[0,0]
  with self.assertRaisesRegex(generator.TerrainGenerationError,"seam correspondence"): self.generate(authority=broken)
  broken=copy.deepcopy(self.source); broken["instancePolicies"][0]["budget"]["maximumCells"]=1
  with self.assertRaisesRegex(generator.TerrainGenerationError,"americas_north_atlantic: cells budget exceeded"): self.generate(source=broken)

if __name__=="__main__": unittest.main()
