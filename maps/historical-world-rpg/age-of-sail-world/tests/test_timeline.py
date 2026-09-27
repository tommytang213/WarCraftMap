import copy, json, sys, unittest
from pathlib import Path
CATEGORY_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(CATEGORY_ROOT/"_shared"/"engine"))
import campaign_save, timeline

BASE={"calendar":"proleptic_gregorian","startDate":"1450-01-01","endDate":"1820-12-31","initialDate":"1450-01-01","eras":[{"id":"early_modern","name":"Early Modern","startDate":"1450-01-01","endDate":"1820-12-31"}],"eventDefinitions":[{"id":"alpha"},{"id":"beta"}],"schedules":[{"id":"annual_alpha","eventId":"alpha","firstDate":"1450-01-01","priority":20,"recurrence":{"unit":"years","interval":1,"untilDate":"1453-01-01"}},{"id":"beta_first","eventId":"beta","firstDate":"1450-01-01","priority":10}]}
class TimelineTests(unittest.TestCase):
 def test_boundaries_and_era(self):
  self.assertEqual("early_modern",timeline.active_era(BASE,"1450-01-01")); self.assertEqual("early_modern",timeline.active_era(BASE,"1820-12-31"))
  with self.assertRaises(timeline.TimelineError): timeline.advance(BASE,timeline.initial_state(BASE),"1821-01-01")
 def test_simultaneous_order_and_stable_ids(self):
  state,events=timeline.advance(BASE,timeline.initial_state(BASE),"1450-01-01")
  self.assertEqual(["beta_first","annual_alpha"],[x.schedule_id for x in events]); self.assertEqual("1450-01-01",state["currentDate"])
 def test_large_jump_equals_incremental_and_is_deterministic(self):
  direct,events=timeline.advance(BASE,timeline.initial_state(BASE),"1453-01-01")
  state=timeline.initial_state(BASE); daily=[]
  for year in range(1450,1454): state,part=timeline.advance(BASE,state,f"{year}-01-01"); daily.extend(part)
  self.assertEqual(direct,state); self.assertEqual(events,tuple(daily)); self.assertEqual(events,timeline.advance(BASE,timeline.initial_state(BASE),"1453-01-01")[1])
 def test_month_end_recurrence_is_defined(self):
  data=copy.deepcopy(BASE); data["schedules"]=[{"id":"month_end","eventId":"alpha","firstDate":"1452-01-31","priority":0,"recurrence":{"unit":"months","interval":1,"untilDate":"1452-03-31"}}]
  _,events=timeline.advance(data,timeline.initial_state(data),"1452-03-31"); self.assertEqual(["1452-01-31","1452-02-29","1452-03-29"],[x.date for x in events])
 def test_save_load_round_trip_uses_stable_data(self):
  state,_=timeline.advance(BASE,timeline.initial_state(BASE),"1500-01-01")
  raw=campaign_save.serialize_save(build_version="1",scenario_id="test",scenario_version="1",slot=campaign_save.SaveSlot("manual",1),created_at="now",world_state={"timeline":state},player_state={})
  loaded=campaign_save.load_save(raw)["state"]["world"]["timeline"]; timeline.validate_state(BASE,loaded); self.assertEqual(state,loaded); self.assertNotIn("timer",json.dumps(loaded).lower())
 def test_malformed_definitions_and_state(self):
  cases=[]
  bad=copy.deepcopy(BASE); bad["endDate"]="1449-01-01"; cases.append(bad)
  bad=copy.deepcopy(BASE); bad["eventDefinitions"].append({"id":"alpha"}); cases.append(bad)
  bad=copy.deepcopy(BASE); bad["schedules"][0]["eventId"]="missing"; cases.append(bad)
  bad=copy.deepcopy(BASE); bad["schedules"][0]["recurrence"]["interval"]=0; cases.append(bad)
  bad=copy.deepcopy(BASE); del bad["schedules"][0]["priority"]; cases.append(bad)
  for value in cases:
   with self.subTest(value=value), self.assertRaises(timeline.TimelineError): timeline.validate_definition(value)
  state=timeline.initial_state(BASE); state["pendingSchedules"][0]["scheduleId"]="missing"
  with self.assertRaisesRegex(timeline.TimelineError,"missing schedule reference"): timeline.validate_state(BASE,state)
 def test_research_time_query_never_locks(self):
  self.assertEqual(1.0,timeline.research_cost_multiplier(1500,"1500-01-01",3,0.1)); self.assertEqual(8.0,timeline.research_cost_multiplier(1500,"1450-01-01",3,0.1))
if __name__=="__main__": unittest.main()
