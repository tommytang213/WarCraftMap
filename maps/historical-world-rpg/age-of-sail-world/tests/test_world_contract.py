import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


CATEGORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = CATEGORY_ROOT / "_shared" / "tooling" / "validate_world.py"
WORLD_PATH = Path(__file__).resolve().parents[1] / "scenario" / "world" / "world.json"

spec = importlib.util.spec_from_file_location("validate_world", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def add_character_fixture(data):
    data["traits"] = [{"id": "steadfast", "name": "Steadfast", "description": "Keeps faith under pressure."}]
    data["skills"] = [{"id": "navigation", "name": "Navigation", "description": "Plans and follows routes."}]
    data["professions"] = [{"id": "navigator", "name": "Navigator", "description": "A professional navigator."}]
    data["personalQuests"] = [{
        "id": "prove_the_route", "title": "Prove the Route",
        "summary": "Resolve a personal obligation.", "characterId": "companion_alpha"
    }]
    data["characters"] = [
        {
            "id": "companion_alpha", "displayName": "Companion Alpha",
            "biography": "Scenario-defined character display data.",
            "traitIds": ["steadfast"], "skills": [{"skillId": "navigation", "rating": 60}],
            "professionIds": ["navigator"], "personalQuestIds": ["prove_the_route"],
            "loyalty": {"score": 25, "permanentState": "none"}
        },
        {
            "id": "companion_beta", "displayName": "Companion Beta",
            "biography": "A second scenario-defined character.",
            "traitIds": [], "skills": [], "professionIds": [], "personalQuestIds": [],
            "loyalty": {"score": 0, "permanentState": "oathbound"}
        }
    ]
    data["relationshipThresholds"] = [{
        "id": "trusted_companions", "scope": "companion_relationship",
        "minimum": 50, "maximum": 100,
        "consequences": [{"kind": "buff", "contentId": "trusted_companion_synergy"}]
    }]
    data["companionRelationships"] = [{
        "id": "alpha_beta_relation", "characterAId": "companion_alpha",
        "characterBId": "companion_beta", "score": 10
    }]
    return data


class WorldContractTests(unittest.TestCase):
    def test_current_world_is_valid(self):
        validator.validate(WORLD_PATH)

    def test_duplicate_ids_are_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["settlements"].append(dict(data["settlements"][0]))
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        try:
            with self.assertRaises(validator.ValidationError):
                validator.validate(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_broken_cross_reference_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["provinces"][0]["settlementIds"] = ["nonexistent_city"]
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        try:
            with self.assertRaises(validator.ValidationError):
                validator.validate(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def assert_invalid_data(self, data):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        try:
            with self.assertRaises(validator.ValidationError):
                validator.validate(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_duplicate_military_ids_are_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["strategicUnits"].append(dict(data["strategicUnits"][0]))
        self.assert_invalid_data(data)

    def test_broken_army_membership_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["armies"][0]["formationUnitIds"] = ["missing_formation"]
        self.assert_invalid_data(data)

    def test_fleet_cannot_contain_a_formation(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["fleets"][0]["shipUnitIds"] = ["english_guard_formation"]
        self.assert_invalid_data(data)

    def test_broken_commander_reference_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["armies"][0]["commanderOfficerId"] = "missing_officer"
        self.assert_invalid_data(data)

    def test_runtime_metadata_must_match_instantiation_state(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["strategicUnits"][0]["runtimeInstantiation"]["activeObjectCount"] = 1
        self.assert_invalid_data(data)

    def test_native_food_is_not_part_of_strategic_contract(self):
        schema_path = CATEGORY_ROOT / "_shared" / "contracts" / "military.schema.json"
        schema_text = schema_path.read_text(encoding="utf-8").lower()
        self.assertNotIn('"food"', schema_text)

    def test_character_contract_fixture_is_valid(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        try:
            validator.validate(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_character_ranges_are_rejected(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["characters"][0]["loyalty"]["score"] = 101
        self.assert_invalid_data(data)
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["characters"][0]["skills"][0]["rating"] = -1
        self.assert_invalid_data(data)
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["companionRelationships"][0]["score"] = -101
        self.assert_invalid_data(data)

    def test_duplicate_character_ids_are_rejected(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["characters"].append(dict(data["characters"][0]))
        self.assert_invalid_data(data)

    def test_duplicate_companion_pairs_are_rejected_regardless_of_order(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["companionRelationships"].append({
            "id": "beta_alpha_relation", "characterAId": "companion_beta",
            "characterBId": "companion_alpha", "score": 20
        })
        self.assert_invalid_data(data)

    def test_broken_character_references_are_rejected(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["companionRelationships"][0]["characterBId"] = "missing_character"
        self.assert_invalid_data(data)
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["personalQuests"][0]["characterId"] = "missing_character"
        self.assert_invalid_data(data)

    def test_invalid_permanent_state_transitions_are_rejected(self):
        with self.assertRaises(validator.ValidationError):
            validator.validate_permanent_state_transition("oathbound", "none")
        with self.assertRaises(validator.ValidationError):
            validator.validate_permanent_state_transition("oathbound", "oathbound")
        with self.assertRaises(validator.ValidationError):
            validator.validate_permanent_state_transition("none", "none")

    def test_oathbound_may_be_entered_once(self):
        validator.validate_permanent_state_transition("none", "oathbound")

    def test_threshold_range_must_be_ordered(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["relationshipThresholds"][0]["minimum"] = 75
        data["relationshipThresholds"][0]["maximum"] = 50
        self.assert_invalid_data(data)


if __name__ == "__main__":
    unittest.main()
