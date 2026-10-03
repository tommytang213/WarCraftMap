import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "tooling"))
from package_wurst_map import generate, load_config  # noqa: E402


class WarcraftCountryInteractionGenerationTests(unittest.TestCase):
    def generate(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        generate(load_config(ROOT / "package.json"), output)
        return ((output / "ScenarioData.wurst").read_text(),
                json.loads((output / "scenario-runtime.json").read_text()))

    def test_live_economy_rewards_and_conflicts_are_generated(self):
        source, runtime = self.generate()
        state = runtime["countryInteractionState"]
        self.assertEqual(len(runtime["polityDefinitions"]), len(state["polities"]))
        self.assertTrue(any(row["treasury"] > 0 for row in state["polities"]))
        self.assertTrue(all(row["rewards"] for row in state["polities"]))
        self.assertTrue(state["conflicts"])
        self.assertEqual(sum(len(row["rewards"]) for row in state["polities"]),
                         source.count("runtime.registerRewardProfile("))
        self.assertIn('setActiveConflict("england", "hundred_years_war")', source)
        self.assertIn('setActiveConflict("france", "hundred_years_war")', source)

    def test_discovery_and_peace_are_persistent_authority_not_generated_knowledge(self):
        source, _ = self.generate()
        runtime = (ROOT / "wurst/PlayableCountryInteractions.wurst").read_text()
        # Generation must not disclose all governments merely because their
        # authoritative state was loaded.
        self.assertNotIn("runtime.discover(", source)
        self.assertIn('result += "|c,"', runtime)
        self.assertIn("if conflictIds[c] == settledConflict", runtime)
        self.assertIn('if p < 0 or not known[p]', runtime)


if __name__ == "__main__":
    unittest.main()
