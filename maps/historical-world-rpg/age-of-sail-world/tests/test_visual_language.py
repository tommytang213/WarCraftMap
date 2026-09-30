import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SHARED=ROOT.parent/"_shared"
sys.path.insert(0,str(SHARED/"engine"))
import visual_language as runtime

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); loaded=importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded

builder=module(ROOT/"tooling/build_visual_language.py","build_visual_language")

class VisualLanguageTests(unittest.TestCase):
    def setUp(self):
        self.path=ROOT/"scenario/visuals/country-unit-language.json"
        self.data=json.loads(self.path.read_text())
        self.resolver=runtime.VisualResolver(self.data)

    def test_scenario_data_and_snapshots_are_deterministic(self):
        self.assertEqual(builder.build(),self.data)
        reports=ROOT/"scenario/visuals/reports"
        self.assertEqual(builder.snapshots(self.data),json.loads((reports/"global-visual-snapshot.json").read_text()))
        self.assertEqual(builder.previews(self.data),json.loads((reports/"regional-preview-scenes.json").read_text()))
        self.assertEqual({"southeast_asia","east_asia","pacific","americas_caribbean"},set(builder.previews(self.data)))
        self.assertEqual(len({x["label"] for x in builder.snapshots(self.data)}),len(self.data["rosterAssignments"]))

    def test_every_polity_ordinary_and_authored_assignment_is_covered_unambiguously(self):
        polities=builder.polities(); archetypes,authored=builder.roster_data()
        actual={(x["polityId"],x["archetypeId"]) for x in self.data["rosterAssignments"]}
        self.assertEqual(len(actual),len(self.data["rosterAssignments"]))
        families=json.loads((ROOT/"scenario/rosters/global-roster-families.json").read_text())["families"]
        for family in families:
            region=family["politySource"].replace("-1450.json","").replace("-","_")
            for polity in (p for p,r in polities.items() if r==region):
                for archetype in family["archetypeIds"]: self.assertIn((polity,archetype),actual)
        for assignment in authored:
            for polity in assignment["polityIds"]:
                for archetype in assignment["archetypeIds"]: self.assertIn((polity,archetype),actual)
        categories={archetypes[x["archetypeId"]].get("category") for x in self.data["rosterAssignments"]}
        self.assertTrue({"infantry","cavalry","artillery","specialist","marine","warship","transport","merchant"} <= categories)

    def test_assets_variations_ships_and_high_priority_characters_are_declared(self):
        catalogue=json.loads((SHARED/"assets/warcraft-3.0-stock.json").read_text())
        self.assertTrue(builder.validate(self.data,catalogue))
        asset_ids={x["id"] for x in catalogue["assets"]}
        for row in self.data["rosterAssignments"]:
            for visual in [row["baseline"],*row["progression"]]:
                self.assertIn(visual["assetId"],asset_ids); self.assertEqual([],visual["attachments"])
                self.assertGreater(visual["scale"],0)
        self.assertEqual(set(builder.ships()),{x["shipId"] for x in self.data["shipAssignments"]})
        requirements={x["id"]:x for x in self.data["productionRequirements"]}
        for char in self.data["characterAssignments"]:
            self.assertIn(char["productionRequirementId"],requirements)
            self.assertTrue(set(requirements[char["productionRequirementId"]]["fallbackAssetIds"]) <= asset_ids)

    def test_validator_rejects_ambiguous_missing_invalid_unsafe_and_undeclared_data(self):
        catalogue=json.loads((SHARED/"assets/warcraft-3.0-stock.json").read_text())
        cases=[]
        bad=copy.deepcopy(self.data); bad["rosterAssignments"].append(copy.deepcopy(bad["rosterAssignments"][0])); cases.append((bad,"ambiguous"))
        bad=copy.deepcopy(self.data); bad["rosterAssignments"][0]["familyId"]="absent"; cases.append((bad,"missing family"))
        bad=copy.deepcopy(self.data); bad["rosterAssignments"][0]["baseline"]["assetId"]="absent"; cases.append((bad,"invalid asset"))
        bad=copy.deepcopy(self.data); bad["rosterAssignments"][0]["baseline"]["scale"]=99; cases.append((bad,"unsafe scale"))
        bad=copy.deepcopy(self.data); bad["rosterAssignments"][0]["baseline"]["attachments"]=["weapon,left"]; cases.append((bad,"unsafe attachment"))
        bad=copy.deepcopy(self.data); bad["characterAssignments"][0].pop("productionRequirementId"); cases.append((bad,"undeclared"))
        for data,message in cases:
            with self.subTest(message=message),self.assertRaisesRegex(builder.VisualDataError,message): builder.validate(data,catalogue)

    def test_date_technology_controller_import_and_alternate_history_resolution(self):
        row=next(x for x in self.data["rosterAssignments"] if x["archetypeId"]=="japanese_teppo_ashigaru")
        with self.assertRaisesRegex(runtime.VisualLanguageError,"anachronistic"):
            self.resolver.resolve(polity_id=row["polityId"],archetype_id=row["archetypeId"],year=1450)
        result=self.resolver.resolve(polity_id=row["polityId"],archetype_id=row["archetypeId"],year=1600,
            technologies=["pike_and_shot"],controller_id="captor",imported_from=row["polityId"])
        self.assertEqual(("captor","controller",row["culturalMarkingId"]),(result["controllerId"],result["teamColorSource"],result["culturalMarkingId"]))
        alternate=self.resolver.resolve(polity_id=row["polityId"],archetype_id=row["archetypeId"],year=1450,alternate_history=True)
        self.assertEqual(row["baseline"]["assetId"],alternate["assetId"])

    def test_retirement_reconstruction_and_object_budget_are_bounded_and_atomic(self):
        row=self.data["rosterAssignments"][0]
        visual=self.resolver.resolve(polity_id=row["polityId"],archetype_id=row["archetypeId"],year=1820)
        self.resolver.instantiate("army",visual,3); retired=self.resolver.retire("army")
        self.assertEqual(3,retired["objectCount"]); self.assertEqual({},self.resolver.active)
        self.assertEqual(("a","b"),self.resolver.reconstruct((("b",visual,2),("a",visual,1))))
        before=copy.deepcopy(self.resolver.active)
        with self.assertRaisesRegex(runtime.VisualLanguageError,"budget"):
            self.resolver.reconstruct((("too_many",visual,257),))
        self.assertEqual(before,self.resolver.active)

if __name__ == "__main__": unittest.main()
