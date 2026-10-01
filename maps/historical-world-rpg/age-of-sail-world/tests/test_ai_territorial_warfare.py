import copy, importlib.util, json, pathlib, sys, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("ai",ROOT.parent/"_shared"/"engine"/"ai_territorial_warfare.py")
AI=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=AI;SPEC.loader.exec_module(AI)
CONFIG=json.loads((ROOT/"scenario"/"ai"/"territorial-warfare.json").read_text())

class Gateway:
    def __init__(self): self.calls=[];self.operations=True;self.peace=True
    def validate_war(self,a,t,g): self.calls.append(("validate_war",a,t));return True
    def declare_war(self,c,a,t): self.calls.append(("declare",c,a,t))
    def validate_join(self,a,c,s): return True
    def join_war(self,a,c,s): self.calls.append(("join",a,c,s))
    def validate_operation(self,a,g): return self.operations
    def validate_peace(self,c,o): self.calls.append(("validate_peace",c,copy.deepcopy(o)));return self.peace
    def conclude_peace(self,c,o): self.calls.append(("peace",c,copy.deepcopy(o)))

def world(pressure=True):
    return {"aiPolityIds":["england"],"owners":{},"controllers":{},
      "claims":{"english_french_dynastic_claim":pressure},"rivalries":{"england_france_rivalry":pressure},
      "alliances":{},"routes":{},"access":{},"governments":{},"threats":{},
      "activeAttackersByTarget":{},
      "candidateGoals":{"england":[{"id":"claim_normandy","kind":"press_claim","targetPolityId":"france","territoryIds":["normandy"],"settlementValue":50,"routeValue":20}]},
      "pairMetrics":{"england:france":{"claim":80,"ownership":20,"control":20,"access":30,"diplomacy":0,"alliance":0,"threat":20,"terrain":0}},
      "polityMetrics":{"england":{"landStrength":100,"navalStrength":80,"manpower":50,"supply":50,"treasury":50,"economy":50,"technology":50,"institutions":50,"warExhaustion":0},
       "france":{"landStrength":90,"navalStrength":30,"technology":45,"institutions":45}},"wars":{}}

class AITests(unittest.TestCase):
    def test_pressure_bias_decays_without_forcing_outcome(self):
        gateway=Gateway(); ai=AI.TerritorialWarfareAI(CONFIG,gateway,"seed")
        score_on=ai._war_score("england","france",world()["candidateGoals"]["england"][0],world(),0)[0]
        divergent=world(False)
        score_off=ai._war_score("england","france",divergent["candidateGoals"]["england"][0],divergent,0)[0]
        self.assertGreater(score_on,score_off)
        gateway.operations=False
        self.assertFalse(ai.evaluate(0,world()))

    def test_authoritative_validation_determinism_cooldown_and_save(self):
        g1=Gateway();a1=AI.TerritorialWarfareAI(CONFIG,g1,"same")
        first=a1.evaluate(0,world());self.assertEqual("declare",first[0].kind)
        snap=a1.snapshot();g2=Gateway();a2=AI.TerritorialWarfareAI(CONFIG,g2,"same");a2.restore(snap)
        self.assertEqual(a1.evaluate(30,world()),a2.evaluate(30,world()))
        self.assertEqual(1,len([x for x in g1.calls if x[0]=="declare"]))
        adapter=AI.StrategicAISaveAdapter(a2,{"clock":30});saved=adapter.capture_world()
        self.assertEqual(a2.snapshot()["activeObjectives"],saved[AI.AI_WORLD_STATE_KEY]["activeObjectives"])

    def test_proportionate_peace_only_transfers_goal_territory(self):
        g=Gateway();a=AI.TerritorialWarfareAI(CONFIG,g,"s");a.evaluate(0,world())
        w=world();cid=a.state["activeObjectives"][0]["conflictId"]
        w["wars"][cid]={"metricsByPolity":{"england":{"goalCompletion":100,"casualties":20,"exhaustion":30,"economicCost":20,"alliance":0,"continuingThreat":0,"strategicRisk":0}},
          "occupations":[{"entityKind":"province","entityId":"normandy","legalOwnerPolityId":"france","controllerPolityId":"england"},
            {"entityKind":"province","entityId":"paris","legalOwnerPolityId":"france","controllerPolityId":"england"}]}
        decisions=a.evaluate(180,w);self.assertEqual("peace",decisions[0].kind)
        outcomes=[x for x in g.calls if x[0]=="peace"][0][2]
        self.assertEqual("england",outcomes[0]["legalOwnerPolityId"])
        self.assertEqual(("france","france"),(outcomes[1]["legalOwnerPolityId"],outcomes[1]["controllerPolityId"]))

if __name__=="__main__": unittest.main()
