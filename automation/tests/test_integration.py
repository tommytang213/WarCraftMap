"""Bounded staging with real Git histories and mocked GitHub/Codex boundaries."""
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from automation.warcraftmap_agent import integration, worker
from automation.warcraftmap_agent.closure import Closure


RUNTIME = "maps/historical-world-rpg/_shared/wurst/PlayableCampaignRuntime.wurst"
CONTROLLER = "automation/warcraftmap_agent/budget.py"


def issue(number):
    return {"number": number, "title": "[agent-ready] Unrelated title proves nothing",
            "body": "", "state": "OPEN", "createdAt": f"2026-01-{number % 20 + 1:02d}",
            "url": f"https://example.invalid/issues/{number}"}


class OverlapTests(unittest.TestCase):
    def test_shared_runtime_bootstrap_save_and_evidence_are_high_risk(self):
        for path in (RUNTIME, "maps/historical-world-rpg/_shared/wurst-bootstrap/Bootstrap.wurst",
                     "maps/historical-world-rpg/_shared/engine/save.py",
                     "maps/historical-world-rpg/age-of-sail-world/scenario/traceability/mappings.json",
                     "maps/historical-world-rpg/age-of-sail-world/reports/traceability/requirements.json",
                     "maps/historical-world-rpg/age-of-sail-world/reports/traceability/requirements.md"):
            with self.subTest(path=path):
                decision = integration.classify([path], [path.upper()])
                self.assertFalse(decision["independent"])
                self.assertEqual(decision["overlaps"], [path.casefold()])
                self.assertFalse(integration.classify([path], [RUNTIME])["independent"])

    def test_only_known_disjoint_boundaries_authorize_separate_ci(self):
        self.assertTrue(integration.classify([CONTROLLER], [RUNTIME])["independent"])
        for files in (None, [], ["unknown.py"], ["../outside"], ["/absolute"],
                      ["automation/run_checks.sh"], [".github/workflows/map-build.yml"],
                      ["automation/warcraftmap_agent/worker.py"],
                      ["automation/warcraftmap_agent/closure.py"],
                      [RUNTIME, CONTROLLER]):
            self.assertFalse(integration.classify(files, [RUNTIME])["independent"])

    def test_failed_or_design_blocked_stage_keeps_its_slot(self):
        for status in ("working", "repair", "failed", "needs_design", "waiting_dependency", "staged"):
            state = {"issues": {"427": {"stage": {"worktree": "preserved"}, "status": status,
                                        "attempts": 3}}}
            self.assertEqual(integration.staged_numbers(state), [427])
            self.assertIsNone(worker.select_issue([issue(428)], state, 3))


class LocalStagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.upstream = self.root / "upstream"
        self.worktree = self.root / "worktree"
        self.git(self.root, "init", "-b", "main", str(self.upstream))
        self.configure(self.upstream)
        self.write(self.upstream, RUNTIME, "\n".join(f"line {n}" for n in range(15)) + "\n")
        self.write(self.upstream, CONTROLLER, "# controller\n")
        self.initial_base = self.commit(self.upstream)
        self.git(self.root, "clone", str(self.upstream), str(self.worktree))
        self.configure(self.worktree)
        self.git(self.worktree, "checkout", "-b", "agent/issue-427")
        self.config = worker.Config(self.worktree, self.root / "state")
        self.state_path = self.config.state_dir / "state.json"
        self.issues = [issue(427)]
        self.history = []
        self.views = {}
        self.file_pages = {}
        self.action = self.implement_runtime
        self.launch_records = []
        self.checks = mock.Mock()
        self.scoped = mock.Mock()
        self.publish = mock.Mock(return_value=501)
        self.invoke = mock.Mock(side_effect=self.codex)
        patches = self.enterContext(ExitStack())
        for name, value in {
            "default_branch": mock.Mock(return_value="main"),
            "make_config": mock.Mock(return_value=self.config),
            "promote_planned_issues": mock.Mock(return_value=[]),
            "list_history": mock.Mock(side_effect=lambda config, kind: self.issues if kind == "issue" else self.history),
            "read_closure": mock.Mock(side_effect=lambda *args: Closure(self.git(self.upstream, "rev-parse", "HEAD"), True, {})),
            "gh_json": mock.Mock(side_effect=self.github),
            "service_open_prs": mock.Mock(return_value=False),
            "queue_refill_count": mock.Mock(return_value=0),
            "worktree_for": mock.Mock(return_value=(self.worktree, "agent/issue-427")),
            "invoke_codex": self.invoke, "run_checks": self.checks,
            "run_scoped_checks": self.scoped, "publish": self.publish,
            "emit_pr_metrics": mock.Mock(),
        }.items():
            patches.enter_context(mock.patch.object(worker, name, value))

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True).stdout.strip()

    def configure(self, repo):
        for key, value in {"user.name": "Fixture", "user.email": "fixture@example.invalid",
                           "commit.gpgsign": "false"}.items():
            self.git(repo, "config", key, value)

    def write(self, repo, relative, text):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, repo):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-m", "Local fixture changes")
        return self.git(repo, "rev-parse", "HEAD")

    def state(self):
        return worker.load_state(self.state_path)

    def record(self):
        return self.state()["issues"]["427"]

    def tick(self):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(worker.main([]), 0)
        return self.record()

    def codex(self, config, worktree, selected, record, run_entry):
        self.assertEqual(fcntl.fcntl(worker.lock_fds()[0], fcntl.F_GETFL) & os.O_ACCMODE, os.O_RDONLY)
        saved = self.state()
        self.assertEqual(saved["issues"]["427"], record)
        self.assertEqual(saved["runs"][-1], run_entry)
        self.assertEqual(integration.staged_numbers(saved), [427])
        self.launch_records.append(json.loads(json.dumps(record)))
        self.action()
        run_entry.update(tokens=42, telemetry="reported", completed_at=integration.stamp())
        return {"outcome": "complete"}

    def implement_runtime(self):
        path = self.worktree / RUNTIME
        path.write_text(path.read_text().replace("line 14", "candidate implementation"))

    def predecessor(self, *, files=None, number=500, state="OPEN", ci="pending"):
        files = files or [RUNTIME]
        row = {"number": number, "state": state, "headRefName": f"agent/issue-{number - 1}"}
        self.history.append(row)
        self.views[number] = {**row, "changedFiles": len(files), "headRefOid": "b" * 40,
                              "baseRefName": "main", "mergedAt": None, "mergeCommit": None,
                              "statusCheckRollup": [{"status": "IN_PROGRESS"} if ci == "pending" else
                                                    {"conclusion": "FAILURE" if ci == "failed" else "SUCCESS"}]}
        self.file_pages[number] = [[{"filename": path} for path in files]]

    def github(self, repo, args):
        if args[:2] == ["pr", "view"]:
            return dict(self.views[int(args[2])])
        if args[0] == "api" and "/files?" in args[-1]:
            return self.file_pages[int(args[-1].split("/pulls/")[1].split("/")[0])]
        raise AssertionError(f"Unexpected GitHub request: {args}")

    def merge_predecessor(self, number=500):
        path = self.upstream / RUNTIME
        path.write_text(path.read_text().replace("line 0\n", "merged predecessor\n"))
        base = self.commit(self.upstream)
        self.views[number].update(state="MERGED", mergedAt=integration.stamp(), mergeCommit={"oid": base})
        for row in self.history:
            if row["number"] == number:
                row.update(self.views[number])
        return base

    def test_pending_predecessor_reserves_before_launch_and_never_validates_or_publishes(self):
        self.predecessor()
        record = self.tick()
        self.assertEqual(record["status"], "staged")
        self.assertEqual(self.launch_records[0]["stage"]["predecessors"][0]["files"], [RUNTIME])
        self.assertEqual(self.record()["metrics"]["codex_runs"][self.state()["runs"][0]["id"]]["tokens"], 42)
        self.issues.append(issue(428))
        self.config.max_daily_runs = 1
        self.tick()
        self.assertEqual(self.invoke.call_count, 1)
        self.assertEqual(len(self.state()["runs"]), 1)
        self.checks.assert_not_called()
        self.publish.assert_not_called()
        self.assertIn("candidate implementation", (self.worktree / RUNTIME).read_text())

    def test_green_unmerged_predecessor_still_waits_then_validates_actual_merged_base(self):
        self.predecessor(ci="passed")
        self.assertEqual(self.tick()["status"], "staged")
        self.checks.assert_not_called()
        base = self.merge_predecessor()
        self.config.max_daily_runs = 1
        record = self.tick()
        self.assertEqual(record["status"], "pr_open")
        self.assertEqual(record["validation_receipt"]["base_sha"], base)
        self.assertEqual(record["metrics"]["first_validation_base_sha"], base)
        self.git(self.worktree, "merge-base", "--is-ancestor", base, "HEAD")
        contents = (self.worktree / RUNTIME).read_text()
        self.assertIn("candidate implementation", contents)
        self.assertIn("merged predecessor", contents)
        self.assertEqual(self.invoke.call_count, 1)
        self.scoped.assert_called_once()
        self.checks.assert_called_once()
        self.publish.assert_called_once()

    def test_failed_closed_and_stalled_predecessors_preserve_and_explain_hold(self):
        self.predecessor(ci="failed")
        self.assertIn("failed", self.tick()["stage"]["hold_reason"])
        self.views[500]["state"] = "CLOSED"
        self.history[0]["state"] = "CLOSED"
        self.assertIn("closed without merging", self.tick()["stage"]["hold_reason"])
        state = self.state()
        state["issues"]["427"]["stage"]["created_at"] = "2020-01-01T00:00:00Z"
        worker.save_state(self.state_path, state)
        self.assertIn("attention required", self.tick()["stage"]["hold_reason"])
        self.assertEqual(self.invoke.call_count, 1)
        self.publish.assert_not_called()
        self.merge_predecessor()
        self.assertEqual(self.tick()["status"], "pr_open")

    def test_disjoint_code_uses_independent_ci_with_a_bounded_pr_count(self):
        self.predecessor()
        self.action = lambda: self.write(self.worktree, CONTROLLER, "# independent implementation\n")
        self.assertEqual(self.tick()["status"], "pr_open")
        self.publish.assert_called_once()
        decision = self.record()["metrics"]["overlap_observations"][0]
        self.assertTrue(decision["independent"])

    def test_two_open_prs_prevent_a_third_speculative_full_build(self):
        self.predecessor(number=500)
        self.predecessor(number=502)
        self.action = lambda: self.write(self.worktree, CONTROLLER, "# independent implementation\n")
        self.assertIn("two managed PRs", self.tick()["stage"]["hold_reason"])
        self.checks.assert_not_called()
        self.publish.assert_not_called()

    def test_main_advancing_during_validation_requires_another_full_validation(self):
        def advance(*args):
            self.write(self.upstream, "new-main.txt", "new main\n")
            self.commit(self.upstream)
        self.checks.side_effect = advance
        first = self.tick()
        self.assertEqual(first["status"], "staged")
        self.assertNotIn("validation_receipt", first)
        self.publish.assert_not_called()
        self.checks.side_effect = None
        final = self.tick()
        self.assertEqual(final["status"], "pr_open")
        self.assertNotEqual(first["metrics"]["first_validation_base_sha"], final["validation_receipt"]["base_sha"])
        self.assertEqual(self.invoke.call_count, 1)
        self.assertEqual(self.checks.call_count, 2)
        self.assertEqual(len(final["metrics"]["validations"]), 2)

    def test_overlapping_pr_appearing_during_validation_closes_publication_gate(self):
        self.checks.side_effect = lambda *args: self.predecessor()
        record = self.tick()
        self.assertEqual(record["status"], "staged")
        self.assertIn("shared paths", record["stage"]["hold_reason"])
        self.publish.assert_not_called()
        self.tick()
        self.assertEqual(self.checks.call_count, 1)

    def test_crash_during_validation_restarts_preflight_without_implementation_or_green_reuse(self):
        self.checks.side_effect = SystemExit("simulated crash")
        with self.assertRaises(SystemExit):
            self.tick()
        self.assertEqual(self.record()["status"], "staged")
        self.assertEqual(self.record()["metrics"]["validations"][0]["result"], "running")
        self.checks.side_effect = None
        self.assertEqual(self.tick()["status"], "pr_open")
        self.assertEqual(self.invoke.call_count, 1)
        self.assertEqual(self.checks.call_count, 2)

    def test_crash_after_pr_creation_recovers_remote_claim_without_duplicate_run(self):
        def created(*args, **kwargs):
            self.history.append({"number": 501, "headRefName": "agent/issue-427", "state": "OPEN"})
            raise SystemExit("crash after create")
        self.publish.side_effect = created
        with self.assertRaises(SystemExit):
            self.tick()
        self.assertNotIn("pr", self.record())
        record = self.tick()
        self.assertEqual(record["status"], "pr_open")
        self.assertEqual(record["pr"], 501)
        self.assertEqual(self.invoke.call_count, 1)
        self.assertEqual(self.publish.call_count, 1)

    def test_real_source_conflict_enters_existing_budgeted_repair_lane(self):
        self.predecessor()
        self.action = lambda: self.write(self.worktree, RUNTIME, "candidate source\n")
        self.tick()
        self.merge_predecessor()
        record = self.tick()
        self.assertEqual(record["status"], "repair")
        self.assertEqual(record["repair_kind"], "merge_conflict")
        self.assertEqual(worker.unmerged_paths(self.worktree), [RUNTIME])
        self.checks.assert_not_called()
        self.publish.assert_not_called()
        def resolve():
            self.write(self.worktree, RUNTIME, "candidate source\nmerged predecessor\n")
            self.git(self.worktree, "add", RUNTIME)
        self.action = resolve
        record = self.tick()
        self.assertEqual(record["status"], "pr_open")
        self.assertEqual(record["conflict_attempts"], 1)
        self.assertEqual(record["attempts"], 1)

    def test_conflicting_generated_reports_are_regenerated_from_both_sources(self):
        project = "maps/historical-world-rpg/test"
        report = project + "/reports/traceability/requirements"
        script = project + "/tooling/requirement_traceability_audit.py"
        self.write(self.upstream, project + "/scenario/ours.txt", "base ours")
        self.write(self.upstream, project + "/scenario/theirs.txt", "base theirs")
        generator = '''from pathlib import Path
p = Path(__file__).resolve().parents[1]
value = (p / "scenario/ours.txt").read_text() + "|" + (p / "scenario/theirs.txt").read_text()
for extension in ("json", "md"):
    (p / ("reports/traceability/requirements." + extension)).write_text(value)
'''
        self.write(self.upstream, script, generator)
        for suffix in ("json", "md"):
            self.write(self.upstream, report + "." + suffix, "base ours|base theirs")
        self.commit(self.upstream)
        self.predecessor(files=[report + ".json", report + ".md"])
        def implement():
            self.write(self.worktree, project + "/scenario/ours.txt", "candidate source")
            for suffix in ("json", "md"):
                self.write(self.worktree, report + "." + suffix, "candidate source|base theirs")
        self.action = implement
        self.tick()
        self.write(self.upstream, project + "/scenario/theirs.txt", "merged source")
        for suffix in ("json", "md"):
            self.write(self.upstream, report + "." + suffix, "base ours|merged source")
        base = self.commit(self.upstream)
        self.views[500].update(state="MERGED", mergedAt=integration.stamp(), mergeCommit={"oid": base})
        self.history[0].update(self.views[500])
        record = self.tick()
        self.assertEqual(record["status"], "pr_open")
        for suffix in ("json", "md"):
            self.assertEqual((self.worktree / (report + "." + suffix)).read_text(), "candidate source|merged source")
        self.assertEqual(self.invoke.call_count, 1)
        self.assertEqual(len(record["metrics"]["conflicts"]), 1)
        self.checks.assert_called_once()

    def test_receipt_rejects_changed_code_even_with_passing_previous_validation(self):
        self.tick()
        receipt = self.record()["validation_receipt"]
        worker.assert_validation_receipt(self.config, self.worktree, receipt)
        self.write(self.worktree, RUNTIME, "unvalidated code")
        with self.assertRaisesRegex(RuntimeError, "fresh integration"):
            worker.assert_validation_receipt(self.config, self.worktree, receipt)

    def test_missing_worktree_is_preserved_as_an_explicit_hold(self):
        self.predecessor()
        self.tick()
        self.worktree.rename(self.root / "preserved-worktree")
        # Planning's local Git inspection uses an existing controller checkout.
        self.config.repo_root = self.root / "preserved-worktree"
        self.assertIn("worktree is missing", self.tick()["stage"]["hold_reason"])
        self.assertEqual(self.invoke.call_count, 1)

    def test_complete_file_pagination_renames_and_head_race(self):
        files = [f"automation/tests/test_{n}.py" for n in range(105)]
        self.predecessor(files=files)
        self.file_pages[500] = [self.file_pages[500][0][:100], self.file_pages[500][0][100:]]
        self.file_pages[500][1][-1]["previous_filename"] = RUNTIME
        snapshot = worker.predecessor_snapshot(self.config, {"issues": {}}, self.history, {})[0]
        self.assertEqual(len(snapshot["files"]), 106)
        self.assertIn(RUNTIME, snapshot["files"])
        self.file_pages[500].pop()
        snapshot = worker.predecessor_snapshot(self.config, {"issues": {}}, self.history, {})[0]
        self.assertIsNone(snapshot["files"])
        self.assertIn("incomplete", snapshot["error"])
        view = self.views[500]
        with mock.patch.object(worker, "gh_json", side_effect=[
                {**view, "changedFiles": 1}, [[{"filename": RUNTIME}]], {**view, "headRefOid": "new"}]):
            snapshot = worker.predecessor_snapshot(self.config, {"issues": {}}, self.history, {})[0]
        self.assertIsNone(snapshot["files"])
        self.assertIn("changed while", snapshot["error"])


