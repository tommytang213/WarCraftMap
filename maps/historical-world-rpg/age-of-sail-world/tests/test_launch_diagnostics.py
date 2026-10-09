import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tooling"))
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
import stage_launch_smoke as smoke
import prepare_native_map_diagnostic as native
import wgc_local_adapter as wgc
from independent_mpq import load_reader
from warcraft_campaign import MpqReader, write_mpq


def sha(data):
    return hashlib.sha256(data).hexdigest()


class LaunchIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.identity = {"sourceRevision": "a" * 40, "sourceTreeSha256": "b" * 64}
        nested = self.root / "map.w3x"
        write_mpq(nested, {"(listfile)": b"war3map.lua\n", "war3map.lua": b"fixture"})
        self.campaign = self.root / "internal.w3n"
        write_mpq(self.campaign, {"(listfile)": b"Maps/Test.w3x\nwar3campaign.w3f\n",
                                  "Maps/Test.w3x": nested.read_bytes(), "war3campaign.w3f": b"unaltered"})
        self.digest = sha(self.campaign.read_bytes())

    def result(self, run="37864283150", attempt="1"):
        return {"sourceIdentity": self.identity, "campaignSha256": self.digest,
                "diagnosticId": smoke.build_id(self.identity, self.digest, run, attempt),
                "buildRun": {"id": run, "attempt": attempt}}

    def test_revision_run_attempt_dirty_tree_and_content_distinguish_safe_names(self):
        names = {smoke.build_id(self.identity, self.digest, "100", "1"),
                 smoke.build_id(self.identity, self.digest, "101", "1"),
                 smoke.build_id(self.identity, self.digest, "100", "2"),
                 smoke.build_id(self.identity | {"sourceRevision": "c" * 40}, self.digest, "100", "1"),
                 smoke.build_id(self.identity, self.digest),
                 smoke.build_id(self.identity | {"sourceTreeSha256": "d" * 64}, self.digest),
                 smoke.build_id(self.identity, "e" * 64)}
        self.assertEqual(len(names), 7)
        self.assertEqual(smoke.build_id(self.identity, self.digest), smoke.build_id(self.identity, self.digest))
        for name in names:
            filename = "AgeOfSailWorldCampaign-" + name + ".w3n"
            self.assertRegex(filename, r"^[A-Za-z0-9.-]+$")
            self.assertLess(len(filename), 255)
            self.assertNotIn("LAUNCH-425", name)

    def test_unsafe_or_incomplete_actions_identity_is_rejected(self):
        for run, attempt in (("../100", "1"), ("100", None), (None, "1"), ("0", "1"), ("100", "-1")):
            with self.subTest(run=run, attempt=attempt), self.assertRaises(ValueError):
                smoke.build_id(self.identity, self.digest, run, attempt)

    def test_known_failed_bytes_cannot_be_relabeled_as_new_candidate(self):
        for constant in ("FAILING_SHA256", "PREVIOUS_FAILING_SHA256"):
            with patch.object(smoke, constant, self.digest), self.assertRaisesRegex(ValueError, "repeat the failing"):
                smoke.stage(self.campaign, self.root / "missing-execution", self.root / "rejected", "a" * 40)
        self.assertFalse((self.root / "rejected").exists())

    def test_staging_changes_no_archive_or_nested_map_bytes(self):
        original = self.campaign.read_bytes()
        members = MpqReader(self.campaign).members()
        for run in ("100", "101"):
            output = self.root / run
            result = smoke.publish(self.campaign, output, self.result(run))
            target = output / result["installedCampaignPath"]
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(MpqReader(target).members(), members)
            self.assertEqual(sha(target.read_bytes()), self.digest)
            self.assertEqual(smoke.verify_staged(output, "a" * 40), result)
            for name in ("launch-smoke.json", "SHA256SUMS.txt", "LAUNCH-SMOKE-ONLY.txt"):
                self.assertNotIn("AgeOfSailWorldCampaign.w3n", (output / name).read_text())
            self.assertIn("No player retest is requested", (output / "LAUNCH-SMOKE-ONLY.txt").read_text())
        self.assertEqual(self.campaign.read_bytes(), original)

    def test_post_stage_rejects_mutated_payload_checksum_revision_and_mixed_versions(self):
        for case in ("payload", "checksum", "revision", "extra", "identity"):
            output = self.root / case
            result = smoke.publish(self.campaign, output, self.result())
            if case == "payload": (output / result["installedCampaignPath"]).write_bytes(b"corrupted")
            if case == "checksum": (output / "SHA256SUMS.txt").write_text(self.digest + "  wrong.w3n\n")
            if case == "revision": (output / "SOURCE_REVISION.txt").write_text("c" * 40 + "\n")
            if case == "extra": (output / "Campaigns/old.w3n").write_bytes(b"old")
            if case == "identity":
                result["diagnosticId"] = "LAUNCH-425-LIGHTING-1"
                (output / "launch-smoke.json").write_text(json.dumps(result))
            with self.subTest(case=case), self.assertRaises(ValueError):
                smoke.verify_staged(output, "a" * 40)

    def test_publish_refuses_changed_input_and_existing_output(self):
        changed = self.result() | {"campaignSha256": "0" * 64,
                                  "diagnosticId": smoke.build_id(self.identity, "0" * 64, "37864283150", "1")}
        with self.assertRaisesRegex(ValueError, "changed"):
            smoke.publish(self.campaign, self.root / "new", changed)
        self.assertFalse((self.root / "new").exists())
        smoke.publish(self.campaign, self.root / "new", self.result())
        with self.assertRaisesRegex(ValueError, "empty"):
            smoke.publish(self.campaign, self.root / "new", self.result())


class NativeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.identity = {"sourceRevision": "a" * 40, "sourceTreeSha256": "b" * 64}
        nested = self.root / "original.w3x"
        write_mpq(nested, {"war3map.lua": b"fixture only", "runtime/build-identity.json": json.dumps(self.identity).encode()})
        self.map_bytes = nested.read_bytes()
        self.campaign = self.root / "original.w3n"
        self.entry = {"id": "selector", "packagePath": "Maps/Selector.w3x", "sha256": sha(self.map_bytes)}
        self.make_campaign(self.entry)

    def make_campaign(self, entry):
        write_mpq(self.campaign, {"campaign-manifest.json": json.dumps({"maps": [entry]}).encode(),
                                  "Maps/Selector.w3x": self.map_bytes})

    def prepare(self, **overrides):
        # Unit-test only: exercise the extraction/identity gate using actual MPQ
        # fixtures. Production and the recorded integration run use pinned mpyq.
        def archive(_reader, data):
            path = self.root / "unit-test-reader.mpq"
            path.write_bytes(data)
            return MpqReader(path)
        args = {"campaign": self.campaign, "expected_sha": sha(self.campaign.read_bytes()),
                "reader_path": self.root / "reader.py", "output": self.root / "package",
                "map_path": self.entry["packagePath"]} | overrides
        with patch.object(native, "load_reader"), patch.object(native, "open_archive", side_effect=archive), \
                patch.object(native, "read_member", side_effect=lambda archive, name: archive.read(name)):
            return native.prepare(**args)

    def test_exact_extraction_and_default_unavailable_status(self):
        original = self.campaign.read_bytes()
        result = self.prepare()
        package = self.root / "package"
        self.assertEqual((package / result["mapFile"]).read_bytes(), self.map_bytes)
        self.assertEqual(self.campaign.read_bytes(), original)
        self.assertEqual(result["runnerStatus"], "native_runner_unavailable")
        self.assertEqual(result["map_standalone_native"], "not_run")
        self.assertEqual(result["campaign_native"], "not_run")
        self.assertFalse(result["playerTestRequested"])
        self.assertNotEqual(sha((package / "corrupt-control.w3x").read_bytes()), result["w3xSha256"])
        from independent_mpq import open_archive
        with self.assertRaises(ValueError):
            open_archive(None, b"deliberately not MPQ")
        with self.assertRaises(ValueError):
            MpqReader(package / "corrupt-control.w3x")

    def test_bad_w3n_manifest_and_build_receipt_fail_before_output(self):
        with self.assertRaisesRegex(ValueError, "W3N SHA"):
            self.prepare(expected_sha="0" * 64)
        self.make_campaign(self.entry | {"sha256": "0" * 64})
        with self.assertRaisesRegex(ValueError, "manifest hash"):
            self.prepare()
        self.make_campaign(self.entry)
        evidence = self.root / "evidence.json"
        evidence.write_text(json.dumps({"campaignSha256": "0" * 64, "sourceIdentity": self.identity}))
        with self.assertRaisesRegex(ValueError, "build evidence"):
            self.prepare(build_evidence=evidence)
        self.assertFalse((self.root / "package").exists())

    def test_unpinned_reader_code_is_not_imported(self):
        source = self.root / "unreviewed.py"
        source.write_text("raise RuntimeError('must never execute')")
        with self.assertRaisesRegex(ValueError, "reviewed pin"):
            load_reader(source)

    def test_default_cli_never_launches_even_with_approval_argument(self):
        with patch.object(sys, "argv", ["adapter", "--approval", "missing.json"]), \
                patch.object(wgc, "execute") as execute, patch("builtins.print") as output:
            wgc.main()
        execute.assert_not_called()
        self.assertEqual(json.loads(output.call_args.args[0])["map_standalone_native"], "not_run")

    def test_review_gate_and_context_controls_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "owner-approved"):
            wgc.approve({"ownerApproved": True})
        self.prepare()
        context = {"positiveSha256": "a" * 64, "clientBuild": "3.0.0.24268"}
        package = self.root / "package"
        manifest = json.loads((package / "diagnostic.json").read_text())
        for case, milestone, digest in (("positive", "gameplay_frames", "a" * 64),
                                        ("negative", "load_rejected", manifest["negativeControl"]["sha256"])):
            (package / f"{case}-result.json").write_text(json.dumps({"context": context,
                "observedMilestone": milestone, "w3xSha256": digest, "nativeAttempt": True,
                "logEvents": {"openingMap": 1}, "loadfileSemantics": "confirmed_in_this_control_context"}))
        wgc.qualify(package, context)
        with self.assertRaisesRegex(ValueError, "qualification"):
            wgc.qualify(package, context | {"clientBuild": "3.0.1.24342"})
        p = package / "positive-result.json"
        row = json.loads(p.read_text()); row["observedMilestone"] = "process_started"; p.write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError, "qualification"):
            wgc.qualify(package, context)

    def test_approved_bundle_rejects_unreviewed_dependencies_and_changed_executable(self):
        bundle = self.root / "reviewed"
        bundle.mkdir()
        for name in ("wgc-launch.lua", "lua.exe"):
            (bundle / name).write_bytes(b"inert test fixture; never executed")
        exe = self.root / "client.exe"; exe.write_bytes(b"test exe")
        control = self.root / "control.w3x"; control.write_bytes(b"test map")
        config = {"format": "wgc_local_approval_v1", "ownerApproved": True, "upstreamVersion": "1.1",
                  "review": {"source": True, "dependencies": True, "license": True},
                  "clientBuild": "3.0.0.24268", "bundle": str(bundle),
                  "files": {p.name: sha(p.read_bytes()) for p in bundle.iterdir()},
                  "lua": "lua.exe", "script": "wgc-launch.lua", "gameRoot": str(self.root),
                  "gameExe": str(exe), "gameExeSha256": sha(exe.read_bytes()), "allowGameRootScratch": True,
                  "reviewedWriteScope": "session_and_game_root_map-wgc-test_only",
                  "reviewedLoadfileMode": "reforged_absolute",
                  "positiveControl": {"path": str(control), "sha256": sha(control.read_bytes()),
                    "knownWorkingClientBuild": "3.0.0.24268", "scriptLanguage": "Lua", "provenance": "unit test only"}}
        self.assertEqual(wgc.approve(config)["gamespeed"], 1)
        extra = bundle / "unreviewed-dependency.lua"; extra.write_bytes(b"unreviewed")
        with self.assertRaisesRegex(ValueError, "complete"):
            wgc.approve(config)
        extra.unlink()
        exe.write_bytes(b"different game build")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            wgc.approve(config)

    def test_launch_command_uses_same_slots_1x_and_explicit_map_executable(self):
        argv = wgc.command({"lua": "lua.exe", "script": "wgc-launch.lua"}, Path("approved"),
                           Path("game"), Path("game/client.exe"), Path("map.w3x"), Path("launch.wgc"))
        self.assertEqual(argv[argv.index("--gamespeed") + 1], "1")
        self.assertEqual(argv[argv.index("--map") + 1], "map.w3x")
        self.assertEqual(argv[argv.index("--gameexe") + 1], "game/client.exe")
        self.assertIn("--reforged", argv)
        self.assertIn("-E", argv)
        for slot in wgc.SLOTS: self.assertIn(slot, argv)

    def test_log_sanitization_excludes_old_other_map_and_personal_lines(self):
        old = b"Played C:/private/selector.w3x\n"
        new = old + b"Account secret\nOpening map - C:/Users/private/selector.w3x\nPlayed Maps/selector.w3x\nPlayed Maps/other.w3x\n"
        result = wgc.log_events(old, new, "selector.w3x")
        self.assertEqual(result, {"openingMap": 1, "playedLoaderEntry": 1})
        self.assertNotIn("private", json.dumps(result))
        self.assertNotIn("passed", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
