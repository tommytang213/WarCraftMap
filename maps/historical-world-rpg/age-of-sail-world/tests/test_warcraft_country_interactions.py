import json
from dataclasses import replace
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "tooling"))
from package_wurst_map import generate, load_config, _load_country_interaction_runtime_data, PackagingError  # noqa: E402


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
        authored = [conflict for path in sorted((ROOT / "scenario/politics").glob("*-1450.json"))
                    for conflict in json.loads(path.read_text()).get("activeConflicts", [])]
        expected = [{key: row[key] for key in ("id", "attackerPolityIds", "defenderPolityIds")}
                    for row in authored]
        self.assertEqual(expected, state["conflicts"])
        self.assertNotIn("setActiveConflict(", source)
        for row in expected:
            for side, key in ((1, "attackerPolityIds"), (2, "defenderPolityIds")):
                for polity in row[key]:
                    self.assertEqual(1, source.count(
                        f'registerConflictMember("{row["id"]}", "{polity}", {side})'))
        self.assertIn("configureGeneratedConflicts(runtime)", source)
        self.assertEqual(sum(len(row["rewards"]) for row in state["polities"]),
                         source.count("runtime.registerRewardProfile("))
        self.assertIn('registerConflictMember("hundred_years_war", "england", 1)', source)
        self.assertIn('registerConflictMember("hundred_years_war", "france", 2)', source)

    def test_discovery_and_peace_are_persistent_authority_not_generated_knowledge(self):
        source, _ = self.generate()
        runtime = (ROOT / "wurst/PlayableCountryInteractions.wurst").read_text()
        # Generation must not disclose all governments merely because their
        # authoritative state was loaded.
        self.assertNotIn("runtime.discover(", source)
        self.assertIn("military.activeConflictBetween(identity.allegianceId(), polityId)", runtime)
        self.assertIn("peaceAuthority.commitPeace(offerConflicts[i], offerTerms[i])", runtime)
        self.assertIn('if p < 0 or not known[p]', runtime)

    def load_conflicts(self, conflicts):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        project = Path(temporary.name)
        politics = project / "scenario/politics"
        politics.mkdir(parents=True)
        (politics / "conflicts.json").write_text(json.dumps({"activeConflicts": conflicts}))
        (project / "package.json").write_text(json.dumps({
            "scenario": {"politics": ["scenario/politics/conflicts.json"]},
        }))
        config = replace(load_config(ROOT / "package.json"), project=project)
        world = {"polities": [{"id": p} for p in ("a", "b", "c")]}
        return _load_country_interaction_runtime_data(config, world)["conflicts"]

    def test_duplicate_registration_sources_merge_only_identical_conflicts(self):
        row = {"id": "war", "attackerPolityIds": ["a", "b"], "defenderPolityIds": ["c"]}
        self.assertEqual([row], self.load_conflicts([row, row]))
        with self.assertRaisesRegex(PackagingError, "conflicting definitions"):
            self.load_conflicts([row, dict(row, attackerPolityIds=["a"])])

    def test_invalid_or_unknown_sides_fail_generation_instead_of_losing_wars(self):
        for attackers, defenders in (([], ["b"]), (["a"], []), (["a"], ["a"]),
                                     (["a", "a"], ["b"]), (["a"], ["unknown"])):
            with self.subTest(attackers=attackers, defenders=defenders):
                with self.assertRaisesRegex(PackagingError, "invalid conflict membership"):
                    self.load_conflicts([{"id": "war", "attackerPolityIds": attackers,
                                          "defenderPolityIds": defenders}])


if __name__ == "__main__":
    unittest.main()
