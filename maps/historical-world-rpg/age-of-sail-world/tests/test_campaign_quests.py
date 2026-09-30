import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from quest_event import QuestEventError, QuestEventRuntime
from quest_journal import QuestJournal, QuestJournalSaveAdapter

SPEC = importlib.util.spec_from_file_location("campaign_quests", ROOT / "tooling" / "campaign_quests.py")
CAMPAIGN = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(CAMPAIGN)
WORLD = json.loads((ROOT / "scenario" / "world" / "world.json").read_text(encoding="utf-8"))
SOURCE = json.loads((ROOT / "scenario" / "campaign-quests.json").read_text(encoding="utf-8"))


class Adapters:
    """Deterministic stand-in for the existing scenario-neutral subsystem boundary."""
    def evaluate_condition(self, condition_id, refs, snapshot, context):
        return condition_id in context.get("satisfied", ())

    def apply_outcomes(self, outcomes, snapshot, context):
        if context.get("reject_rewards"):
            raise QuestEventError("adapter rejected atomic reward batch")
        candidate = copy.deepcopy(snapshot)
        deliveries = candidate["externalState"].setdefault("deliveries", [])
        deliveries.extend((x["id"], x["outcomeId"]) for x in outcomes)
        return candidate


def definitions():
    return {"quests": copy.deepcopy(WORLD["quests"]), "events": copy.deepcopy(WORLD["events"]), "discoveries": []}


def finish(runtime, quest_id, choices=None, context=None):
    """Complete a quest through named branch choices, satisfying each active stage."""
    choices = choices or {}
    while True:
        state = next(x for x in runtime.snapshot()["quests"] if x["id"] == quest_id)
        quest = next(x for x in WORLD["quests"] if x["id"] == quest_id)
        stage = next(x for x in quest["stages"] if x["id"] == state["stageId"])
        for objective_id in stage["objectiveIds"]:
            runtime.set_objective_complete(quest_id, objective_id)
        if not stage["nextStageIds"]:
            runtime.complete_quest(quest_id, context=context or {})
            return
        runtime.advance_quest(quest_id, choices.get(stage["id"], stage["nextStageIds"][0]))


