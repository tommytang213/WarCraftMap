import copy
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
sys.path.insert(0, str(PROJECT / "tooling"))
import wurst_execution as execution
import package_release_candidate as release
import package_wurst_map as maps
from wurst_execution_fixture import FAKE_EXECUTION, allow_synthetic_compiler, passing_evidence


class WurstExecutionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "wurst").mkdir()
        (self.root / "wurst/Fixture.wurst").write_text(
            'package Fixture\n// @test function ignored()\n'
            '/* @test function ignoredToo() */\n'
            '@test function actual()\n\ttrue.assertTrue()\n'
            '@test\nfunction second()\n\ttrue.assertTrue()\n')
        self.fake = self.root / "grill"
        # The protocol fake uses a simple regex; remove ignored declarations
        # in its input scan. Production discovery is tested independently.
        protocol = FAKE_EXECUTION.replace('text = path.read_text()',
            'text = re.sub(r"//[^\\n]*|/\\*.*?\\*/", lambda m: " " * len(m[0]), path.read_text())')
        self.fake.write_text('#!/usr/bin/env python3\nimport os, pathlib, sys\nroot=pathlib.Path.cwd()\n'
                             'print("JAVA_TOOL_OPTIONS=" + os.environ.get("JAVA_TOOL_OPTIONS", ""))\n' + protocol)
        self.fake.chmod(0o755)
        allow_synthetic_compiler(self, self.fake)

    def run_suite(self, mode="pass"):
        with patch.dict(os.environ, {"FAKE_WURST_RESULT": mode}):
            return execution.execute_tests(self.root, str(self.fake), self.root / "evidence", "a" * 40)

    def test_required_suite_discovers_production_startup_regressions(self):
        discovered = {row["id"].split(":")[1] for row in execution.discover(PROJECT)
                      if row["id"].startswith("wurst/CampaignStartupTests.wurst:")}
        self.assertIn("selectorCommitFailureAllowsAnotherChoiceAndNeverLoads", discovered)
        self.assertIn("selectorToAsianRegionUsesPhysicalStartingCoordinates", discovered)
        self.assertIn("interruptedAcknowledgementRestoresBoundCheckpointWithoutReinitializing", discovered)
        self.assertIn("populatedTransferRestoresAfterProductionRegistrationAndPreservesEveryDomain", discovered)
        self.assertIn("transferFromAbstractOriginUsesDestinationArrivalWithoutCityObject", discovered)
        self.assertIn("checksumValidTransferWithUnknownOriginCannotActivateOrOverwrite", discovered)

    def test_required_suite_discovers_cross_domain_load_transactions(self):
        discovered = {row["id"].split(":")[1] for row in execution.discover(PROJECT)}
        self.assertTrue({
            "checksummedLateReligionAndDiplomacyRejectBeforeAnyMutation",
            "countryOfferBindingsValidateAgainstCandidateConflictsInBothDomains",
            "failedLoadRetainsSettledConflictsBoundOffersAndActiveSieges",
            "legacyMilitaryMigrationSupportsFoundedPolityReconciliation",
            "invalidTradeAndPirateTerritoriesAreStagedWithoutLiveCallbacks",
            "lateExtensionFailureRestoresEveryAuthorityAndProjection",
            "latePartyFailureRestoresProjectionsAndRetryCommitsExactlyOnce",
            "stagedLoadAbortRetainsClockAndTimerUntilCommit",
            "reportedOrdinaryPolityFailureRollsBackItsOwnMutations",
            "rejectedLoadRestoresInactiveMilitaryProjectionTarget",
            "rejectedLoadRetainsEquipmentContributionsOnSurvivingObjects",
            "boundStartupProjectionFailureRollsBackAllDomainsAndRetries",
            "boundStartupSessionFailureRollsBackBeforePublication",
            "boundStartupMilestoneFailureRollsBackBeforePublication",
            "boundStartupAcknowledgementFailureRollsBackAndRetainsHandoff",
        }.issubset(discovered))

    def test_required_suite_discovers_party_locations_and_every_migration_batch(self):
        discovered = {row["id"].split(":")[1] for row in execution.discover(PROJECT)}
        self.assertTrue({
            "legacyTransferSchemasOneAndTwoResolveGeneratedBoundary",
            "legacyTransferSchemasThreeAndFourResolveGeneratedBoundary",
            "transferSchemasFiveThroughSevenResolveGeneratedBoundary",
            "coordinateLessSchemasOneAndTwoUseDeterministicFallback",
            "coordinateLessSchemasThreeAndFourUseDeterministicFallback",
            "coordinateLessSchemasFiveAndSixUseDeterministicFallback",
            "currentPartyCoordinatesSurviveManualAutosaveAndRecoveryLoads",
            "ordinaryDestinationMovementDoesNotReplayTransferArrival",
            "lostRepresentationsRetainCommittedPositionsAndRemoteCompanionsStayAbstract",
            "failedPartyReconstructionRetainsMovedMembersAuthorityAndStoredSaves",
            "malformedAndBlockedPartyLocationsRejectWithoutRelocatingAuthority",
            "transferDoesNotMaterializeAbstractCompanionAssignedToDestination",
        }.issubset(discovered))

    def test_required_suite_discovers_production_pirate_founding_and_load_regressions(self):
        discovered = {row["id"].split(":")[1] for row in execution.discover(PROJECT)}
        self.assertTrue({
            "registeredFoundingRejectsUnqualifiedCaptainsAndGovernmentTerritory",
            "registeredFoundingRejectsMalformedListsAndLateTerritoryFailures",
            "registeredFoundingCannotConvertOccupationIntoLegalOwnership",
            "registeredFoundingCommitsOrdinaryTerritoryAndReconstructionIsIdempotent",
            "foundedPolityLoadsPreserveCapturesCessionsAllegianceAndResources",
            "legacyPiracyHistoryMigratesWithoutGrantingDisputedTitle",
            "failedLoadRetainsFoundedPolityLossesAndLegacyMigrationIsAtomic",
        }.issubset(discovered))

    def test_discovery_and_complete_results_bind_compiler_revision_and_inputs(self):
        report = self.run_suite()
        self.assertEqual(["wurst/Fixture.wurst:actual", "wurst/Fixture.wurst:second"],
                         [test["id"] for test in report["expected"]])
        self.assertEqual((2, 2), (report["discovered"], report["succeeded"]))
        execution.verify_evidence(report, (self.root / "evidence/execution.log").read_bytes(), "a" * 40)
        self.assertIn("wurst/Fixture.wurst", report["inputs"])

    def test_execution_and_packaging_receive_heap_without_mutating_caller_environment(self):
        probe = self.root / "java_environment.py"
        probe.write_text('import os, pathlib\npathlib.Path("java-options.txt").write_text('
                         'os.environ.get("JAVA_TOOL_OPTIONS", ""))\n')
        for options in (None, "-Dfile.encoding=UTF-8", "-Xmx8g -Dfile.encoding=UTF-8"):
            with self.subTest(options=options), patch.dict(os.environ):
                if options is None:
                    os.environ.pop("JAVA_TOOL_OPTIONS", None)
                else:
                    os.environ["JAVA_TOOL_OPTIONS"] = options
                before = dict(os.environ)
                expected = "-Xmx6g" + (" " + options if options else "")
                self.run_suite()
                log = (self.root / "evidence/execution.log").read_text()
                self.assertIn("JAVA_TOOL_OPTIONS=" + expected + "\n", log)
                # Map and campaign compilation share this subprocess boundary.
                maps._run("heap probe", [sys.executable, str(probe)], self.root)
                self.assertEqual(expected, (self.root / "java-options.txt").read_text())
                self.assertEqual(before, dict(os.environ))

    def test_assertion_exception_absence_truncation_incomplete_and_zero_fail_closed(self):
        for mode in ("assertion", "exception", "timeout", "absent", "truncated", "incomplete", "zero"):
            with self.subTest(mode=mode), redirect_stderr(io.StringIO()), self.assertRaises(execution.WurstExecutionError):
                self.run_suite(mode)
            report = json.loads((self.root / "evidence/results.json").read_text())
            self.assertEqual("fail", report["status"])

    def test_failed_execution_emits_retained_transcript_for_disposable_ci_builds(self):
        for mode in ("assertion", "exception", "timeout", "truncated", "incomplete"):
            diagnostic = io.StringIO()
            with self.subTest(mode=mode), redirect_stderr(diagnostic):
                with self.assertRaises(execution.WurstExecutionError):
                    self.run_suite(mode)
            log = (self.root / "evidence/execution.log").read_text()
            self.assertEqual(log, diagnostic.getvalue())
            self.assertIn("actual..", diagnostic.getvalue())
            self.assertEqual("fail", json.loads((self.root / "evidence/results.json").read_text())["status"])

    def test_successful_execution_does_not_replay_transcript(self):
        diagnostic = io.StringIO()
        with redirect_stderr(diagnostic):
            self.run_suite()
        self.assertEqual("", diagnostic.getvalue())

    def test_missing_executable_and_empty_discovery_write_failed_evidence(self):
        for executable in (str(self.root / "missing-grill"), str(self.fake)):
            with self.subTest(executable=executable), redirect_stderr(io.StringIO()), self.assertRaises(execution.WurstExecutionError):
                execution.execute_tests(self.root, executable, self.root / "evidence", "a" * 40)
            self.assertEqual("fail", json.loads((self.root / "evidence/results.json").read_text())["status"])
            (self.root / "wurst/Fixture.wurst").write_text("package NoTests\n")

    def test_exit_code_and_compiler_identity_override_a_successful_transcript(self):
        for mode in ("returncode", "compiler"):
            with self.subTest(mode=mode), redirect_stderr(io.StringIO()):
                report = self.run_suite()
                log = (self.root / "evidence/execution.log").read_text()
                if mode == "returncode":
                    from subprocess import CompletedProcess
                    with patch.object(execution.subprocess, "run", return_value=CompletedProcess([], 1, log)):
                        with self.assertRaisesRegex(execution.WurstExecutionError, "exited 1"):
                            self.run_suite()
                else:
                    with patch.object(execution, "PINNED_COMPILER_SHA256", "0" * 64):
                        with self.assertRaisesRegex(execution.WurstExecutionError, "pinned toolchain"):
                            self.run_suite()

    def test_missing_duplicate_unexpected_or_misreported_results_are_rejected(self):
        report, log = passing_evidence()
        for transcript in (
            log.replace(b"OK!", b""), log.replace(b"1/1", b"0/0"),
            log.replace(b" - fixture..", b" - unlisted.."),
            log.replace(b":2 -", b":3 -"),
            log.replace(b"Tests succeeded", b"Running /test/wurst/Fixture.wurst:2 - fixture..\nOK!\nTests succeeded"),
            log + b"NullPointerException\n", log + b"Finished running tests\n",
        ):
            with self.subTest(transcript=transcript):
                _, issues = execution.parse_results(transcript.decode(), report["expected"])
                self.assertTrue(issues)

    def test_saved_pass_cannot_hide_failed_missing_or_stale_execution(self):
        original, log = passing_evidence()
        for key, value in (("sourceRevision", "b" * 40), ("tests", []),
                           ("expected", []), ("returnCode", 1), ("succeeded", 0),
                           ("compiler", {}), ("logSha256", "0" * 64), ("inputs", {})):
            report = copy.deepcopy(original)
            report[key] = value
            with self.subTest(key=key), self.assertRaises(execution.WurstExecutionError):
                execution.verify_evidence(report, log, "a" * 40)


