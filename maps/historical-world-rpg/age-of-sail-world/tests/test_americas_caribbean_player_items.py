import copy, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT.parent/"_shared"/"engine"),str(ROOT/"tooling")]
import player_items, player_item_catalog
DATA=json.loads((ROOT/"scenario/inventory/player-use-catalog.json").read_text())
AMERICAS=[x for x in DATA["items"] if "americas_caribbean" in x["requirements"].get("regionIds",[])]

def ctx(year=1450,tech=()):
 return {"campaignSeed":"a","settlementId":"port","regionId":"americas_caribbean","controllerId":"local","year":year,"refreshEpoch":2,"technologyIds":list(tech),"institutionIds":[],"eventFlagIds":[],"questFlagIds":[],"localProductionIds":[],"tradeAccess":True,"wealth":100}

class AmericasCaribbeanPlayerItems(unittest.TestCase):
 def test_global_targets_and_regional_breadth(self):
  r=player_item_catalog.build_report(DATA)
  self.assertTrue(r["catalogueTargetComplete"]); self.assertEqual([],r["failures"])
  self.assertGreaterEqual(len(AMERICAS),180); self.assertGreaterEqual(len({s for x in AMERICAS for s in x.get("coverage",{}).get("subregionIds",[]) }),15)
  self.assertGreaterEqual(sum(x["unique"] for x in AMERICAS),60)

 def test_later_technology_does_not_leak_into_1450(self):
  for archetype in ("gunsmith","military_supplier","bookseller_cartographer"):
   early={x.item_type_id for x in player_items.resolve_stock(DATA,archetype,ctx())}
   self.assertNotIn("kentucky_rifle",early); self.assertNotIn("caribbean_boarding_pistol",early)
  late={x.item_type_id for x in player_items.resolve_stock(DATA,"gunsmith",ctx(1780,("flintlock_drill",)))}
  self.assertTrue({"kentucky_rifle","caribbean_boarding_pistol"}&late)

 def test_sets_have_attainable_thresholds_and_tradeoffs(self):
  region_sets=[s for s in DATA["equipmentSets"] if s["id"].endswith("_set") and any(i.startswith(("woodland_","andean_","caribbean_","haitian_")) for i in s["itemTypeIds"])]
  self.assertGreaterEqual(len(region_sets),4)
  for s in region_sets:
   self.assertEqual([2,3,4],[t["pieceCount"] for t in s["thresholds"]])
   pieces=[next(x for x in DATA["items"] if x["id"]==i) for i in s["itemTypeIds"]]
   self.assertEqual(4,len({x["comparison"]["slotIds"][0] for x in pieces}))

 def test_unique_identity_transactions_and_rollback(self):
  item=next(x for x in AMERICAS if x["unique"]); stock=(player_items.StockEntry(item["id"],1,100),)
  bought=player_items.transact_purchase(stock,(),{},DATA,item_type_id=item["id"],owner_id="hero",funds_minor=100,capacity=1)
  self.assertEqual("hero",bought["uniqueOwners"][item["provenance"]["identityId"]])
  before=(stock,(),{})
  with self.assertRaises(player_items.PlayerItemError): player_items.transact_purchase(stock,("full",),{},DATA,item_type_id=item["id"],owner_id="hero",funds_minor=100,capacity=1)
  self.assertEqual(before,(stock,(),{}))

 def test_generator_is_repeatable(self):
  before=(ROOT/"scenario/inventory/player-use-catalog.json").read_text()
  import expand_americas_caribbean_player_items as gen
  gen.expand(); self.assertEqual(before,(ROOT/"scenario/inventory/player-use-catalog.json").read_text())

if __name__=="__main__": unittest.main()
