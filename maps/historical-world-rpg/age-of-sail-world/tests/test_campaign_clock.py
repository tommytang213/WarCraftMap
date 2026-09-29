import copy, json, sys, unittest
from pathlib import Path

CATEGORY_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(CATEGORY_ROOT/"_shared"/"engine"))
import campaign_clock, campaign_save, timeline

DEFINITION={"calendar":"proleptic_gregorian","startDate":"1450-01-01","endDate":"1450-01-12","initialDate":"1450-01-01","eras":[{"id":"opening","name":"Opening","startDate":"1450-01-01","endDate":"1450-01-05"},{"id":"later","name":"Later","startDate":"1450-01-06","endDate":"1450-01-12"}],"eventDefinitions":[{"id":"alpha"},{"id":"beta"}],"schedules":[{"id":"beta_once","eventId":"beta","firstDate":"1450-01-03","priority":5},{"id":"alpha_daily","eventId":"alpha","firstDate":"1450-01-03","priority":5,"recurrence":{"unit":"days","interval":2,"untilDate":"1450-01-11"}}]}

class FakeTimer:
 def __init__(self): self.callback=None; self.stops=0
 def start(self,interval,callback): self.interval=interval; self.callback=callback
 def stop(self): self.stops+=1; self.callback=None
 def tick(self,elapsed): self.callback(elapsed)

class CampaignClockTests(unittest.TestCase):
 def test_normal_paused_accelerated_and_boundaries(self):
  clock=campaign_clock.CampaignClock(DEFINITION)
  self.assertEqual((1450,1,1,"opening"),(clock.time().year,clock.time().month,clock.time().day,clock.time().era_id))
  clock.advance_elapsed(1); self.assertEqual("1450-01-02",clock.time().iso_date)
  clock.set_paused(True); clock.advance_elapsed(20); self.assertEqual("1450-01-02",clock.time().iso_date)
  clock.set_paused(False); self.assertTrue(clock.set_speed(3)); clock.advance_elapsed(1)
  self.assertEqual("1450-01-05",clock.time().iso_date)
  before=clock.state(); self.assertEqual((),clock.advance_to("1450-01-01")); self.assertEqual(before,clock.state()); self.assertIn("between currentDate",clock.diagnostic)
  clock.advance_elapsed(100); self.assertEqual("1450-01-12",clock.time().iso_date)
  before=clock.state(); self.assertEqual((),clock.advance_to("1450-01-13")); self.assertEqual(before,clock.state())

 def test_large_jump_matches_headless_and_orders_simultaneous_recurring_events(self):
  clock=campaign_clock.CampaignClock(DEFINITION); seen=[]
  for system in campaign_clock.SYSTEM_ORDER:
   clock.subscribe(system,lambda event, system=system: seen.append((event.date,event.schedule_id,system)))
  emitted=clock.advance_to("1450-01-11")
  expected_state,expected=timeline.advance(DEFINITION,timeline.initial_state(DEFINITION),"1450-01-11")
  self.assertEqual(expected,emitted); self.assertEqual(expected_state,clock.state()["timeline"])
  self.assertEqual(["alpha_daily","beta_once"],[x.schedule_id for x in emitted[:2]])
  self.assertEqual(list(campaign_clock.SYSTEM_ORDER),[x[2] for x in seen[:5]])

 def test_save_load_is_exactly_once_and_restore_is_atomic(self):
  first=campaign_clock.CampaignClock(DEFINITION); delivered=list(first.advance_to("1450-01-07"))
  raw=campaign_save.serialize_save(build_version="1",scenario_id="test",scenario_version="1",slot=campaign_save.SaveSlot("manual",1),created_at="now",world_state={"clock":first.state()},player_state={})
  saved=campaign_save.load_save(raw)["state"]["world"]["clock"]
  resumed=campaign_clock.CampaignClock(DEFINITION); resumed.restore(saved)
  delivered.extend(resumed.advance_to("1450-01-12"))
  _,expected=timeline.advance(DEFINITION,timeline.initial_state(DEFINITION),"1450-01-12")
  self.assertEqual(expected,tuple(delivered)); self.assertNotIn("timer",json.dumps(saved).lower())
  before=resumed.state(); invalid=copy.deepcopy(before); invalid["timeline"]["pendingSchedules"].append({"scheduleId":"missing","nextDate":"1450-01-12","occurrencesEmitted":0})
  with self.assertRaises(timeline.TimelineError): resumed.restore(invalid)
  self.assertEqual(before,resumed.state())

 def test_timer_adapter_can_be_destroyed_and_reconstructed(self):
  clock=campaign_clock.CampaignClock(DEFINITION); one=FakeTimer(); clock.attach_timer(one); one.tick(2)
  clock.detach_timer(); self.assertEqual(1,one.stops); self.assertEqual("1450-01-03",clock.time().iso_date)
  two=FakeTimer(); clock.attach_timer(two,.5); two.tick(2); self.assertEqual("1450-01-05",clock.time().iso_date)

 def test_fractional_scheduler_state_survives_save(self):
  clock=campaign_clock.CampaignClock(DEFINITION,days_per_second=.25); clock.advance_elapsed(3)
  restored=campaign_clock.CampaignClock(DEFINITION,days_per_second=.25); restored.restore(clock.state()); restored.advance_elapsed(1)
  self.assertEqual("1450-01-02",restored.time().iso_date)

if __name__=="__main__": unittest.main()
