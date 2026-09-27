import copy
import importlib.util
import json
import unittest
from pathlib import Path


CATEGORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = CATEGORY_ROOT / "_shared" / "tooling" / "validate_world.py"
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "quest_events"

spec = importlib.util.spec_from_file_location("validate_world_quest_events", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class QuestEventContractTests(unittest.TestCase):
    def setUp(self):
        self.valid = json.loads((FIXTURE_ROOT / "valid.json").read_text(encoding="utf-8"))

    def assert_invalid(self, data, expected):
        with self.assertRaisesRegex(validator.ValidationError, expected):
            validator.validate_quest_events(data, validator.fail, validator.require_id, validator.unique_index)

    def test_valid_graph_and_explicit_repeatable_event(self):
        quests, events = validator.validate_quest_events(
            self.valid, validator.fail, validator.require_id, validator.unique_index
        )
        self.assertEqual({"orientation", "follow_up"}, set(quests))
        self.assertTrue(events["periodic_notice"]["repeatable"])

    def test_duplicate_ids_identify_collection_and_id(self):
        data = copy.deepcopy(self.valid)
        data["quests"].append(copy.deepcopy(data["quests"][0]))
        self.assert_invalid(data, r"quests: duplicate ID 'orientation'")

    def test_broken_cross_reference_identifies_reference_path(self):
        data = copy.deepcopy(self.valid)
        data["quests"][1]["prerequisites"][0]["id"] = "missing_quest"
        self.assert_invalid(data, r"quest follow_up\.prerequisites\[0\]\.id: missing quest reference 'missing_quest'")

    def test_missing_stage_reference_identifies_reference_path(self):
        data = copy.deepcopy(self.valid)
        data["events"][0]["prerequisites"][0]["stageId"] = "missing_stage"
        self.assert_invalid(data, r"event periodic_notice\.prerequisites\[0\]\.stageId: missing stage reference 'missing_stage'")

    def test_invalid_transition_identifies_outcome(self):
        data = copy.deepcopy(self.valid)
        outcome = data["quests"][0]["outcomes"][0]
        outcome["fromStageId"], outcome["toStageId"] = outcome["toStageId"], outcome["fromStageId"]
        self.assert_invalid(data, r"quest orientation\.outcomes\[0\]: invalid stage transition")

    def test_unresolved_world_reference_identifies_objective_path(self):
        data = copy.deepcopy(self.valid)
        data["quests"][0]["objectives"][0]["entityRefs"][0]["id"] = "missing_hub"
        self.assert_invalid(data, r"quest orientation\.objectives\[visit_hub\]\.entityRefs\[0\]\.id: unresolved settlement reference 'missing_hub'")

    def test_deliberately_cyclic_prerequisite_fixture(self):
        data = json.loads((FIXTURE_ROOT / "cyclic_prerequisites.json").read_text(encoding="utf-8"))
        self.assert_invalid(data, r"prerequisites\[0\]: cyclic prerequisite relationship")

    def test_non_repeatable_event_cannot_request_repeat(self):
        data = copy.deepcopy(self.valid)
        data["events"][0]["repeatable"] = False
        self.assert_invalid(data, r"repeat: event 'periodic_notice' is not repeatable")


if __name__ == "__main__":
    unittest.main()
