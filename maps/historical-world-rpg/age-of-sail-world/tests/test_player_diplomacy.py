import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from diplomacy import DiplomacyRuntime
from player_diplomacy import PlayerDiplomacyError,PlayerDiplomacyRuntime,PlayerDiplomacySaveAdapter
from polity import PolityRuntime
from province import ProvinceRuntime
from settlement import RecordingSettlementAdapter,SettlementRuntime

class PlayerDiplomacyTests(unittest.TestCase):
 def setUp(self):
  world=json.loads((ROOT/"scenario/world/world.json").read_text()); clauses=json.loads((ROOT/"scenario/diplomacy/treaty-clauses.json").read_text())["clauses"]
  self.polities=PolityRuntime(world);self.provinces=ProvinceRuntime(world,self.polities);self.settlements=SettlementRuntime(world,RecordingSettlementAdapter())
  self.diplomacy=DiplomacyRuntime(self.polities,self.provinces,self.settlements);self.diplomacy.declare_war("channel_war","england","france")
  caps={p:list(clauses) for p in ("england","france","castile")}
  self.runtime=PlayerDiplomacyRuntime(self.polities,self.diplomacy,self.provinces,self.settlements,clause_definitions=clauses,government_capabilities=caps)
  self.runtime.discover("england",source="origin");self.runtime.discover("france",source="ruler_met")
  self.authority={"treasuries":{"england":1000,"france":1000},"capabilities":caps}
 def term(self,**changes):
  row={"kind":"ceasefire","grantorPolityId":"england","beneficiaryPolityId":"france","durationDays":90};row.update(changes);return row
 def test_country_screen_is_discovery_safe_and_contextual(self):
  self.runtime.set_standing("france",reputation=12,favor=4,service=2)
  view=self.runtime.country_view("france",{"originPolityId":"england","currentAllegiancePolityId":"england"},rulers={"france":{"name":"Known ruler"}},partners=["england","castile"],government_interactions=["serve","negotiate"])
  self.assertTrue(view["atWar"]);self.assertEqual({"reputation":12,"favor":4,"service":2},view["standing"]);self.assertEqual(["england"],view["knownPartners"]);self.assertEqual("Known ruler",view["government"]["name"])
  with self.assertRaisesRegex(PlayerDiplomacyError,"not been discovered"):self.runtime.country_view("castile",{})
 def test_government_service_access_reward_and_allegiance_are_gated(self):
  state={"originPolityId":"england","currentAllegiancePolityId":"england"}
  with self.assertRaisesRegex(PlayerDiplomacyError,"requirements"):self.runtime.government_action("change_allegiance","france",state)
  changed=self.runtime.government_action("change_allegiance","france",state,eligible=True);self.assertEqual("france",changed["currentAllegiancePolityId"]);self.assertEqual("england",changed["originPolityId"])
  self.runtime.government_action("serve","france",changed,eligible=True);self.runtime.government_action("request_reward","france",changed,eligible=True,reward={"id":"commission"});self.runtime.government_action("request_access","france",changed,eligible=True)
  self.assertIn("government_access",self.runtime.rights["france"])
 def test_win_loss_stalemate_and_bounded_reasons(self):
  oid="offer_balance";self.runtime.propose_peace(oid,"channel_war","england","france",[self.term()],day=10,authority=self.authority)
  losing={"polities":{"france":{"warExhaustion":80,"casualtyPressure":30,"economicCost":50,"treasury":10}},"relativeStrength":{"england":40},"occupiedValue":{"england":20,"france":0}}
  self.assertTrue(self.runtime.evaluate_offer(oid,losing)["acceptable"])
  winning={"polities":{"france":{"warExhaustion":0,"casualtyPressure":0,"economicCost":1,"treasury":500,"continuingThreat":60}},"relativeStrength":{"england":-40}}
  result=self.runtime.evaluate_offer(oid,winning);self.assertFalse(result["acceptable"]);self.assertLessEqual(len(result["reasons"]),3)
  stalemate={"polities":{"france":{"warExhaustion":20,"casualtyPressure":5,"economicCost":5,"treasury":100}},"relativeStrength":{"england":0},"alliancePressure":{"france":0},"diplomaticHistory":{"france":-5},"historicalPressure":{"france":999}}
  self.assertFalse(self.runtime.evaluate_offer(oid,stalemate)["acceptable"],"historical bias is bounded and cannot override current state")
 def test_occupied_territory_explicit_return_or_cession(self):
  self.diplomacy.record_occupation("channel_war","province","kent","france")
  cession=self.term(kind="territory",grantorPolityId="england",beneficiaryPolityId="france",entityKind="province",entityId="kent");self.runtime.propose_peace("cede_kent","channel_war","france","england",[cession],day=1,authority=self.authority)
  with self.assertRaisesRegex(PlayerDiplomacyError,"confirmation required"):self.runtime.respond("cede_kent",True,day=2,authority=self.authority)
  self.runtime.respond("cede_kent",True,day=2,authority=self.authority,confirmed=True);self.assertEqual("france",self.provinces.require("kent").legal_owner_polity_id)
 def test_invalid_impossible_terms_and_alliance_participation(self):
  self.diplomacy.join_conflict("channel_war","castile","attacker")
  with self.assertRaisesRegex(PlayerDiplomacyError,"neither owns nor controls"):self.runtime.propose_peace("steal","channel_war","france","england",[self.term(kind="territory",grantorPolityId="france",beneficiaryPolityId="england",entityKind="province",entityId="kent")],day=1,authority=self.authority)
  with self.assertRaisesRegex(PlayerDiplomacyError,"cannot fund"):self.runtime.propose_peace("debt","channel_war","england","france",[self.term(kind="payment",amount=1001,durationDays=None)],day=1,authority=self.authority)
  with self.assertRaisesRegex(PlayerDiplomacyError,"opposing sides"):self.runtime.propose_peace("allies","channel_war","england","france",[self.term(beneficiaryPolityId="castile")],day=1,authority=self.authority)
  weak=copy.deepcopy(self.authority);weak["capabilities"]["england"]=[]
  with self.assertRaisesRegex(PlayerDiplomacyError,"cannot grant"):self.runtime.propose_peace("rights","channel_war","england","france",[self.term(kind="trade_access")],day=1,authority=weak)
 def test_rich_and_poor_exhausted_states_and_ai_offer(self):
  self.runtime.propose_peace("ai_offer","channel_war","france","england",[self.term(grantorPolityId="france",beneficiaryPolityId="england")],day=3,authority=self.authority,initiated_by="ai")
  rich={"polities":{"england":{"warExhaustion":80,"casualtyPressure":20,"economicCost":5,"treasury":9999}},"relativeStrength":{"france":0}}
  poor=copy.deepcopy(rich);poor["polities"]["england"].update(economicCost=80,treasury=1)
  self.assertTrue(self.runtime.evaluate_offer("ai_offer",rich)["acceptable"]);self.assertTrue(self.runtime.evaluate_offer("ai_offer",poor)["acceptable"])
 def test_rejected_offer_cooldown_and_save_resume_equivalence(self):
  self.runtime.propose_peace("first_offer","channel_war","england","france",[self.term()],day=4,authority=self.authority);self.runtime.respond("first_offer",False,day=4,authority=self.authority)
  with self.assertRaisesRegex(PlayerDiplomacyError,"cooldown"):self.runtime.propose_peace("too_soon","channel_war","england","france",[self.term()],day=5,authority=self.authority)
  saved=PlayerDiplomacySaveAdapter(self.runtime,{"calendar":{"day":4}}).capture_world();restored=PlayerDiplomacyRuntime(self.polities,self.diplomacy,self.provinces,self.settlements,government_capabilities=self.runtime.capabilities);restored.restore(saved["playerDiplomacyState"])
  self.assertEqual(self.runtime.snapshot(),restored.snapshot());self.assertEqual(saved,PlayerDiplomacySaveAdapter(restored,{"calendar":{"day":4}}).capture_world())

if __name__=="__main__":unittest.main()
