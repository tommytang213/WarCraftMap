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
        report=player_item_catalog.build_report(DATA)
        self.assertFalse(report["catalogueTargetComplete"])
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