class RecoveryAndMetricsTests(unittest.TestCase):
    def test_closed_predecessor_does_not_burn_repairs_and_reopening_restores_service(self):
        with tempfile.TemporaryDirectory() as root:
            config = worker.Config(Path(root), Path(root))
            record = {"status": "pr_open", "pr": 500, "attempts": 1}
            state = {"issues": {"427": record}}
            with mock.patch.object(worker, "gh_json", return_value={"state": "CLOSED"}):
                self.assertTrue(worker.service_open_prs(config, state))
            self.assertEqual(record["status"], "pr_closed")
            self.assertIsNone(worker.select_issue([issue(427)], state, 3))
            worker.reconcile_pr_claims(state, [{"number": 500, "headRefName": "agent/issue-427", "state": "OPEN"}])
            self.assertEqual(record["status"], "pr_open")
            self.assertEqual(record["attempts"], 1)

    def test_publication_crash_recovers_even_when_pr_merged_before_restart(self):
        record = {"stage": {"worktree": "preserved"}, "validation_receipt": {"head_sha": "head"}}
        integration.phase(record, "publication")
        state = {"issues": {"427": record}}
        worker.reconcile_pr_claims(state, [{"number": 500, "headRefName": "agent/issue-427",
                                           "headRefOid": "head", "state": "MERGED"}])
        self.assertEqual(record["pr"], 500)
        # The ordinary service path will verify MERGED directly with GitHub.
        self.assertEqual(record["status"], "pr_open")
        self.assertEqual(integration.staged_numbers(state), [])

    def test_metrics_publish_structured_receipt_without_replacing_human_pr_body(self):
        with tempfile.TemporaryDirectory() as root:
            config = worker.Config(Path(root), Path(root))
            record = {"pr": 500, "status": "pr_open"}
            integration.phase(record, "pr_ci")
            state = {"version": 3, "issues": {"427": record}, "runs": []}
            body = "Human description.\n\nCloses #427"
            with mock.patch.object(worker, "collect_ci_metrics"), \
                 mock.patch.object(worker, "gh_json", return_value={"body": body}), \
                 mock.patch.object(worker, "run") as mutation:
                worker.emit_pr_metrics(config, state)
            command = mutation.call_args.args[0]
            self.assertEqual(command[:5], ["gh", "api", "--method", "PATCH", "repos/{owner}/{repo}/pulls/500"])
            updated = json.loads(Path(command[command.index("--input") + 1]).read_text())["body"]
            self.assertTrue(updated.startswith(body))
            payload = json.loads((config.state_dir / "metrics/pr-500.json").read_text())
            self.assertEqual(payload["trial"]["max_staged_depth"], 1)
            self.assertIsNone(payload["ci_run_count"])
            with mock.patch.object(worker, "collect_ci_metrics"), \
                 mock.patch.object(worker, "gh_json", return_value={"body": updated}), \
                 mock.patch.object(worker, "run") as mutation:
                worker.emit_pr_metrics(config, state)
            final_body = json.loads((config.state_dir / "metrics/pr-500.body.json").read_text())["body"]
            self.assertEqual(final_body.count("<!-- warcraftmap-agent-metrics -->"), 1)
            self.assertTrue(final_body.startswith(body))

    def test_duplicate_claims_fail_closed(self):
        state = {"issues": {}}
        history = [{"number": n, "headRefName": "agent/issue-427", "state": "OPEN"} for n in (500, 501)]
        with self.assertRaisesRegex(RuntimeError, "multiple managed PRs"):
            worker.reconcile_pr_claims(state, history)

    def test_v2_state_preserves_attempts_and_unknown_token_charges(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "state.json"
            state = {"version": 2, "issues": {"427": {"attempts": 3}},
                     "runs": [{"timestamp": "2026-01-01T00:00:00Z", "issue": 427, "tokens": None}]}
            worker.save_state(path, state)
            migrated = worker.load_state(path)
            self.assertEqual(migrated["version"], 3)
            self.assertEqual(migrated["runs"], state["runs"])
            self.assertEqual(migrated["issues"], state["issues"])
            integration.record_runs(migrated)
            migrated["runs"] = []
            data = integration.summary(migrated["issues"]["427"])
            self.assertEqual(data["codex_unknown_runs"], 1)
            self.assertEqual(data["codex_run_count"], 1)
            self.assertIsNone(data["ci_run_count"])

    def test_stale_green_checks_cannot_merge_a_changed_head_or_base(self):
        for head, base in (("new-head", "base"), ("head", "new-base")):
            with self.subTest(head=head, base=base), tempfile.TemporaryDirectory() as root:
                config = worker.Config(Path(root), Path(root))
                record = {"status": "pr_open", "pr": 500, "stage": {},
                          "validation_receipt": {"head_sha": "head", "base_sha": "base"}}
                state = {"issues": {"427": record}}
                view = {"state": "OPEN", "headRefOid": head, "baseRefName": "main", "mergeStateStatus": "CLEAN",
                        "statusCheckRollup": [{"conclusion": "SUCCESS"}]}
                with mock.patch.object(worker, "gh_json", return_value=view), \
                     mock.patch.object(worker, "remote_branch_oid", return_value=base), \
                     mock.patch.object(worker, "run") as mutation:
                    self.assertTrue(worker.service_open_prs(config, state))
                mutation.assert_not_called()
                self.assertEqual(record["status"], "staged")
                self.assertIn("fresh integration and CI", record["stage"]["hold_reason"])

    def test_ci_counts_include_attempts_and_do_not_count_polling_as_reruns(self):
        with tempfile.TemporaryDirectory() as root:
            config = worker.Config(Path(root), Path(root))
            record = {"pr": 500}
            latest = {"id": 900, "run_attempt": 2, "head_sha": "head", "status": "completed",
                      "run_started_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:10:00Z",
                      "pull_requests": [{"number": 500}], "conclusion": "success"}
            prior = {**latest, "run_attempt": 1, "updated_at": "2026-01-01T00:05:00Z"}
            with mock.patch.object(worker, "gh_json", side_effect=[[{"total_count": 1, "workflow_runs": [latest]}], prior,
                                                                  [{"total_count": 1, "workflow_runs": [latest]}]]):
                worker.collect_ci_metrics(config, record, "427")
                worker.collect_ci_metrics(config, record, "427")
            data = integration.summary(record)
            self.assertEqual(data["ci_run_count"], 1)
            self.assertEqual(data["ci_reruns"], 1)
            self.assertEqual(data["ci_elapsed_seconds"], 900)

    def test_paginated_json_supports_the_installed_older_github_cli(self):
        response = subprocess.CompletedProcess([], 0, '[{"filename":"a"}]\n[{"filename":"b"}]\n', "")
        with mock.patch.object(worker, "run", return_value=response) as request:
            self.assertEqual(worker.gh_json(Path("."), ["api", "--paginate", "files"]),
                             [[{"filename": "a"}], [{"filename": "b"}]])
        self.assertNotIn("--slurp", request.call_args.args[0])
        response.stdout = '[{"filename":"a"}]\n[{"filename":'
        with mock.patch.object(worker, "run", return_value=response), self.assertRaises(ValueError):
            worker.gh_json(Path("."), ["api", "--paginate", "files"])

    def test_child_retains_controller_lock_after_parent_descriptor_closes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "worker.lock"
            with path.open("w") as held:
                fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with mock.patch.object(worker, "_worker_lock", held):
                    child = subprocess.Popen([sys.executable, "-c", "print('ready', flush=True); input()"],
                        pass_fds=worker.lock_fds(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                    self.assertEqual(child.stdout.readline().strip(), "ready")
            try:
                with path.open("w") as contender:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                child.communicate("done\n", timeout=5)
            with path.open("w") as released:
                fcntl.flock(released, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_stale_global_result_is_never_reused_and_runs_have_distinct_outputs(self):
        with tempfile.TemporaryDirectory() as root:
            config = worker.Config(Path(root), Path(root))
            (Path(root) / "last-codex-result.json").write_text('{"outcome":"complete"}')
            process = mock.Mock(returncode=0)
            process.communicate.return_value = ("", None)
            with mock.patch.object(worker.subprocess, "Popen", return_value=process) as launch:
                for _ in range(2):
                    with self.assertRaisesRegex(RuntimeError, "no structured result"):
                        worker.invoke_codex(config, Path(root), issue(427), {"attempts": 1}, {})
            outputs = [call.args[0][call.args[0].index("--output-last-message") + 1] for call in launch.call_args_list]
            self.assertNotEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
