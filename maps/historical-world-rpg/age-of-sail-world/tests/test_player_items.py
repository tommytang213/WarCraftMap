import copy, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
sys.path.insert(0,str(ROOT/"tooling"))
import player_items
import player_item_catalog

DATA=json.loads((ROOT/"scenario/inventory/player-use-catalog.json").read_text())

def context(**changes):
    value={"campaignSeed":"campaign_a","settlementId":"lisbon","regionId":"europe","cultureId":"portuguese","controllerId":"portugal","year":1650,"refreshEpoch":3,"technologyIds":["cast_cannon","oceanic_seamanship"],"institutionIds":[],"localProductionIds":["iron","brass"],"tradeAccess":True,"wealth":50,"eventFlagIds":[],"questFlagIds":[]}
    value.update(changes); return value

class PlayerItemTests(unittest.TestCase):
    def test_catalog_and_coverage_dimensions(self):
        player_items.validate_catalog(DATA)
        player_items.validate_catalog_references(DATA,player_item_catalog.scenario_references())
        report=player_item_catalog.build_report(DATA)
        self.assertFalse(report["catalogueTargetComplete"])
        self.assertGreaterEqual(report["itemCount"],150)
        self.assertGreaterEqual(report["uniqueCount"],20)
        self.assertGreaterEqual(len(DATA["equipmentSets"]),14)
        for region in ("europe","africa","middle_east_india"):
            self.assertGreaterEqual(report["byRegion"][region],55)
        self.assertTrue({"1-50","51-100","101-150","151-200","201-250","251-300"} <= set(report["byLevelBand"]))
        self.assertTrue(all(report["byArchetype"].get(x["id"],0)>0 for x in DATA["merchantArchetypes"]))
        self.assertEqual(set(player_item_catalog.REGIONS),set(report["byRegion"]))
        self.assertTrue({"equipment","consumable","tool","book_map","artifact"}<={x["category"] for x in DATA["items"]})
        self.assertTrue({"generic","regional","cultural","profession","set_piece","historical"}<={x["provenance"]["kind"] for x in DATA["items"]})

    def test_stock_is_deterministic_and_context_sensitive(self):
        first=player_items.resolve_stock(DATA,"armourer",context())
        self.assertEqual(first,player_items.resolve_stock(DATA,"armourer",copy.deepcopy(context())))
        self.assertNotEqual(first,player_items.resolve_stock(DATA,"armourer",context(refreshEpoch=4)))
        guns=player_items.resolve_stock(DATA,"gunsmith",context())
        self.assertIn("matchlock_musket",{x.item_type_id for x in guns})
        self.assertNotIn("matchlock_musket",{x.item_type_id for x in player_items.resolve_stock(DATA,"gunsmith",context(technologyIds=[]))})
        self.assertNotEqual(player_items.resolve_stock(DATA,"general_merchant",context()),player_items.resolve_stock(DATA,"general_merchant",context(tradeAccess=False,wealth=0)))

    def test_region_date_controller_quest_event_and_scarcity_gates(self):
        early=player_items.resolve_stock(DATA,"apothecary",context(regionId="americas_caribbean",year=1600))
        late=player_items.resolve_stock(DATA,"apothecary",context(regionId="americas_caribbean",year=1650))
        self.assertNotIn("quinine_bark_dose",{x.item_type_id for x in early}); self.assertIn("quinine_bark_dose",{x.item_type_id for x in late})
        mysore=context(regionId="middle_east_india",controllerId="mysore_kingdom",year=1800,wealth=100)
        self.assertIn("tipu_sultans_tiger_emblem",{x.item_type_id for x in player_items.resolve_stock(DATA,"relic_merchant",mysore)})
        self.assertNotIn("tipu_sultans_tiger_emblem",{x.item_type_id for x in player_items.resolve_stock(DATA,"relic_merchant",dict(mysore,scarceItemTypeIds=["tipu_sultans_tiger_emblem"]))})

    def test_settlement_technology_institution_event_and_quest_variation(self):
        west=context(regionId="africa",settlementId="timbuktu",year=1600,technologyIds=[],institutionIds=[])
        self.assertIn("timbuktu_legal_manuscript",{x.item_type_id for x in player_items.resolve_stock(DATA,"bookseller_cartographer",west)})
        self.assertNotIn("timbuktu_legal_manuscript",{x.item_type_id for x in player_items.resolve_stock(DATA,"bookseller_cartographer",dict(west,settlementId="gao"))})
        europe=context(year=1780,technologyIds=["marine_chronometer","flintlock_drill"],institutionIds=["movable_type_printing"],wealth=100)
        self.assertIn("marine_chronometer",{x.item_type_id for x in player_items.resolve_stock(DATA,"ship_chandler",europe)})
        no_tech=dict(europe,technologyIds=[])
        self.assertNotIn("marine_chronometer",{x.item_type_id for x in player_items.resolve_stock(DATA,"ship_chandler",no_tech)})
        africa=context(regionId="africa",controllerId="benin_kingdom",year=1760,eventFlagIds=["atlantic_routes_expand"],wealth=100)
        self.assertIn("dahomey_flintlock",{x.item_type_id for x in player_items.resolve_stock(DATA,"gunsmith",africa)})
        self.assertNotIn("dahomey_flintlock",{x.item_type_id for x in player_items.resolve_stock(DATA,"gunsmith",dict(africa,eventFlagIds=[]))})

    def test_no_bulk_goods_or_exact_stat_clones_and_sets_have_tradeoffs(self):
        bulk={"grain","fish","timber","iron","copper","salt","wine","wool","cloth","spices","sugar","tobacco","coffee","tea","silk","porcelain","slaves"}
        self.assertFalse(bulk & {x["id"] for x in DATA["items"]})
        for row in DATA["equipmentSets"]:
            self.assertGreaterEqual(len(row["thresholds"]),2)
            pieces=[next(x for x in DATA["items"] if x["id"]==pid) for pid in row["itemTypeIds"]]
            self.assertGreaterEqual(len({tuple(sorted(x["comparison"].get("majorStats",{}))) for x in pieces}),2)

    def test_comparison_keeps_specialized_tradeoffs_and_set_thresholds(self):
        view=player_items.compare(DATA,"naval_hanger","matchlock_musket",enhancement_rank=2,equipped_set_counts={"company_officer_set":1})
        self.assertLess(view["itemLevel"],60); self.assertLess(view["deltas"]["rangedPower"],0)
        self.assertGreater(view["deltas"]["boarding"],0); self.assertEqual(2,view["set"]["equippedPieceCount"])
        self.assertTrue(view["conditionalEffects"]); self.assertTrue(view["requirements"])
        with self.assertRaises(player_items.PlayerItemError): player_items.compare(DATA,"naval_hanger",enhancement_rank=99)

    def test_unique_purchase_overflow_and_rejection_are_atomic(self):
        ctx=context(regionId="middle_east_india",controllerId="mysore_kingdom",year=1800,wealth=100)
        stock=player_items.resolve_stock(DATA,"relic_merchant",ctx); before=(stock,(),{})
        result=player_items.transact_purchase(stock,(),{},DATA,item_type_id="tipu_sultans_tiger_emblem",owner_id="hero",funds_minor=20000,capacity=2)
        self.assertIn("mysore_tiger_emblem",result["uniqueOwners"])
        self.assertNotIn("tipu_sultans_tiger_emblem",{x.item_type_id for x in player_items.resolve_stock(DATA,"relic_merchant",ctx,result["uniqueOwners"])})
        with self.assertRaises(player_items.PlayerItemError): player_items.transact_purchase(stock,("full",),{},DATA,item_type_id="tipu_sultans_tiger_emblem",owner_id="hero",funds_minor=20000,capacity=1)
        self.assertEqual(before,(stock,(),{}))
        sold=player_items.transact_sale(result["stock"],result["inventory"],result["uniqueOwners"],DATA,item_type_id="tipu_sultans_tiger_emblem",owner_id="mysore_shop",funds_minor=result["fundsMinor"],price_minor=4000)
        self.assertNotIn("tipu_sultans_tiger_emblem",sold["inventory"])
        self.assertEqual("merchant:mysore_shop",sold["uniqueOwners"]["mysore_tiger_emblem"])

    def test_save_migration_reconstruction_and_duplicate_unique_rejection(self):
        old={"schemaVersion":1,"instances":[{"instanceId":"relic_1","itemTypeId":"magellans_compass","ownerId":"hero"}]}
        migrated=player_items.migrate_state(old)
        migrated["uniqueOwners"]={"magellan_victoria_compass":"hero"}
        player_items.validate_state(DATA,migrated)
        self.assertEqual(0,migrated["instances"][0]["enhancementRank"]); self.assertNotIn("uniqueOwners",old)
        bad=copy.deepcopy(migrated); bad["instances"].append(dict(bad["instances"][0],instanceId="relic_2"))
        with self.assertRaisesRegex(player_items.PlayerItemError,"duplicate unique"): player_items.validate_state(DATA,bad)

if __name__=="__main__": unittest.main()
