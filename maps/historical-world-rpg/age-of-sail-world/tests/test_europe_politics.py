import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tooling")); sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from validate_europe_politics import ValidationError,validate
from diplomacy import DiplomacyRuntime,DiplomacySaveAdapter
from polity import PolityRuntime
from province import ProvinceRuntime


class EuropePoliticsTests(unittest.TestCase):
 def setUp(self):
  self.path=ROOT/"scenario/politics/europe-1450.json"; self.world=json.loads((ROOT/"scenario/world/world.json").read_text()); self.data=json.loads(self.path.read_text())
 def test_authoritative_baseline_and_world_projection_validate(self):
  result=validate(self.path)
  self.assertEqual((49,62,2),(len(result["polities"]),sum(len(x["provinces"]) for x in result["polities"]),len(result["activeConflicts"])))
 def test_overlap_missing_geography_and_hierarchy_cycles_are_rejected(self):
  cases=[]
  overlap=copy.deepcopy(self.data); overlap["polities"][1]["provinces"].append(copy.deepcopy(overlap["polities"][0]["provinces"][0])); cases.append((overlap,"overlaps"))
  feature=copy.deepcopy(self.data); feature["polities"][0]["geographicFeatureIds"]=["modern_border"]; cases.append((feature,"missing geographic feature"))
  cycle=copy.deepcopy(self.data); cycle["vassalage"].append({"id":"england_vassalage","subjectPolityId":"england","overlordPolityId":"ireland"}); cases.append((cycle,"cycle"))
  with tempfile.TemporaryDirectory() as tmp:
   for candidate,pattern in cases:
    path=Path(tmp)/"candidate.json"; path.write_text(json.dumps(candidate))
    with self.subTest(pattern=pattern),self.assertRaisesRegex(ValidationError,pattern): validate(path,ROOT/"scenario/world/world.json",ROOT/"scenario/geography/europe.json")
 def test_seeded_diplomacy_is_deterministic_and_persistent(self):
  polities=PolityRuntime(self.world); provinces=ProvinceRuntime(self.world,polities)
  first=DiplomacyRuntime(polities,provinces,initial_conflicts=self.data["activeConflicts"]); second=DiplomacyRuntime(polities,provinces,initial_conflicts=self.data["activeConflicts"])
  self.assertEqual(first.snapshot(),second.snapshot()); self.assertEqual("war",first.relation("england","france")); self.assertEqual("war",first.relation("ottoman_empire","byzantine_empire"))
  saved=DiplomacySaveAdapter(first,{"calendar":{"day":1}}).capture_world(); restored=DiplomacyRuntime(polities,provinces); restored.restore(saved["diplomacyState"])
  self.assertEqual(first.snapshot(),restored.snapshot())


if __name__=="__main__": unittest.main()
