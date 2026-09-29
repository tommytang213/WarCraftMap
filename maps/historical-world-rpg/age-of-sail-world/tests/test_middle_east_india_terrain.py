import copy, importlib.util, json, sys, time, unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]; SHARED=PROJECT.parent/"_shared"; SOURCE=PROJECT/"scenario/terrain/middle-east-india.json"; GEOGRAPHY=PROJECT/"scenario/geography/middle-east-india.json"; WORLD=PROJECT/"scenario/world/world.json"
spec=importlib.util.spec_from_file_location("mei_generator",SHARED/"tooling/generate_regional_terrain.py"); generator=importlib.util.module_from_spec(spec); sys.modules[spec.name]=generator; spec.loader.exec_module(generator)
class MiddleEastIndiaTerrainTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.source=json.loads(SOURCE.read_text()); cls.geography=json.loads(GEOGRAPHY.read_text()); cls.regional=json.loads(WORLD.read_text())["regionalGeography"]
 def generate(self): return generator.generate(copy.deepcopy(self.source),copy.deepcopy(self.regional))
 @staticmethod
 def cells(r): return [v for v,n in r["surfaceEncoding"]["runs"] for _ in range(n)]
 def test_clean_generation_is_byte_deterministic_and_normalized(self):
  a=generator.canonical_bytes(self.generate()); b=generator.canonical_bytes(self.generate()); self.assertEqual(a,b); self.assertEqual(json.loads(a),json.loads(b)); self.assertEqual(b"\n",a[-1:])
 def test_landmarks_match_authority_within_tolerance(self):
  r=self.generate(); cells=self.cells(r); legend=r["surfaceEncoding"]["legend"]; w,h=r["grid"]["width"],r["grid"]["height"]
  for mark in r["landmarks"]:
   x,y=generator._cell(self.source,mark["at"]); t=mark["toleranceCells"]; nearby=[cells[cy*w+cx] for cy in range(max(0,y-t),min(h,y+t+1)) for cx in range(max(0,x-t),min(w,x+t+1))]; self.assertIn(legend[mark["expectedSurface"]],nearby,mark["id"])
  self.assertGreater(r["surfaceCounts"]["land"],4000); self.assertGreater(r["surfaceCounts"]["navigable_sea"],3000); self.assertGreater(r["surfaceCounts"]["decorative_water"],50)
 def test_corridors_barriers_straits_crossings_and_isolated_water(self):
  r=self.generate(); f={x["id"]:x for x in r["features"]["linear"]}; required=self.geography["requiredFeatureIds"]
  self.assertEqual(set(required["coastline"]),{k for k,v in f.items() if v["kind"]=="coastline"}); self.assertEqual(set(required["island"]),{x["id"] for x in self.source["surfaces"] if x["id"] in required["island"]})
  self.assertEqual(set(required["river"]),{k for k,v in f.items() if v["kind"]=="river"}); self.assertEqual(set(required["mountain_barrier"]),{k for k,v in f.items() if v["kind"]=="mountain_barrier"}); self.assertEqual(set(required["traversal_corridor"]),{k for k,v in f.items() if v["kind"]=="traversal_corridor"}); self.assertEqual(set(required["strait"]),{x["id"] for x in r["features"]["chokepoints"]}); self.assertEqual(4,len(r["features"]["crossings"])); naval=r["navigation"]["connectivity"]["naval"]; self.assertIn("black_sea_navigation",naval["mediterranean_navigation"]); self.assertIn("bay_of_bengal_navigation",naval["red_sea_navigation"]); self.assertNotIn("isolated_inland_water",naval)
 def test_all_movement_classes_and_cross_region_seams(self):
  r=self.generate(); graph=r["navigation"]["connectivity"]; self.assertEqual({"land","naval","amphibious","flying"},set(graph)); self.assertIn("southeast_asia_transition",graph["land"]["europe_transition"]); self.assertIn("southeast_asia_transition",graph["naval"]["africa_transition"]); runtime={x["id"]:x for x in self.regional["anchors"]}; self.assertEqual({"europe","africa","southeast_asia"},{x["neighborRegionId"] for x in r["transitionAnchors"]})
  for anchor in r["transitionAnchors"]:
   target=runtime[anchor.get("runtimeAnchorId",anchor["id"])]; self.assertEqual("middle_east_india",target["regionId"]); self.assertTrue(set(anchor["movementClasses"])<=set(target["movementClasses"]));
   if "runtimeAnchorId" not in anchor: self.assertEqual(anchor["at"],[target["position"]["x"],target["position"]["y"]])
 def test_budgets_and_invalid_topology_are_enforced(self):
  start=time.perf_counter(); r=self.generate(); self.assertLess((time.perf_counter()-start)*1000,self.source["budgets"]["maximumGenerationMilliseconds"]); self.assertLessEqual(r["statistics"]["encodedRuns"],self.source["budgets"]["maximumEncodedRuns"]); broken=copy.deepcopy(self.source); broken["transitionAnchors"][0]["zoneId"]="missing"
  with self.assertRaisesRegex(generator.TerrainGenerationError,"zone is missing"): generator.generate(broken,self.regional)
  broken=copy.deepcopy(self.source); broken["chokepoints"][0]["connects"][0]="missing"
  with self.assertRaisesRegex(generator.TerrainGenerationError,"water bodies"): generator.generate(broken,self.regional)
if __name__=="__main__": unittest.main()
