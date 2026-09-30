import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_shared" / "engine"))

from quest_event import QuestEventRuntime
from quest_journal import QuestJournal, QuestJournalError, QuestJournalSaveAdapter, QuestJournalScreen


def geography():
    regions = [{"id": value} for value in ("europe", "africa", "middle_east_india", "americas_caribbean")]
    def edge(ident, source, target, directed=False):
        return {"id": ident, "from": {"regionId": source}, "to": {"regionId": target}, "directed": directed}
    return {"regions": regions, "boundaries": [
        edge("europe_africa", "europe", "africa"),
        edge("africa_middle_east", "africa", "middle_east_india"),
        edge("europe_middle_east", "europe", "middle_east_india"),
    ], "routes": [edge("atlantic", "europe", "americas_caribbean")]}


LOCATIONS = [
    {"id": "lisbon_harbor", "regionId": "europe", "settlementId": "lisbon", "position": {"x": 10, "y": 20}},
    {"id": "alexandria_docks", "regionId": "middle_east_india", "settlementId": "alexandria", "position": {"x": 30, "y": 40}},
    {"id": "hidden_ruin", "regionId": "africa", "position": {"x": 50, "y": 60}},
    {"id": "amazon_camp", "regionId": "americas_caribbean", "position": {"x": 70, "y": 80}},
]


def definitions():
    def quest(ident, title, destination, *, turn_in=True):
        journal = {
            "giver": {"kind": "character", "id": f"{ident}_giver"},
            "destinations": {"go": destination},
        }
        if turn_in:
            journal.update({
                "turnIn": {"kind": "settlement", "id": "lisbon"},
                "turnInDestination": {"precision": "exact", "regionId": "europe", "locationId": "lisbon_harbor", "settlementId": "lisbon"},
            })
        return {
            "id": ident, "title": title, "summary": f"Summary {ident}", "initialStageId": "work",
            "stages": [{"id": "work", "objectiveIds": ["go"], "nextStageIds": []}],
            "objectives": [{"id": "go", "description": f"Do {ident}", "conditionId": "never", "entityRefs": [{"kind": "settlement", "id": destination.get("settlementId", "lisbon")}]}],
            "prerequisites": [], "outcomes": [], "journal": journal,
        }
    return {"quests": [
        quest("exact_task", "Zulu", {"precision": "exact", "regionId": "middle_east_india", "locationId": "alexandria_docks", "settlementId": "alexandria"}),
        quest("approx_task", "Alpha", {"precision": "approximate", "regionId": "americas_caribbean", "locationId": "amazon_camp", "searchAreas": [{"x": 60, "y": 70, "radius": 15}]}),
        quest("region_task", "Bravo", {"precision": "region", "regionId": "africa"}),
        quest("hidden_task", "Hidden", {"precision": "hidden", "regionId": "africa", "locationId": "hidden_ruin"}),
        quest("clue_task", "Clue", {"precision": "region", "regionId": "africa", "requiredClueIds": ["heard_rumor"]}),
    ], "events": [], "discoveries": []}


