import copy, importlib.util, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from settlement_catalogue import CatalogueError, normalized, project_lon_lat, stable_id, validate_catalogue
SPEC=importlib.util.spec_from_file_location("aos_catalogue_tool",ROOT/"tooling"/"settlement_catalogue.py")
tool=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(tool)

class SettlementCatalogueTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.rows,cls.refs=tool.load()
 def test_current_catalogue_and_report_are_complete_and_repeatable(self):
  report=tool.build_report(); world=json.loads((ROOT/"scenario/world/world.json").read_text())
  self.assertEqual(616,len(self.rows)); self.assertEqual(report,tool.build_report())
  self.assertEqual({x["id"] for x in self.rows},{x["id"] for x in world["settlements"]})
  self.assertEqual("foundation_only_not_density_complete",report["status"]); self.assertEqual(184,report["global"]["gapToMinimum"])
  self.assertEqual(report,json.loads((ROOT/"reports/settlement-coverage-baseline.json").read_text()))
 def test_coverage_profile_is_weighted_not_equal_quota(self):
  p=json.loads((ROOT/"scenario/settlements/release-scale-coverage.json").read_text()); mins=[x["target"]["minimum"] for x in p["regions"]]; maxs=[x["target"]["planningMaximum"] for x in p["regions"]]
  self.assertEqual((800,1200),(sum(mins),sum(maxs))); self.assertGreater(len(set(mins)),3); self.assertIn("never equal polity quotas",p["policy"])
 def test_stable_id_projection_and_normalization_helpers(self):
  self.assertEqual("sao_tome",stable_id("São Tomé")); first=stable_id("São Tomé",{"sao_tome"}); self.assertEqual(first,stable_id("São Tomé",{"sao_tome"}))
  self.assertEqual({"x":50.0,"y":50.0},project_lon_lat(0,0,{"minX":0,"maxX":100,"minY":0,"maxY":100})); self.assertEqual(normalized({"z":1,"a":[2]}),normalized({"a":[2],"z":1}))
 def test_abstract_minor_is_authoritative_without_object(self):
  row=copy.deepcopy(self.rows[0]); row.update(id="abstract_test",representation="abstract_minor",compressionRationale="Kept abstract because a local object adds no route or gameplay value."); row.pop("physicalMapId")
  self.assertEqual("abstract_minor",validate_catalogue([row],self.refs)[0]["representation"])
 def test_malformed_fixtures_cover_contract_failures(self):
  base=copy.deepcopy(self.rows[0]); cases=[([base,copy.deepcopy(base)],"duplicate")]
  mutations=[(lambda x:x["placement"].update(x=999),"coordinates"),(lambda x:x.update(polityId="unknown"),"unknown polity"),(lambda x:x.update(provinceId="unknown"),"unknown province"),(lambda x:x.update(physicalMapId="unknown"),"unknown physical map"),(lambda x:x["placement"].update(terrainClass="unknown"),"unknown terrain"),(lambda x:x["placement"].update(navigationZoneId="unknown"),"unknown navigation"),(lambda x:x.update(routeIds=["unknown_route"]),"unknown route"),(lambda x:x.update(roles=["inland","major_port"]),"contradictory"),(lambda x:(x.update(roles=["major_port"]),x.pop("port",None)),"lacks port"),(lambda x:x.update(evidence=[]),"missing evidence"),(lambda x:x.update(polityId=next(p for p in self.refs["polities"] if p!=x["polityId"])),"unsupported ownership")]
  for mutate,pattern in mutations: row=copy.deepcopy(base); mutate(row); cases.append(([row],pattern))
  port=copy.deepcopy(base); port["roles"]=["major_port"]; port["placement"]["terrainClass"]="plains"; port["port"]={"kind":"port","navigationZoneId":port["placement"]["navigationZoneId"]}; cases.append(([port],"invalid port"))
  for rows,pattern in cases:
   with self.subTest(pattern=pattern),self.assertRaisesRegex(CatalogueError,pattern): validate_catalogue(rows,self.refs)
if __name__=="__main__": unittest.main()
