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


if __name__ == "__main__":
    unittest.main()
