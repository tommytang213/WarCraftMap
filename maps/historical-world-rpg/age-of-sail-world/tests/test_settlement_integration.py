import copy, importlib.util, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from settlement_integration import SettlementIntegrationError, SettlementIntegrationRuntime, REQUIRED_ROLES, validate_manifest
SPEC=importlib.util.spec_from_file_location("integration_tool",ROOT/"tooling/settlement_integration.py")
tool=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(tool)


class SettlementIntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.manifest=tool.build_manifest(); cls.rows=validate_manifest(cls.manifest)

 def test_all_authoritative_settlements_have_every_gameplay_role(self):
  report=tool.build_report(self.manifest); world=json.loads((ROOT/"scenario/world/world.json").read_text())
  self.assertEqual(len(world["settlements"]),len(self.rows)); self.assertEqual({x["id"] for x in world["settlements"]},set(self.rows))
  self.assertEqual("pass",report["status"]); self.assertEqual(0,report["inertSettlements"])
  self.assertFalse(report["roadmapDensityComplete"])
  self.assertEqual(report,json.loads((ROOT/"reports/settlement-integration.json").read_text()))
  for row in self.rows.values(): self.assertEqual(REQUIRED_ROLES,set(row["gameplayRoles"]))

 def test_generated_officials_are_unique_cultural_and_repeatable(self):
  second=tool.build_manifest(); a={x["settlementId"]:x["official"] for x in self.manifest["settlements"]}; b={x["settlementId"]:x["official"] for x in second["settlements"]}
  self.assertEqual(a,b); self.assertEqual(len(a),len({x["characterId"] for x in a.values()})); self.assertEqual(len(a),len({x["displayName"] for x in a.values()}))
  self.assertTrue(all(" of " in x["displayName"] and x["culturePoolId"] in tool.NAME_POOLS for x in a.values()))

 def test_activation_retirement_capture_save_reconstruction_and_recovery(self):
  runtime=SettlementIntegrationRuntime(self.manifest); made=[]
  active=runtime.activate("pacific",lambda sid,kind,state: made.append((sid,kind,state["revision"])) or object())
  expected=sum(len(x["physicalRepresentationKinds"]) for x in self.rows.values() if x["regionId"]=="pacific")
  self.assertEqual(expected,len(active)); self.assertEqual(expected,runtime.active_object_count)
  inactive=next(x for x in self.rows if self.rows[x]["regionId"]!="pacific")
  runtime.simulate(inactive,"inactive",30); before=runtime.snapshot(); self.assertEqual(expected,runtime.active_object_count)
  capturable=next(x for x in self.rows if self.rows[x]["captureModel"]=="city_core")
  legal=runtime.state[capturable]["legalOwnerPolityId"]; captured=runtime.capture(capturable,"test_controller")
  self.assertEqual(legal,captured["legalOwnerPolityId"]); self.assertEqual("test_controller",captured["controllerPolityId"])
  saved=runtime.snapshot(); restored=SettlementIntegrationRuntime(self.manifest); restored.restore(saved); self.assertEqual(saved,restored.snapshot())
  old=copy.deepcopy(before); old["settlements"].pop(next(iter(old["settlements"])))
  restored.restore(old); self.assertEqual(len(self.rows),len(restored.state))
  runtime.retire(); self.assertEqual(0,runtime.active_object_count)

 def test_representative_conditions_and_budget_fail_transactionally(self):
  runtime=SettlementIntegrationRuntime(self.manifest); sid=next(iter(self.rows))
  values={condition:runtime.simulate(sid,condition,10)["growthPermille"] for condition in ("peaceful","wartime","captured","blockaded","isolated","growing","inactive")}
  self.assertGreater(values["growing"],values["blockaded"])
  tiny=SettlementIntegrationRuntime(self.manifest,maximum_active_objects=1)
  with self.assertRaisesRegex(SettlementIntegrationError,"budget"): tiny.activate(self.rows[sid]["regionId"],lambda *args:object())
  self.assertEqual(0,tiny.active_object_count)

 def test_missing_role_impossible_market_and_non_capturable_are_enforced(self):
  broken=copy.deepcopy(self.manifest); del broken["settlements"][0]["gameplayRoles"]["ai"]
  with self.assertRaisesRegex(SettlementIntegrationError,"missing gameplay roles"): validate_manifest(broken)
  broken=copy.deepcopy(self.manifest); broken["settlements"][0]["economy"]["availableGoodIds"]=[]
  with self.assertRaisesRegex(SettlementIntegrationError,"impossible market"): validate_manifest(broken)
  runtime=SettlementIntegrationRuntime(self.manifest); sid=next(x for x in self.rows if self.rows[x]["captureModel"]=="non_capturable")
  with self.assertRaisesRegex(SettlementIntegrationError,"non-capturable"): runtime.capture(sid,"other")


if __name__=="__main__": unittest.main()
