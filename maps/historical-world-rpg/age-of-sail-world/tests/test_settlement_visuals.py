import copy, importlib.util, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SHARED=ROOT.parent/"_shared"
sys.path.insert(0,str(SHARED/"engine"))
from settlement_visuals import SettlementVisualRuntime, SettlementVisualRuntimeError
spec=importlib.util.spec_from_file_location("build_settlement_visuals",ROOT/"tooling/build_settlement_visuals.py")
builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)

class SettlementVisualTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/"scenario/visuals/settlement-building-sets.json").read_text())
        self.catalogue=json.loads((SHARED/"assets/warcraft-3.0-stock.json").read_text())

    def test_generated_sources_and_structural_previews_are_deterministic(self):
        self.assertEqual(builder.build(),self.data); self.assertTrue(builder.validate(self.data,self.catalogue))
        report=json.loads((ROOT/"scenario/visuals/reports/settlement-placement-manifests.json").read_text())
        self.assertEqual(builder.placements(self.data),report); self.assertTrue(report)

    def test_complete_world_and_defense_coverage_with_all_regions_and_roles(self):
        world=json.loads((ROOT/"scenario/world/world.json").read_text())
        self.assertEqual({x["id"] for x in world["settlements"]},{x["settlementId"] for x in self.data["settlementAssignments"]})
        self.assertEqual({x["id"] for x in world["defenseLayouts"]},{x["defenseLayoutId"] for x in self.data["defenseLayoutAssignments"]})
        self.assertEqual(set(builder.REGIONS),{x["regionId"] for x in self.data["visualSets"]})
        self.assertEqual(set(builder.ROLE_TEMPLATES),{x["role"] for s in self.data["visualSets"] for x in s["roleVisuals"]})

    def test_validator_rejects_coverage_navigation_footprints_and_placeholders(self):
        cases=[]
        bad=copy.deepcopy(self.data); bad["settlementAssignments"].pop(); cases.append((bad,"coverage"))
        bad=copy.deepcopy(self.data); bad["defenseLayoutAssignments"].pop(); cases.append((bad,"defense layout"))
        bad=copy.deepcopy(self.data); bad["settlementAssignments"][0]["visualSetId"]="absent"; cases.append((bad,"visual set"))
        bad=copy.deepcopy(self.data); bad["visualSets"][0]["roleVisuals"][0]["footprintCells"]=0; cases.append((bad,"footprint"))
        bad=copy.deepcopy(self.data); bad["settlementAssignments"][0]["portAccess"]={"access":"coastal"}; bad["settlementAssignments"][0]["terrainClass"]="plains"; cases.append((bad,"inland port"))
        for data,message in cases:
            with self.subTest(message=message),self.assertRaisesRegex(builder.SettlementVisualError,message): builder.validate(data,self.catalogue)

    def test_capture_growth_destruction_loss_and_reconstruction_use_stable_state(self):
        runtime=SettlementVisualRuntime(self.data)
        sid=next(x["settlementId"] for x in self.data["settlementAssignments"] if {"city_core","defense","civilian_service"} <= set(x["requiredVisualRoles"]))
        initial=runtime.reconstruct(sid,controller_id="owner",year=1450,growth="town")
        civilian=next(x for x in initial["objects"] if x["role"]=="civilian_service")
        core=next(x for x in initial["objects"] if x["role"]=="city_core")
        self.assertTrue(civilian["invulnerable"] and not civilian["destructible"]); self.assertTrue(core["destructible"])
        damaged=runtime.reconstruct(sid,controller_id="owner",destroyed_roles=("defense",),growth="town")
        self.assertNotIn("defense",{x["role"] for x in damaged["objects"]})
        captured=runtime.reconstruct(sid,controller_id="captor",year=1700,growth="capital")
        self.assertEqual("captor",next(x for x in captured["objects"] if x["role"]=="city_core")["teamColor"])
        self.assertGreater(captured["density"],initial["density"])
        runtime.lose_representation(sid); self.assertNotIn(sid,runtime.active)
        self.assertEqual(captured,runtime.reconstruct(sid,controller_id="captor",year=1700,growth="capital"))

    def test_unknown_settlement_period_and_growth_are_rejected(self):
        runtime=SettlementVisualRuntime(self.data); sid=self.data["settlementAssignments"][0]["settlementId"]
        for args,message in [({"settlement_id":"absent","controller_id":"x"},"unknown"),({"settlement_id":sid,"controller_id":"x","year":1900},"period"),({"settlement_id":sid,"controller_id":"x","growth":"megacity"},"growth")]:
            with self.assertRaisesRegex(SettlementVisualRuntimeError,message): runtime.resolve(**args)

if __name__=="__main__": unittest.main()
