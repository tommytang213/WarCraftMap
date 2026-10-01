import copy, importlib.util, json, sys, unittest
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CATEGORY=ROOT.parent
sys.path.insert(0,str(CATEGORY/"_shared"/"engine"))
import historical_events, quest_event, timeline

spec=importlib.util.spec_from_file_location("historical_events_tool",ROOT/"tooling"/"historical_events.py")
tool=importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
WORLD=json.loads((ROOT/"scenario"/"world"/"world.json").read_text())
SOURCE=json.loads((ROOT/"scenario"/"historical-events.json").read_text())

def external_state():
    active=[x["id"] for key in ("polities","provinces","settlements") for x in WORLD[key]]
    return {"activeEntityIds":active,"ownership":{x["id"]:x["legalOwnerPolityId"] for x in WORLD["provinces"]},
      "control":{x["id"]:x["controllerPolityId"] for x in WORLD["provinces"]},
      "prosperity":{x["id"]:50 for x in WORLD["provinces"]},"treasury":{x["id"]:100 for x in WORLD["polities"]},
      "relations":{},"activeWars":[],"knownResearchIds":[x["id"] for x in WORLD["technologies"]+WORLD["institutions"]],
      "completedResearchIds":["celestial_navigation"],"flags":{},"historicalLog":[]}

def runtime(state=None, events=None):
    definitions={"quests":[],"discoveries":[],"events":events or WORLD["events"]}
    return quest_event.QuestEventRuntime(definitions,extensions=historical_events.HistoricalExtensions(events or WORLD["events"]),authoritative_state=state or external_state())

class HistoricalEventTests(unittest.TestCase):
    def test_source_projection_and_coverage_are_current(self):
        tool.validate(SOURCE,WORLD); self.assertEqual(WORLD,tool.project(SOURCE,WORLD))
        self.assertEqual({x["id"] for x in WORLD["events"]},{x["id"] for x in WORLD["timeline"]["eventDefinitions"]})
        self.assertTrue(any(x.get("recurrence") for x in WORLD["timeline"]["schedules"]))
        self.assertTrue(any(not x.get("recurrence") for x in WORLD["timeline"]["schedules"]))
        bad=copy.deepcopy(SOURCE); bad["events"][0]["alternatives"][0]["effects"][0]["targetId"]="missing_province"
        with self.assertRaises(AssertionError): tool.validate(bad,WORLD)

    def test_large_jump_has_canonical_simultaneous_order_and_one_shot_dedup(self):
        initial=timeline.initial_state(WORLD["timeline"])
        final, occurrences=timeline.advance(WORLD["timeline"],initial,"1820-12-31")
        self.assertEqual(list(occurrences),sorted(occurrences,key=lambda x:(x.date,x.priority,x.schedule_id,x.occurrence,x.event_id)))
        r=runtime(); historical_events.enqueue_occurrences(r,occurrences)
        r.process_until(date(1820,12,31).toordinal())
        by_id={x["id"]:x["occurrences"] for x in r.snapshot()["events"]}
        self.assertEqual(1,by_id["fall_of_constantinople_pressure"])
        self.assertGreater(by_id["atlantic_hurricane_pressure"],1)
        # Re-enqueuing identical schedule occurrences is idempotent.
        before=r.snapshot(); historical_events.enqueue_occurrences(r,occurrences); r.process_until(date(1820,12,31).toordinal()); self.assertEqual(before,r.snapshot())
        self.assertEqual("1820-12-31",final["currentDate"])

    def test_checkpoint_resume_equals_uninterrupted(self):
        definition=WORLD["timeline"]
        full_occ=timeline.advance(definition,timeline.initial_state(definition),"1820-12-31")[1]
        full=runtime(); historical_events.enqueue_occurrences(full,full_occ); full.process_until(date(1820,12,31).toordinal())
        mid_state,first=timeline.advance(definition,timeline.initial_state(definition),"1650-01-01")
        part=runtime(); historical_events.enqueue_occurrences(part,first); part.process_until(date(1650,1,1).toordinal())
        saved=part.snapshot(); resumed=runtime(); resumed.restore(saved)
        _,second=timeline.advance(definition,mid_state,"1820-12-31"); historical_events.enqueue_occurrences(resumed,second); resumed.process_until(date(1820,12,31).toordinal())
        self.assertEqual(full.snapshot(),resumed.snapshot())

    def test_altered_history_selects_non_forcing_alternatives_or_blocks(self):
        event=next(x for x in WORLD["events"] if x["id"]=="fall_of_constantinople_pressure")
        state=external_state(); state["ownership"]["byzantine_thrace"]="ottoman_empire"
        choice=historical_events.choose_alternative(event,"changed",state)
        self.assertNotEqual("ottoman_breakthrough",choice["id"])
        state["activeEntityIds"].remove("byzantine_empire")
        self.assertIsNone(historical_events.choose_alternative(event,"changed",state))
        voyage=next(x for x in WORLD["events"] if x["id"]=="indian_ocean_route_pressure")
        state=external_state(); state["completedResearchIds"]=[]
        self.assertEqual("voyage_fails",historical_events.choose_alternative(voyage,"missing_discovery",state)["id"])
        synthetic={"id":"ended_war","historical":{"alternatives":[{"id":"continue","weight":1,"conditions":[{"kind":"war_active","valueId":"war_one"}],"effects":[]},{"id":"peace","weight":1,"conditions":[{"kind":"war_inactive","valueId":"war_one"}],"effects":[]}]}}
        self.assertEqual("peace",historical_events.choose_alternative(synthetic,"ended",state)["id"])

    def test_multi_system_effects_rollback_atomically(self):
        state=external_state(); before=copy.deepcopy(state)
        effects=[{"kind":"adjust_prosperity","targetId":"greater_london","value":5},{"kind":"complete_research","targetId":"missing_technology"}]
        with self.assertRaises(historical_events.HistoricalEventError): historical_events.apply_effects(state,effects)
        self.assertEqual(before,state)

    def test_representative_event_from_every_region_and_century(self):
        regions={x["historical"]["region"] for x in WORLD["events"]}
        self.assertTrue({"europe","africa","middle_east_india","southeast_asia","east_asia","americas_caribbean","pacific"}<=regions)
        years={date.fromisoformat(x["firstDate"]).year//100 for x in WORLD["timeline"]["schedules"]}
        self.assertTrue({14,15,16,17,18}<=years)

    def test_multi_century_trajectories_are_relevant_bounded_and_deterministic(self):
        definition=WORLD["timeline"]
        occurrences=timeline.advance(definition,timeline.initial_state(definition),"1820-12-31")[1]
        self.assertEqual(59,len(occurrences))
        self.assertLessEqual(len(occurrences),80)  # fewer than one pressure per five campaign years
        for label,mutate in (
            ("baseline",lambda state:None),
            ("ottoman_thrace",lambda state:state["ownership"].__setitem__("byzantine_thrace","ottoman_empire")),
            ("collapsed_polities",lambda state:state["activeEntityIds"].remove("byzantine_empire")),
        ):
            state=external_state(); mutate(state)
            first=runtime(state); historical_events.enqueue_occurrences(first,occurrences); first.process_until(date(1820,12,31).toordinal())
            second=runtime(copy.deepcopy(state)); historical_events.enqueue_occurrences(second,occurrences); second.process_until(date(1820,12,31).toordinal())
            self.assertEqual(first.snapshot(),second.snapshot(),label)
            fired=sum(x["occurrences"] for x in first.snapshot()["events"])
            self.assertLessEqual(fired,len(occurrences),label)
            self.assertGreaterEqual(fired,45,label)

if __name__=="__main__": unittest.main()