class QuestJournalTests(unittest.TestCase):
    def setUp(self):
        self.defs = definitions()
        self.runtime = QuestEventRuntime(self.defs)
        self.journal = QuestJournal(self.defs, geography(), LOCATIONS)

    def activate(self, *quest_ids):
        for quest_id in quest_ids:
            self.runtime.activate_quest(quest_id)

    def model(self, physical="europe", command="africa"):
        return self.journal.reconstruct(self.runtime.snapshot(), physical_region_id=physical, command_region_id=command)

    def entries(self, model=None):
        return [entry for group in (model or self.model())["groups"] for entry in group["quests"]]

    def entry(self, quest_id, model=None):
        return next(entry for entry in self.entries(model) if entry["id"] == quest_id)

    def test_state_grouping_stable_order_objectives_failure_and_reconstruction(self):
        self.activate("exact_task", "approx_task", "region_task")
        self.runtime.fail_quest("region_task")
        model = self.model()
        active = next(group for group in model["groups"] if group["id"] == "active")["quests"]
        self.assertEqual(["approx_task", "exact_task"], [entry["id"] for entry in active])
        self.assertFalse(self.entry("exact_task", model)["objectives"][0]["complete"])
        self.runtime.set_objective_complete("exact_task", "go")
        rebuilt = self.model()
        exact = self.entry("exact_task", rebuilt)
        self.assertEqual("awaiting_turn_in", exact["group"])
        self.assertTrue(exact["objectives"][0]["complete"])
        self.assertEqual(("turn_in", "lisbon_harbor"), (exact["guidance"]["purpose"], exact["guidance"]["locationId"]))
        self.runtime.complete_quest("exact_task")
        self.assertEqual("completed", self.entry("exact_task")["group"])
        self.assertEqual("failed", self.entry("region_task")["group"])
        self.assertIsNone(self.entry("exact_task")["guidance"])

    def test_exact_approximate_region_hidden_clues_and_prior_discovery(self):
        self.activate("exact_task", "approx_task", "region_task", "hidden_task", "clue_task")
        exact = self.entry("exact_task")
        self.assertEqual({"x": 30, "y": 40}, exact["guidance"]["marker"])
        approximate = self.entry("approx_task")
        self.assertEqual("approximate", approximate["guidance"]["precision"])
        self.assertEqual(15, approximate["guidance"]["searchAreas"][0]["radius"])
        region = self.entry("region_task")
        self.assertEqual(("region", None), (region["guidance"]["precision"], region["guidance"]["marker"]))
        hidden = self.entry("hidden_task")
        self.assertEqual("hidden", hidden["guidance"]["precision"])
        self.assertEqual({"track": False, "showOnMap": False}, hidden["actions"])
        self.assertIsNone(self.entry("clue_task")["guidance"])
        self.journal.learn_clue("heard_rumor")
        self.assertEqual("region", self.entry("clue_task")["guidance"]["precision"])
        self.journal.discover_location("hidden_ruin")
        discovered = self.entry("hidden_task")
        self.assertEqual(("exact", "hidden_ruin", {"x": 50, "y": 60}), (discovered["guidance"]["precision"], discovered["guidance"]["locationId"], discovered["guidance"]["marker"]))

    def test_known_cross_region_breadcrumbs_changes_and_physical_region(self):
        self.activate("exact_task")
        self.journal.discover_transition("europe_africa")
        self.journal.discover_transition("africa_middle_east")
        path = self.entry("exact_task")["guidance"]["breadcrumbs"]
        self.assertEqual(["europe", "africa", "middle_east_india"], [step["regionId"] for step in path])
        # A shorter newly discovered transition deterministically replaces the route.
        self.journal.discover_transition("europe_middle_east")
        path = self.entry("exact_task")["guidance"]["breadcrumbs"]
        self.assertEqual([None, "europe_middle_east"], [step["transitionId"] for step in path])
        # Command/view region is informational; routing starts at physical location.
        model = self.model(physical="africa", command="europe")
        self.assertEqual("africa", model["trackedGuidance"]["breadcrumbs"][0]["regionId"] if model["trackedGuidance"] else self.entry("exact_task", model)["guidance"]["breadcrumbs"][0]["regionId"])
        fresh = QuestJournal(self.defs, geography(), LOCATIONS)
        self.assertEqual([], fresh.reconstruct(self.runtime.snapshot(), physical_region_id="europe")["groups"][0]["quests"][0]["guidance"]["breadcrumbs"])

    def test_actions_are_informational_and_tracking_updates_deterministically(self):
        self.activate("approx_task")
        before_quest = self.runtime.snapshot()
        before_physical = {"regionId": "europe", "position": {"x": 1, "y": 2}}
        guidance = self.journal.track("approx_task", next(state for state in before_quest["quests"] if state["id"] == "approx_task"), physical_region_id="europe")
        self.assertEqual(before_quest, self.runtime.snapshot())
        self.assertEqual({"regionId": "europe", "position": {"x": 1, "y": 2}}, before_physical)
        self.assertEqual("approximate", guidance["precision"])
        self.journal.discover_location("amazon_camp")
        updated = self.model()
        self.assertEqual("exact", updated["trackedGuidance"]["precision"])
        self.runtime.set_objective_complete("approx_task", "go")
        self.assertEqual("turn_in", self.model()["trackedGuidance"]["purpose"])

    def test_save_load_checkpoint_resume_and_ui_loss(self):
        self.activate("exact_task")
        self.journal.discover_location("alexandria_docks")
        self.journal.discover_transition("europe_middle_east")
        self.journal.learn_clue("heard_rumor")
        quest_state = next(state for state in self.runtime.snapshot()["quests"] if state["id"] == "exact_task")
        self.journal.track("exact_task", quest_state, physical_region_id="europe")
        adapter = QuestJournalSaveAdapter(self.journal)
        saved = adapter.capture_world({"calendar": {"year": 1450}})
        replacement = QuestJournal(self.defs, geography(), LOCATIONS)
        reconstructed = QuestJournalSaveAdapter(replacement).reconstruct(saved)
        QuestJournalSaveAdapter(replacement).activate(reconstructed)
        self.assertEqual(self.journal.snapshot(), replacement.snapshot())
        self.assertEqual(self.model(), replacement.reconstruct(self.runtime.snapshot(), physical_region_id="europe", command_region_id="africa"))
        checkpoint = replacement.snapshot()
        replacement.clear_tracking(); replacement.restore(checkpoint)
        self.assertEqual("exact_task", replacement.snapshot()["trackedQuestId"])

    def test_invalid_state_and_false_exact_markers_are_rejected(self):
        bad = copy.deepcopy(self.journal.snapshot()); bad["discoveredLocationIds"] = ["missing"]
        with self.assertRaisesRegex(QuestJournalError, "discoveredLocationIds"):
            self.journal.restore(bad)
        self.assertEqual([], self.journal.snapshot()["discoveredLocationIds"])
        broken = definitions(); broken["quests"][0]["journal"]["destinations"]["go"].pop("locationId")
        with self.assertRaisesRegex(QuestJournalError, "requires a location"):
            QuestJournal(broken, geography(), LOCATIONS)

    def test_modal_pause_owner_survives_ui_reconstruction_and_closes_once(self):
        class Owner:
            def __init__(self, controller): self.controller, self.is_open = controller, True
            def close(self):
                if self.is_open: self.is_open = False; self.controller.owners -= 1
        class PauseController:
            def __init__(self): self.owners = 0
            def open_modal_management_screen(self): self.owners += 1; return Owner(self)
        self.activate("exact_task")
        pause = PauseController(); screen = QuestJournalScreen(self.journal, pause)
        first = screen.open(self.runtime.snapshot(), physical_region_id="europe")
        recovered = screen.recover_ui(self.runtime.snapshot(), physical_region_id="europe")
        self.assertEqual(first, recovered); self.assertEqual(1, pause.owners)
        screen.close(); screen.close(); self.assertEqual(0, pause.owners)


if __name__ == "__main__":
    unittest.main()
