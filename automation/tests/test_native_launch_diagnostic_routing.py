"""Protect the narrowly authorized evidence-first native launch diagnosis.

A verified Warcraft crash cannot depend on the headless evidence it prevents.
This is a worker *selection* exception, not a native-success or release-gate
exception. Do not broaden it to arbitrary [agent-ready] tickets.
"""
import unittest
import tempfile
from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock

from automation.warcraftmap_agent.closure import Blocker, Closure
from automation.warcraftmap_agent.worker import Config, finish_merged_issue, publish, select_issue


REVISION = "a" * 40
LAUNCH = "runtime:campaign_launch"
EVIDENCE = "runtime:evidence"


def issue(number, title, *, keys=(), failed=False):
    body = "\n".join(f"Closure blocker: {k}" for k in keys)
    if failed:
        body += "\nNative launch status: failed\n"
    return {"number": number, "title": title, "body": body,
            "createdAt": str(number), "state": "OPEN"}


def closure(*, fresh=True, extra_dependencies=()):
    blockers = {
        LAUNCH: Blocker(LAUNCH, "Native campaign launch", ["still crashes"],
                        ["reports/runtime-acceptance.json"],
                        {EVIDENCE, *extra_dependencies}),
        EVIDENCE: Blocker(EVIDENCE, "Headless evidence missing",
                          ["no same-revision execution"], ["reports/runtime-acceptance.json"]),
    }
    for dependency in extra_dependencies:
        blockers[dependency] = Blocker(dependency, "Unresolved extra prerequisite",
                                      ["not yet repaired"], ["reports/traceability/requirements.json"])
    return Closure(REVISION, fresh, blockers, reports={
        "runtime": {"path": "reports/runtime-acceptance.json", "regenerated": fresh},
        "release": {"path": "reports/release-blocker-audit.json", "regenerated": fresh},
        "traceability": {"path": "reports/traceability/requirements.json", "regenerated": fresh},
    })


