import json, sys, unittest
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
sys.path.insert(0,str(ROOT/"tooling"))
import player_items
import player_item_catalog

DATA=json.loads((ROOT/"scenario/inventory/player-use-catalog.json").read_text())
REGIONS=("southeast_asia","east_asia","pacific")

def rows(path, key): return json.loads(path.read_text())[key]

class AsiaPacificPlayerItemTests(unittest.TestCase):
    def test_release_scale_regional_dimensions(self):
        report=player_item_catalog.build_report(DATA)
        for region in REGIONS:
            regional=[x for x in DATA["items"] if region in x["requirements"].get("regionIds",[])]
            self.assertGreaterEqual(len(regional),45,region)
            self.assertGreaterEqual(sum(x["unique"] for x in regional),6,region)
            self.assertEqual({"equipment","consumable","tool","book_map","artifact"},{x["category"] for x in regional})
            self.assertTrue({"common","fine","superior","rare","epic","legendary","relic"}<={x["rarityId"] for x in regional})
            self.assertTrue({"regional","cultural","polity","profession","set_piece","historical"}<={x["provenance"]["kind"] for x in regional})
        self.assertGreaterEqual(len(report["bySubregion"]),20)
        self.assertGreaterEqual(report["byHistoricalItemClass"]["named_historical"],18)
        self.assertTrue(report["catalogueTargetComplete"])

    def test_all_slots_merchants_and_specialized_sets_are_covered(self):
        regional=[x for x in DATA["items"] if set(x["requirements"].get("regionIds",[]))&set(REGIONS)]
        self.assertEqual({"head","chest","gloves","boots","ring","primary","offhand","trinket","mount"},
                         {s for x in regional for s in x["comparison"].get("slotIds",[])})
        self.assertEqual({x["id"] for x in DATA["merchantArchetypes"]},
                         {a for x in regional for a in x["merchant"].get("archetypeIds",[])})
        sets={x["id"]:x for x in DATA["equipmentSets"]}
        for region in REGIONS:
            region_sets={x["comparison"].get("setId") for x in regional if region in x["requirements"].get("regionIds",[])}-{None}
            self.assertGreaterEqual(len(region_sets),4)
            for set_id in region_sets:
                self.assertEqual([2,3,4],[x["pieceCount"] for x in sets[set_id]["thresholds"]])
                effects=[e for t in sets[set_id]["thresholds"] for e in t["effectIds"]]
                self.assertGreaterEqual(len(set(effects)),2)

    def test_every_authored_stock_item_is_reachable_and_deterministic(self):
        for item in DATA["items"]:
            if not set(item["requirements"].get("regionIds",[]))&set(REGIONS) or not item["merchant"]["eligible"]: continue
            req=item["requirements"]
            ctx={"campaignSeed":"reachability","settlementId":req.get("settlementIds",["regional_port"])[0],
                 "regionId":req["regionIds"][0],"cultureId":req.get("cultureIds",["regional"])[0],
                 "controllerId":req.get("controllerIds",["regional_controller"])[0],
                 "year":req.get("startYear",1450),"refreshEpoch":0,
                 "technologyIds":req.get("technologyIds",[]),"institutionIds":req.get("institutionIds",[]),
                 "eventFlagIds":req.get("eventFlagIds",[]),"questFlagIds":req.get("questFlagIds",[]),
                 "localProductionIds":item["merchant"].get("localProductionAny",[]),"tradeAccess":True,"wealth":100}
            found=False
            for archetype in item["merchant"]["archetypeIds"]:
                # Raise the stock limit temporarily so reachability, rather than seeded competition, is tested.
                copy_data=dict(DATA); copy_data["merchantArchetypes"]=[dict(x,stockLimit=30) if x["id"]==archetype else x for x in DATA["merchantArchetypes"]]
                first=player_items.resolve_stock(copy_data,archetype,ctx)
                self.assertEqual(first,player_items.resolve_stock(copy_data,archetype,dict(ctx)))
                found |= item["id"] in {x.item_type_id for x in first}
            self.assertTrue(found,item["id"])

    def test_external_requirements_and_historical_hooks_resolve(self):
        progress=json.loads((ROOT/"scenario/progression/catalog.json").read_text())
        valid={"technologyIds":{x["id"] for x in progress["technologies"]},
               "institutionIds":{x["id"] for x in progress["institutions"]},
               "eventFlagIds":{x["id"] for x in rows(ROOT/"scenario/historical-events.json","events")},
               "questFlagIds":{x["id"] for x in rows(ROOT/"scenario/campaign-quests.json","quests")}}
        settlements=set(); controllers=set()
        for slug in ("southeast-asia","east-asia","pacific"):
            settlements|={x["id"] for x in rows(ROOT/f"scenario/settlements/{slug}-1450.json","settlements")}
            controllers|={x["id"] for x in rows(ROOT/f"scenario/politics/{slug}-1450.json","polities")}
        for item in DATA["items"]:
            if not set(item["requirements"].get("regionIds",[]))&set(REGIONS): continue
            req=item["requirements"]
            for key, universe in valid.items(): self.assertFalse(set(req.get(key,[]))-universe,(item["id"],key))
            self.assertFalse(set(req.get("settlementIds",[]))-settlements,item["id"])
            self.assertFalse(set(req.get("controllerIds",[]))-controllers,item["id"])
            if item["unique"]:
                self.assertTrue(item["evidenceIds"])
                self.assertIn(item["availability"]["source"],{"deterministic_merchant","quest_reward"})
                self.assertTrue(item["merchant"]["eligible"] or item["availability"]["rewardQuestIds"])

    def test_no_late_or_imported_baseline_leakage(self):
        baseline={"campaignSeed":"baseline","settlementId":"honolulu_anchorage","regionId":"pacific","cultureId":"hawaiian",
                  "controllerId":"hawaii_chiefdom","year":1450,"refreshEpoch":0,"technologyIds":["oceanic_seamanship"],
                  "institutionIds":[],"eventFlagIds":[],"questFlagIds":[],"localProductionIds":[],"tradeAccess":False,"wealth":100}
        stock={e.item_type_id for a in (x["id"] for x in DATA["merchantArchetypes"]) for e in player_items.resolve_stock(DATA,a,baseline)}
        self.assertFalse({"pacific_survey_set","japanese_tanegashima"}&stock)
        self.assertFalse(stock&{"waxed_specimen_hat","surveyors_field_coat","botanical_collecting_case","brass_sextant_case"})

    def test_duplicate_unique_identity_is_rejected(self):
        import copy
        broken=copy.deepcopy(DATA); duplicate=copy.deepcopy(next(x for x in broken["items"] if x["unique"])); duplicate["id"]="duplicate_named_relic"; broken["items"].append(duplicate)
        with self.assertRaisesRegex(player_items.PlayerItemError,"duplicate unique identity"): player_items.validate_catalog(broken)

    def test_regional_consumable_use_is_atomic(self):
        before=("noni_leaf_poultice","maori_patu")
        used=player_items.transact_consume(before,DATA,item_type_id="noni_leaf_poultice")
        self.assertEqual(("maori_patu",),used["inventory"])
        self.assertEqual(("field_medicine",),used["effectIds"])
        with self.assertRaisesRegex(player_items.PlayerItemError,"not consumable"):
            player_items.transact_consume(before,DATA,item_type_id="maori_patu")
        self.assertEqual(("noni_leaf_poultice","maori_patu"),before)

if __name__=="__main__": unittest.main()
