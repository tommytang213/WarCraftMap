import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tooling")); sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from validate_africa_politics import ValidationError,validate
from diplomacy import DiplomacyRuntime,DiplomacySaveAdapter
from polity import PolityRuntime
from province import ProvinceRuntime


class AfricaPoliticsTests(unittest.TestCase):
 def setUp(self):
  self.path=ROOT/"scenario/politics/africa-1450.json"; self.world=json.loads((ROOT/"scenario/world/world.json").read_text()); self.data=json.loads(self.path.read_text())
 def test_authoritative_baseline_and_world_projection_validate(self):
  result=validate(self.path)
  self.assertEqual((47,65,0),(len(result["polities"]),sum(len(x["provinces"]) for x in result["polities"]),len(result["activeConflicts"])))
 def test_overlap_missing_geography_and_hierarchy_cycles_are_rejected(self):
  cases=[]
  overlap=copy.deepcopy(self.data); overlap["polities"][1]["provinces"].append(copy.deepcopy(overlap["polities"][0]["provinces"][0])); cases.append((overlap,"overlaps"))
  feature=copy.deepcopy(self.data); feature["polities"][0]["geographicFeatureIds"]=["modern_border"]; cases.append((feature,"missing geographic feature"))
  cycle=copy.deepcopy(self.data); cycle["vassalage"].append({"id":"ethiopia_vassalage","subjectPolityId":"ethiopian_empire","overlordPolityId":"medri_bahri"}); cases.append((cycle,"cycle"))
  with tempfile.TemporaryDirectory() as tmp:
   for candidate,pattern in cases:
    path=Path(tmp)/"candidate.json"; path.write_text(json.dumps(candidate))
    with self.subTest(pattern=pattern),self.assertRaisesRegex(ValidationError,pattern): validate(path,ROOT/"scenario/world/world.json",ROOT/"scenario/geography/africa.json")
 def test_capitals_reachability_tributaries_and_conflicts_are_validated(self):
  cases=[]
  capital=copy.deepcopy(self.data); capital["polities"][0]["capitalSettlementId"]="missing_capital"; cases.append((capital,"capital"))
  reach=copy.deepcopy(self.data); reach["polities"][0]["provinces"][0]["adjacentProvinceIds"]=[]; cases.append((reach,"unreachable"))
  tribute=copy.deepcopy(self.data); tribute["tributaryRelations"][0]["taxRatePercent"]=0; cases.append((tribute,"obligation"))
  conflict=copy.deepcopy(self.data); conflict["activeConflicts"].append({"id":"invalid_war","attackerPolityIds":["mali_empire"],"defenderPolityIds":["missing_polity"],"startDate":"1450-01-01"}); cases.append((conflict,"inactive participants"))
  with tempfile.TemporaryDirectory() as tmp:
   for candidate,pattern in cases:
    path=Path(tmp)/"candidate.json"; path.write_text(json.dumps(candidate))
    with self.subTest(pattern=pattern),self.assertRaisesRegex(ValidationError,pattern): validate(path,ROOT/"scenario/world/world.json",ROOT/"scenario/geography/africa.json")
 def test_seeded_diplomacy_is_deterministic_and_persistent(self):
  polities=PolityRuntime(self.world); provinces=ProvinceRuntime(self.world,polities)
  first=DiplomacyRuntime(polities,provinces,initial_conflicts=self.data["activeConflicts"]); second=DiplomacyRuntime(polities,provinces,initial_conflicts=self.data["activeConflicts"])
  self.assertEqual(first.snapshot(),second.snapshot()); self.assertEqual("neutral",first.relation("marinid_morocco","mali_empire")); self.assertEqual("neutral",first.relation("ethiopian_empire","adal_sultanate"))
  saved=DiplomacySaveAdapter(first,{"calendar":{"day":1}}).capture_world(); restored=DiplomacyRuntime(polities,provinces); restored.restore(saved["diplomacyState"])
  self.assertEqual(first.snapshot(),restored.snapshot())


if __name__=="__main__": unittest.main()
