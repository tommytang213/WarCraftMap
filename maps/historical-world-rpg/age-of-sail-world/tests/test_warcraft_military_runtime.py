import sys
import tempfile
import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "tooling"))

from package_wurst_map import generate, load_config  # noqa: E402


class WarcraftMilitaryRuntimeGenerationTests(unittest.TestCase):
    def test_authoritative_military_state_is_emitted_into_warcraft_bootstrap(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            generate(load_config(ROOT / "package.json"), output)
            source = (output / "ScenarioData.wurst").read_text(encoding="utf-8")
            runtime = (output / "scenario-runtime.json").read_text(encoding="utf-8")
            self.assertIn("import MilitarySettlementRuntime", source)
            self.assertIn("configureMilitarySettlementScenario", source)
            self.assertIn('RuntimeForce("english_guard_formation"', source)
            self.assertIn('RuntimeForce("english_patrol_ship"', source)
            for domain in (
                '"militaryRuntimeTemplates"',
                '"strategicUnits"',
                '"armies"',
                '"fleets"',
                '"defenseLayouts"',
            ):
                self.assertIn(domain, runtime)

    def test_every_authored_settlement_has_one_generated_runtime_state_at_a_real_location(self):
        integration = json.loads((ROOT / "scenario/integration/release-scale-settlements.json").read_text())
        expected = {row["settlementId"] for row in integration["settlements"]}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            generate(load_config(ROOT / "package.json"), output)
            runtime = json.loads((output / "scenario-runtime.json").read_text())
            states = runtime["settlementRuntimeStates"]
            self.assertEqual(expected, {row["id"] for row in states})
            self.assertEqual(len(expected), len(states))
            self.assertTrue(states)
            self.assertTrue(all(row["regionId"] and (row["x"] != 0 or row["y"] != 0) for row in states))
            generated = (output / "ScenarioData.wurst").read_text()
            self.assertEqual(len(states), generated.count("runtime.registerSettlement("))
            self.assertEqual(len(states), generated.count("runtime.appoint("))

    def test_native_runtime_suite_covers_required_warcraft_scenarios(self):
        source = (ROOT / "wurst" / "MilitarySettlementRuntimeTests.wurst").read_text(encoding="utf-8")
        for marker in (
            "recruitmentLossReinforcementAndTraditionReachRuntimeUnits",
            "legalCaptureRebuildsLayoutAndEnforcesExactFiveSecondImmunity",
            "garrisonWavesConsumePersistentFiniteResourcesAndDespawnQuietly",
            "governorReplacementWarnsAndNeverImpliesPhysicalClone",
            "inactiveRegionContinuesAbstractlyAndReconstructsFromAuthority",
            "captureStateSurvivesMapRetirementAndReconstruction",
            "snapshotRestorePreservesMidWarFleetOrdersSiegeAndAdministration",
            "changedControlImmunityAndRepeatedReconstructionNeverDuplicateAuthority",
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