class CampaignQuestTests(unittest.TestCase):
    def setUp(self):
        self.runtime = QuestEventRuntime(definitions(), extensions=Adapters(), authoritative_state={"deliveries": []})

    def test_source_projection_coverage_references_and_graphs_are_current(self):
        CAMPAIGN.validate(SOURCE, WORLD)
        self.assertEqual(WORLD, CAMPAIGN.project(SOURCE, WORLD))
        regional = {q["campaign"]["region"] for q in WORLD["quests"] if q["campaign"]["chainKind"] == "regional"}
        self.assertEqual(set(SOURCE["coverageTargets"]["majorRegions"]), regional)
        self.assertEqual(1, sum(q["campaign"]["chainKind"] == "long" for q in WORLD["quests"]))

    def test_success_alternate_failed_cancelled_and_unavailable_participant_paths(self):
        # Exercise every regional success path once.
        for quest in (q for q in WORLD["quests"] if q["campaign"]["chainKind"] == "regional"):
            self.runtime.activate_quest(quest["id"]); finish(self.runtime, quest["id"])
        # Explicit unavailable-character alternatives do not require their character objective.
        alternate = QuestEventRuntime(definitions(), extensions=Adapters())
        alternate.activate_quest("india_stars_and_pepper")
        finish(alternate, "india_stars_and_pepper", {"market_measure": "consult_pilots"})
        state = next(x for x in alternate.snapshot()["quests"] if x["id"] == "india_stars_and_pepper")
        self.assertEqual("completed", state["status"])
        self.assertNotIn("meet_krishnadevaraya", state["completedObjectiveIds"])
        failed = QuestEventRuntime(definitions()); failed.activate_quest("pacific_stars_between_islands"); failed.fail_quest("pacific_stars_between_islands")
        cancelled = QuestEventRuntime(definitions()); cancelled.activate_quest("east_asia_coastal_record"); cancelled.cancel_quest("east_asia_coastal_record")
        self.assertEqual("failed", next(x for x in failed.snapshot()["quests"] if x["id"] == "pacific_stars_between_islands")["status"])
        self.assertEqual("cancelled", next(x for x in cancelled.snapshot()["quests"] if x["id"] == "east_asia_coastal_record")["status"])

    def test_changed_control_absence_and_blocked_route_never_silently_complete(self):
        runtime = QuestEventRuntime(definitions(), extensions=Adapters())
        runtime.activate_quest("southeast_strait_accord")
        # Neither changed ownership nor a blocked route makes authoritative objectives true.
        runtime.evaluate_objectives(context={"controller": "foreign", "blocked_routes": ["node_malacca_sea"]})
        state = next(x for x in runtime.snapshot()["quests"] if x["id"] == "southeast_strait_accord")
        self.assertEqual(("active", []), (state["status"], state["completedObjectiveIds"]))
        runtime.set_objective_complete("southeast_strait_accord", "witness_competition")
        runtime.advance_quest("southeast_strait_accord", "guard_convoy")
        runtime.set_objective_complete("southeast_strait_accord", "defend_strait")
        runtime.advance_quest("southeast_strait_accord", "record_accord")
        runtime.set_objective_complete("southeast_strait_accord", "return_malacca")
        runtime.complete_quest("southeast_strait_accord")

    def test_long_chain_prerequisites_alternate_branch_and_all_terminal_paths(self):
        with self.assertRaisesRegex(QuestEventError, "prerequisites"):
            self.runtime.activate_quest("ocean_of_accounts")
        for quest_id in ("europe_printed_compact", "africa_niger_manuscripts"):
            self.runtime.activate_quest(quest_id); finish(self.runtime, quest_id)
        self.runtime.activate_quest("ocean_of_accounts")
        finish(self.runtime, "ocean_of_accounts", {"monsoon_ledger": "chart_detour"})
        state = next(x for x in self.runtime.snapshot()["quests"] if x["id"] == "ocean_of_accounts")
        self.assertEqual("completed", state["status"])
        self.assertNotIn("obtain_coastal_record", state["completedObjectiveIds"])

    def test_rewards_are_atomic_exactly_once_and_checkpoint_resume_stable(self):
        self.runtime.activate_quest("pacific_stars_between_islands")
        # Stop at terminal so a rejected multi-system delivery can be compared exactly.
        quest = next(x for x in WORLD["quests"] if x["id"] == "pacific_stars_between_islands")
        while True:
            state = next(x for x in self.runtime.snapshot()["quests"] if x["id"] == quest["id"])
            stage = next(x for x in quest["stages"] if x["id"] == state["stageId"])
            for oid in stage["objectiveIds"]: self.runtime.set_objective_complete(quest["id"], oid)
            if not stage["nextStageIds"]: break
            self.runtime.advance_quest(quest["id"], stage["nextStageIds"][0])
        checkpoint = self.runtime.snapshot()
        with self.assertRaisesRegex(QuestEventError, "atomic reward"):
            self.runtime.complete_quest(quest["id"], context={"reject_rewards": True})
        self.assertEqual(checkpoint, self.runtime.snapshot())
        self.runtime.complete_quest(quest["id"])
        delivered = self.runtime.snapshot()["externalState"]["deliveries"]
        self.assertEqual(len(quest["outcomes"]), len(delivered))
        restored = QuestEventRuntime(definitions(), extensions=Adapters()); restored.restore(self.runtime.snapshot())
        self.assertEqual(self.runtime.snapshot(), restored.snapshot())
        with self.assertRaises(QuestEventError): restored.complete_quest(quest["id"])
        self.assertEqual(delivered, restored.snapshot()["externalState"]["deliveries"])

    def test_guidance_unknown_approximate_hidden_turn_in_breadcrumbs_and_ui_rebuild(self):
        journal = QuestJournal(definitions(), WORLD["regionalGeography"], WORLD["questLocations"])
        self.runtime.activate_quest("ocean_of_accounts") if False else None
        self.runtime.activate_quest("africa_niger_manuscripts")
        model = journal.reconstruct(self.runtime.snapshot(), physical_region_id="europe")
        entry = next(q for g in model["groups"] for q in g["quests"] if q["id"] == "africa_niger_manuscripts")
        self.assertEqual("approximate", entry["guidance"]["precision"])
        self.assertIsNone(entry["guidance"]["locationId"])
        self.assertEqual([], entry["guidance"]["breadcrumbs"])
        journal.discover_transition("europe_africa_boundary")
        rebuilt = journal.reconstruct(self.runtime.snapshot(), physical_region_id="europe")
        entry = next(q for g in rebuilt["groups"] for q in g["quests"] if q["id"] == "africa_niger_manuscripts")
        self.assertEqual(["europe", "africa"], [x["regionId"] for x in entry["guidance"]["breadcrumbs"]])
        self.runtime.set_objective_complete("africa_niger_manuscripts", "search_sahel")
        self.runtime.advance_quest("africa_niger_manuscripts", "replace_copies")
        self.runtime.set_objective_complete("africa_niger_manuscripts", "fund_copies")
        self.runtime.advance_quest("africa_niger_manuscripts", "return_manuscripts")
        self.runtime.set_objective_complete("africa_niger_manuscripts", "restore_archive")
        awaiting = journal.reconstruct(self.runtime.snapshot(), physical_region_id="europe")
        entry = next(q for g in awaiting["groups"] for q in g["quests"] if q["id"] == "africa_niger_manuscripts")
        self.assertEqual(("awaiting_turn_in", "turn_in"), (entry["group"], entry["guidance"]["purpose"]))
        saved = QuestJournalSaveAdapter(journal).capture_world({"questEventState": self.runtime.snapshot()})
        replacement = QuestJournal(definitions(), WORLD["regionalGeography"], WORLD["questLocations"])
        restored = QuestJournalSaveAdapter(replacement).reconstruct(saved); QuestJournalSaveAdapter(replacement).activate(restored)
        self.assertEqual(awaiting, replacement.reconstruct(self.runtime.snapshot(), physical_region_id="europe"))

    def test_hidden_clue_has_no_information_leak_until_exact_location_is_discovered(self):
        journal = QuestJournal(definitions(), WORLD["regionalGeography"], WORLD["questLocations"])
        self.runtime.activate_quest("americas_highland_messages")
        self.runtime.set_objective_complete("americas_highland_messages", "meet_interpreter")
        self.runtime.advance_quest("americas_highland_messages", "find_refuge")
        model = journal.reconstruct(self.runtime.snapshot(), physical_region_id="americas_caribbean")
        entry = next(q for g in model["groups"] for q in g["quests"] if q["id"] == "americas_highland_messages")
        self.assertIsNone(entry["guidance"])
        journal.learn_clue("highland_knotted_clue")
        entry = next(q for g in journal.reconstruct(self.runtime.snapshot(), physical_region_id="americas_caribbean")["groups"] for q in g["quests"] if q["id"] == "americas_highland_messages")
        self.assertEqual("hidden", entry["guidance"]["precision"])
        self.assertEqual({"track": False, "showOnMap": False}, entry["actions"])


if __name__ == "__main__":
    unittest.main()
