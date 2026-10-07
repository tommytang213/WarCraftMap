import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_shared" / "engine"))
import native_save_regression as regression  # noqa: E402


class NativeSaveRegressionTests(unittest.TestCase):
    def test_repeated_load_reconstructs_authority_indexes_and_handles(self):
        result = regression.run_headless_cycle(2, "fleet:sample_fleet")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["authoritativeDigestBefore"], result["authoritativeDigestAfter"])
        self.assertEqual([2, 3], result["runtimeGenerations"])
        self.assertTrue(result["transientHandlesRecreated"])
        self.assertEqual(["fleet:sample_fleet", "settlement:sample_port"], result["runtimeIndex"]["representedIds"])
        self.assertEqual(1, result["runtimeIndex"]["modalFrameCount"])

    def test_safe_and_unsafe_native_save_decisions(self):
        self.assertEqual("created", regression.save_decision(None))
        for transaction in regression.UNSAFE_TRANSACTIONS:
            self.assertEqual("deferred", regression.save_decision(transaction))

    def test_representation_loss_must_target_an_existing_runtime_entity(self):
        for entity_id in ("missing_fleet", "official:governor"):
            with self.subTest(entity_id=entity_id):
                with self.assertRaisesRegex(ValueError, "unknown represented entity"):
                    regression.run_headless_cycle(2, entity_id)

    def test_unconfigured_runtime_is_an_explicit_successful_skip(self):
        environment = os.environ.copy()
        environment.pop("WC3_NATIVE_SAVE_RUNNER", None)
        completed = subprocess.run(
            [sys.executable, str(PROJECT / "tooling/run_native_save_regression.py")],
            capture_output=True, text=True, env=environment, check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual("skip", result["status"])
        self.assertEqual("runtime_unavailable", result["kind"])
        self.assertTrue(result["oracle"]["passed"])

    def test_configured_runner_protocol_passes_and_compares_oracle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "fixture.w3x"
            map_path.write_bytes(b"fixture")
            runner = root / "runner.py"
            runner.write_text(textwrap.dedent("""
                import argparse, json
                parser = argparse.ArgumentParser()
                parser.add_argument('--request')
                parser.add_argument('--result')
                args = parser.parse_args()
                request = json.load(open(args.request, encoding='utf-8'))
                expected = request['expected']
                result = {
                    'authoritativeDigestBefore': expected['authoritativeDigestBefore'],
                    'authoritativeDigestAfter': expected['authoritativeDigestAfter'],
                    'runtimeIndex': expected['runtimeIndex'],
                    'transientHandlesRecreated': True,
                    'eventDeliveryCount': 1,
                    'loads': request['loads'],
                }
                json.dump(result, open(args.result, 'w', encoding='utf-8'))
            """), encoding="utf-8")
            environment = os.environ.copy()
            environment["WC3_NATIVE_SAVE_RUNNER"] = f"{sys.executable} {runner}"
            completed = subprocess.run(
                [sys.executable, str(PROJECT / "tooling/run_native_save_regression.py"), "--map", str(map_path)],
                capture_output=True, text=True, env=environment, check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual("passed", json.loads(completed.stdout)["status"])

    def test_wurst_fixture_is_structural_and_not_release_activated(self):
        fixture = (PROJECT / "wurst/NativeSaveRegressionFixture.wurst").read_text(encoding="utf-8")
        boundary = (PROJECT / "wurst/WC3Compatibility.wurst").read_text(encoding="utf-8")
        bootstrap = (PROJECT / "wurst/Bootstrap.wurst").read_text(encoding="utf-8")
        self.assertIn("nativeSaveRegressionStart", fixture)
        self.assertIn("nativeSaveRegressionAfterLoad", fixture)
        self.assertIn("nativeSaveRegressionRequestDuring", fixture)
        self.assertIn("discardTransientRuntime", fixture)
        self.assertIn("compatCreateOwnedTimer", boundary)
        self.assertNotIn("NativeSaveRegressionFixture", bootstrap)


if __name__ == "__main__":
    unittest.main()
