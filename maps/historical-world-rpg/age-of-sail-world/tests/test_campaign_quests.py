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


    def test_hang_tuah_personal_quest_is_grounded_in_malacca(self):
        quest = next(q for q in SOURCE["quests"] if q["id"] == "hang_tuah_personal_quest")
        self.assertEqual(["settlement", "malacca"], quest["turnIn"])
        self.assertEqual(["polity", "malacca_sultanate"], quest["stages"][1]["objectives"][0]["refs"][0])
        self.assertEqual(["polity", "malacca_sultanate"], quest["rewards"][1]["refs"][0])
        private = quest["stages"][2]["objectives"][0]
        self.assertEqual(["settlement", "malacca"], private["refs"][0])
        self.assertEqual("malacca", private["guidance"]["settlementId"])
        self.assertIn("seal", quest["summary"].lower())
        self.assertIn("crew", private["text"].lower())
        self.assertNotIn("Personal Reckoning", quest["title"])
        self.assertEqual(["public_duty", "private_duty"], quest["stages"][0]["next"])
        self.assertEqual(["reckoning"], quest["stages"][1]["next"])
        self.assertEqual(["reckoning"], quest["stages"][2]["next"])

    def test_nzinga_kongo_envoys_references_and_choices(self):
        quest = next(q for q in SOURCE["quests"] if q["id"] == "nzinga_mbande_personal_quest")
        self.assertEqual(["character", "nzinga_mbande"], quest["giver"])
        self.assertEqual(["settlement", "mbanza_kongo"], quest["turnIn"])
        self.assertEqual(["polity", "kongo_kingdom"], quest["stages"][1]["objectives"][0]["refs"][0])
        self.assertEqual(["polity", "kongo_kingdom"], quest["rewards"][1]["refs"][0])
        private = quest["stages"][2]["objectives"][0]
        self.assertEqual(["settlement", "mbanza_kongo"], private["refs"][0])
        self.assertEqual("mbanza_kongo", private["guidance"]["settlementId"])
        self.assertIn("Ndongo", quest["summary"])
        self.assertIn("Matamba", quest["summary"])
        self.assertIn("coerced", private["text"])
        self.assertNotIn("songhai", json.dumps(quest).lower())
        self.assertNotIn("kilwa", json.dumps(quest).lower())
        self.assertEqual(["public_duty", "private_duty"], quest["stages"][0]["next"])
        self.assertEqual(["reckoning"], quest["stages"][1]["next"])
        self.assertEqual(["reckoning"], quest["stages"][2]["next"])


    def test_hang_tuah_branch_rewards_follow_reached_stages_and_survive_reload(self):
        projected = CAMPAIGN.project(SOURCE, WORLD)
        quest = next(q for q in projected["quests"] if q["id"] == "hang_tuah_personal_quest")
        scopes = {r["id"]: r.get("requiresReachedStageIds") for r in quest["outcomes"]}
        self.assertEqual(["private_duty"], scopes["hang_tuah_loyalty"])
        self.assertEqual(["public_duty"], scopes["hang_tuah_office"])
        defs = {"quests": [quest], "events": [], "discoveries": []}
        for branch, reward in (("public_duty", "hang_tuah_office"), ("private_duty", "hang_tuah_loyalty")):
            runtime = QuestEventRuntime(defs, extensions=Adapters(), authoritative_state={"deliveries": []})
            runtime.activate_quest(quest["id"])
            for stage_id in ("confidence", branch, "reckoning"):
                stage = next(s for s in quest["stages"] if s["id"] == stage_id)
                for objective in stage["objectiveIds"]:
                    runtime.set_objective_complete(quest["id"], objective)
                if stage_id == "confidence":
                    runtime.advance_quest(quest["id"], branch)
                elif stage_id == branch:
                    runtime.advance_quest(quest["id"], "reckoning")
            before = runtime.snapshot()
            with self.assertRaisesRegex(QuestEventError, "atomic reward"):
                runtime.complete_quest(quest["id"], context={"reject_rewards": True})
            self.assertEqual(before, runtime.snapshot())
            runtime.complete_quest(quest["id"])
            self.assertEqual([reward], [x[0] for x in runtime.snapshot()["externalState"]["deliveries"]])
            restored = QuestEventRuntime(defs, extensions=Adapters())
            restored.restore(runtime.snapshot())
            self.assertEqual(runtime.snapshot(), restored.snapshot())
            with self.assertRaises(QuestEventError):
                restored.complete_quest(quest["id"])

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


    def test_personal_quest_prose_is_distinct_and_situated(self):
        # Editorial source gate: distinct actors and dilemmas, never generic quest template text.
        personal = [quest for quest in SOURCE["quests"] if quest["chainKind"] == "personal"]
        expected = {
            "leonardo_da_vinci_personal_quest": ("lagoon", "Venice"),
            "piri_reis_personal_quest": ("soundings", "Aden"),
            "xu_guangqi_personal_quest": ("grain", "Quanzhou"),
            "malintzin_personal_quest": ("translated", "Tenochtitlan"),
            "nzinga_mbande_personal_quest": ("Ndongo", "Kongo"),
            "hang_tuah_personal_quest": ("letters", "Malacca"),
            "kamehameha_i_personal_quest": ("Hawaiian", "royal center"),
        }
        self.assertEqual(set(expected), {quest["id"] for quest in personal})
        self.assertEqual(len(personal), len({quest["title"] for quest in personal}))
        for quest in personal:
            with self.subTest(quest=quest["id"]):
                rendered = "\\n".join([quest["title"], quest["summary"]] +
                    [obj["text"] for stage in quest["stages"] for obj in stage["objectives"]])
                for term in expected[quest["id"]]:
                    self.assertIn(term.lower(), rendered.lower())
                for template in ("A Personal Reckoning", "Earn the companion's confidence",
                                 "Use the companion's office to negotiate a durable answer",
                                 "Protect the companion's personal obligation at home"):
                    self.assertNotIn(template, rendered)

if __name__ == "__main__":
    unittest.main()
