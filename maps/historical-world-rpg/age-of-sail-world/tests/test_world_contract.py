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


if __name__ == "__main__":
    unittest.main()