class NativeLaunchDiagnosticRoutingTests(unittest.TestCase):
    def setUp(self):
        self.crash = issue(438, "[agent-ready] Investigate native campaign crash",
                           keys=[LAUNCH], failed=True)

    def test_crash_is_actionable_despite_missing_headless_evidence(self):
        gate = closure()
        self.assertTrue(gate.active)
        self.assertNotIn(LAUNCH, gate.actionable)
        self.assertTrue(gate.permits_issue(self.crash))
        self.assertEqual(select_issue([self.crash], {"issues": {}}, 3,
                                      closure=gate)["number"], 438)
        # Routing never marks any audit clean or supplies runtime evidence.
        self.assertIn(EVIDENCE, gate.blockers)
        self.assertTrue(gate.active)

    def test_no_exception_for_unproven_or_wrongly_routed_issues(self):
        gate = closure()
        failures = [
            issue(439, "[agent-ready] Investigate native campaign crash",
                  keys=[LAUNCH], failed=True),
            issue(438, "[agent-ready] Investigate native campaign crash",
                  keys=[LAUNCH], failed=False),
            issue(438, "[planned] Investigate native campaign crash",
                  keys=[LAUNCH], failed=True),
            issue(438, "[needs-design] Investigate native campaign crash",
                  keys=[LAUNCH], failed=True),
            issue(438, "[agent-ready] Investigate native campaign crash",
                  keys=[LAUNCH, EVIDENCE], failed=True),
            issue(438, "[agent-ready] Investigate native campaign crash",
                  keys=[EVIDENCE], failed=True),
        ]
        for bad in failures:
            with self.subTest(title=bad["title"], number=bad["number"],
                              body=bad["body"]):
                # The standard release rules may permit actual evidence repairs,
                # so only test the native-launch key cases here.
                if LAUNCH in bad["body"] and EVIDENCE not in bad["body"]:
                    self.assertFalse(gate.permits_issue(bad))

    def test_other_dependencies_and_stale_checkout_remain_blocking(self):
        self.assertFalse(closure(fresh=False).permits_issue(self.crash))
        self.assertFalse(closure(extra_dependencies=("traceability:dependent",))
                         .permits_issue(self.crash))

    def test_real_client_crash_preempts_independent_evidence_work_only_when_ready(self):
        evidence = issue(200, "[agent-ready] Rebuild headless evidence", keys=[EVIDENCE])
        gate = closure()
        # Oldest-first would pick #200; the independently confirmed native
        # crash is more important, without allowing another Codex process.
        self.assertEqual(select_issue([evidence, self.crash],
                                      {"issues": {}}, 3, closure=gate)["number"], 438)
        # An already published or exhausted crash ticket cannot starve repairs.
        for record in ({"status": "pr_open", "attempts": 1},
                       {"status": "failed", "attempts": 3}):
            with self.subTest(record=record):
                chosen = select_issue([evidence, self.crash],
                                      {"issues": {"438": record}}, 3, closure=gate)
                self.assertEqual(chosen["number"], 200)

    def test_priority_never_allows_unrelated_optional_work(self):
        gate = closure()
        optional = issue(197, "[agent-ready] New optional gameplay content")
        self.assertFalse(gate.permits_issue(optional))
        self.assertEqual(select_issue([optional, self.crash],
                                      {"issues": {}}, 3, closure=gate)["number"], 438)


    def test_native_code_merge_does_not_auto_close_unverified_incident(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state")
            record = {"status": "pr_open", "pr": 555}
            with mock.patch("automation.warcraftmap_agent.worker.run") as run, \
                 mock.patch("automation.warcraftmap_agent.worker.cleanup_merged_issue",
                            return_value=[]) as cleanup:
                finish_merged_issue(config, "438", record)
            self.assertEqual("merged", record["status"])
            self.assertEqual("pending", record["native_validation"])
            run.assert_not_called()
            cleanup.assert_called_once_with(config, 438)

    def test_normal_code_merge_still_closes_completed_issue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state")
            record = {"status": "pr_open", "pr": 556}
            with mock.patch("automation.warcraftmap_agent.worker.run") as run, \
                 mock.patch("automation.warcraftmap_agent.worker.cleanup_merged_issue",
                            return_value=[]):
                finish_merged_issue(config, "434", record)
            self.assertEqual("merged", record["status"])
            self.assertNotIn("native_validation", record)
            run.assert_called_once_with(
                ["gh", "issue", "close", "434", "--reason", "completed"],
                cwd=config.repo_root,
            )

    def test_native_investigation_pr_has_no_github_auto_close_keyword(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state")
            commands = []
            def fake_run(args, **kwargs):
                commands.append(args)
                if args[:3] == ["git", "status", "--porcelain"]:
                    return CompletedProcess(args, 0, " M staged.wurst\n", "")
                if args[:3] == ["gh", "pr", "list"]:
                    return CompletedProcess(args, 0, "", "")
                if args[:3] == ["gh", "pr", "create"]:
                    return CompletedProcess(args, 0, "https://github.com/example/WarCraftMap/pull/999\n", "")
                return CompletedProcess(args, 0, "", "")
            with mock.patch("automation.warcraftmap_agent.worker.run",
                            side_effect=fake_run), \
                 mock.patch("automation.warcraftmap_agent.worker.default_branch",
                            return_value="main"):
                self.assertEqual(999, publish(config, self.crash, root, "agent/issue-438"))
                normal = issue(434, "[agent-ready] Regular repair", keys=[EVIDENCE])
                self.assertEqual(999, publish(config, normal, root, "agent/issue-434"))
            pr_commands = [args for args in commands if args[:3] == ["gh", "pr", "create"]]
            self.assertEqual(2, len(pr_commands))
            native_body = pr_commands[0][pr_commands[0].index("--body") + 1]
            normal_body = pr_commands[1][pr_commands[1].index("--body") + 1]
            self.assertIn("Investigates #438", native_body)
            self.assertNotIn("Closes #438", native_body)
            self.assertIn("Closes #434", normal_body)


if __name__ == "__main__":
    unittest.main()
