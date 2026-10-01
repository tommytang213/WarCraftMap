import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tooling"))
import validate_recovery_documentation as recovery_docs


class RecoveryDocumentationTests(unittest.TestCase):
    def test_release_guidance_matches_authoritative_contracts(self):
        support = recovery_docs.validate()
        self.assertEqual(15, next(x["count"] for x in support["saveSlots"] if x["kind"] == "autosave"))


if __name__ == "__main__":
    unittest.main()