class ReleaseExecutionGateTests(unittest.TestCase):
    def setUp(self):
        # Reuse the real scenario fixture and an otherwise successful packager.
        from test_packaging import PackagingTests
        PackagingTests.setUp(self)

    def test_each_execution_failure_stops_map_and_release_artifact_creation(self):
        for mode in ("assertion", "exception", "timeout", "absent", "truncated", "incomplete", "zero"):
            with self.subTest(mode=mode), redirect_stderr(io.StringIO()), patch.dict(os.environ, {"FAKE_WURST_RESULT": mode}):
                with self.assertRaisesRegex(maps.PackagingError, "Wurst execution"):
                    maps.build(self.project / "package.json", grill=str(self.fake))
                commands = (self.project / "_build/commands.txt").read_text().splitlines()
                self.assertIn("typecheck", commands)
                self.assertNotIn("build map/AgeOfSailWorld.w3x", commands)
                # Real campaign execution gate remains in the RC call chain;
                # expensive unrelated release audits are already covered elsewhere.
                with patch.object(release, "PROJECT", self.project), \
                     patch.object(release, "validate_gates", return_value=({}, {}, {}, [])), \
                     patch.object(release, "_write_zip") as package:
                    with self.assertRaisesRegex(maps.PackagingError, "Wurst execution"):
                        release.build_release_candidate(grill=str(self.fake), revision="a" * 40)
                    package.assert_not_called()
                self.assertFalse((self.project / "_build/release/AgeOfSailWorld-phase9-rc1.zip").exists())

    def test_absent_tool_blocks_release_before_packaging(self):
        with patch.object(release, "PROJECT", self.project), \
             patch.object(release, "validate_gates", return_value=({}, {}, {}, [])), \
             patch.object(release, "_write_zip") as package:
            with self.assertRaises((OSError, maps.PackagingError)):
                release.build_release_candidate(grill=str(self.project / "absent-grill"), revision="a" * 40)
            package.assert_not_called()
