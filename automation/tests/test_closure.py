"""Controller closure policy tests; GitHub mutations and Codex are mocked."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from automation.warcraftmap_agent.closure import Blocker, build_closure, marked_keys
from automation.warcraftmap_agent import worker

A, B = "a" * 40, "b" * 40
KEY = "traceability:REQ-0002.01"
OTHER = "traceability:REQ-0003.01"
DEPENDENT = "traceability:DEP-save-travel"
ROADMAP = "## Phase 8 — Integration\n- [x] done\n## Phase 9 — Release\n- [ ] launch\n"
RELEASE = {"number": 397, "title": "[planned] Phase 9: Release and launch", "body": "", "createdAt": "1"}
BODY = "## Acceptance criteria\n- Repair the production path.\n## Automated validation\n- Run the relevant audit and integration tests."


def bundle(revision=A, findings=()):
    reports = {
        "release": {"status": "pass", "candidateReady": True, "sourceRevision": revision,
                    "taxonomy": [{"id": "campaign_blocker", "releaseBlocking": True},
                                 {"id": "minor", "releaseBlocking": False}],
                    "findings": [], "unresolvedCampaignBlockers": 0},
        "runtime": {"status": "pass", "candidateReady": True, "sourceRevision": revision,
                    "systems": [], "failures": []},
        "traceability": {"status": "fail" if findings else "pass", "candidateReady": not findings,
                         "requirements": [{"id": key, "text": "Implement " + key} for key in findings],
                         "dependencies": [], "blockerCount": len(findings),
                         "blockers": [{"id": key, "class": "integration-missing", "message": "production entry not executed"} for key in findings]},
    }
    return {"revision": revision, "regenerated": True,
            "reports": {name: {"report": report, "recorded": copy.deepcopy(report)} for name, report in reports.items()}}


def issue(number=410, keys=(KEY,), state="OPEN", revision=A, prefix="agent-ready"):
    return {"number": number, "title": f"[{prefix}] Repair production path {number}",
            "body": "\n".join([*(f"Closure blocker: {key}" for key in keys), f"Closure revision: {revision}"]),
            "state": state, "createdAt": str(number), "url": f"https://example/issues/{number}"}


def plan(keys=(KEY,), kind="agent-ready", **kwargs):
    return {"outcome": "planned", "summary": "Repair closure", "issues": [
        {"kind": kind, "title": "Repair integrated production behavior", "body": BODY,
         "question": "Which rule should apply?" if kind == "needs-design" else "",
         "blocker_keys": list(keys), **kwargs}]}


class ClosureTests(unittest.TestCase):
    def test_confirmed_438_crash_investigation_bypasses_only_headless_routing_dependency(self):
        closure = self.closure(findings=())
        closure.blockers["runtime:evidence"] = Blocker("runtime:evidence", "Execute headless coverage")
        launch = Blocker("runtime:campaign_launch", "Investigate launch", dependencies={"runtime:evidence"})
        closure.blockers[launch.key] = launch
        repair = issue(438, keys=(launch.key,))
        repair["body"] += "\nNative launch status: failed\n"
        self.assertTrue(closure.permits_issue(repair))
        self.assertEqual(worker.select_issue([repair], {"issues": {}}, 3, closure=closure), repair)
        self.assertTrue(closure.active)
        self.assertEqual(launch.dependencies, {"runtime:evidence"})
        self.assertNotIn(launch.key, closure.actionable)
        self.assertFalse(closure.permits_issue(RELEASE))
        for change in ({"number": 439}, {"title": "[planned] Launch"},
                       {"body": repair["body"].replace("failed", "passed")},
                       {"body": repair["body"] + "\nClosure blocker: runtime:trade"}):
            with self.subTest(change=change):
                self.assertFalse(closure.permits_issue(repair | change))
        launch.dependencies.add(KEY)
        closure.blockers[KEY] = Blocker(KEY, "Another required repair")
        self.assertFalse(closure.permits_issue(repair))

    def test_confirmed_438_crash_exemption_requires_current_regenerated_checkout(self):
        repair = issue(438, keys=("runtime:campaign_launch",))
        repair["body"] += "\nNative launch status: failed\n"
        unregenerated = bundle() | {"regenerated": False}
        for reason, data, revision, current in (
            ("stale checkout", bundle(), A, False),
            ("stale revision", bundle(), B, True),
            ("missing regeneration", unregenerated, A, True),
        ):
            with self.subTest(reason=reason):
                closure = build_closure(data, revision, issues=[repair], checkout_current=current)
                launch = Blocker("runtime:campaign_launch", "Investigate launch",
                                 dependencies={"runtime:evidence"})
                closure.blockers[launch.key] = launch
                closure.blockers["runtime:evidence"] = Blocker("runtime:evidence", "Execute headless coverage")
                self.assertFalse(closure.fresh)
                self.assertFalse(closure.permits_issue(repair))
                self.assertIsNone(worker.select_issue([repair], {"issues": {}}, 3, closure=closure))
                self.assertEqual(launch.dependencies, {"runtime:evidence"})
                self.assertTrue(closure.active)

    def closure(self, findings=("REQ-0002.01",), **kwargs):
        return build_closure(bundle(findings=findings), A, **kwargs)

    def test_traceability_findings_preempt_older_roadmap_issues(self):
        optional = issue(1, keys=())
        repair = issue()
        closure = self.closure(issues=[optional, repair])
        selected = worker.select_issue([optional, repair], {"issues": {}}, 3, closure=closure)
        self.assertEqual(selected, repair)
        self.assertEqual(worker.select_issue([optional], {"issues": {}}, 3, closure=closure), None)

    def test_exhausted_rejected_for_findings_stale_reports_and_open_repairs(self):
        for closure in (self.closure(), build_closure(bundle(A), B), self.closure(findings=(), issues=[issue()])):
            with self.subTest(closure=closure), self.assertRaisesRegex(ValueError, "exhausted"):
                worker.prepare_plan_items({"outcome": "exhausted"}, [], 10, closure=closure)
        self.assertEqual(worker.prepare_plan_items({"outcome": "exhausted"}, [], 10,
                                                   closure=self.closure(findings=())), [])

    def test_optional_expansion_and_unknown_keys_rejected_during_closure(self):
        for keys in ((), ("traceability:unknown",)):
            with self.subTest(keys=keys), self.assertRaisesRegex(ValueError, "actionable blockers"):
                worker.prepare_plan_items(plan(keys), [], 10, closure=self.closure())

    def test_repair_has_stable_markers_revision_and_post_merge_validation(self):
        items = worker.prepare_plan_items(plan(), [], 10, closure=self.closure())
        self.assertEqual(marked_keys(items[0]), {KEY})
        self.assertIn("Closure revision: " + A, items[0]["body"])
        self.assertIn("After merge, regenerate", items[0]["body"])
        self.assertIn("reports/traceability/requirements.json", items[0]["body"])

    def test_repeated_symptoms_for_obligation_are_one_repair(self):
        data = bundle(findings=["REQ-0002.01"])
        report = data["reports"]["traceability"]["report"]
        report["blockers"].append({"id": "REQ-0002.01", "class": "unpersisted", "message": "save path missing"})
        report["blockerCount"] += 1
        closure = build_closure(data, A)
        self.assertEqual(closure.actionable, [KEY])
        self.assertEqual(len(closure.blockers[KEY].messages), 2)

    def test_runtime_and_release_aliases_deduplicate(self):
        data = bundle()
        release = data["reports"]["release"]["report"]
        release.update(status="fail", candidateReady=False, unresolvedCampaignBlockers=1,
                       findings=[{"id": "RUNTIME-MISSING-TRADE", "severity": "campaign_blocker",
                                  "disposition": "unresolved", "message": "trade is not integrated"}])
        runtime = data["reports"]["runtime"]["report"]
        runtime.update(status="fail", candidateReady=False,
                       systems=[{"id": "trade", "releaseRequired": True, "stages": {}}])
        closure = build_closure(data, A)
        self.assertEqual(closure.actionable, ["runtime:trade"])
        self.assertEqual(len(closure.blockers["runtime:trade"].reports), 2)

    def test_missing_execution_is_a_prerequisite_to_domain_validation(self):
        data = bundle()
        runtime = data["reports"]["runtime"]["report"]
        runtime.update(status="fail", candidateReady=False, executionStatus="not_run",
                       failures=["production execution missing"], systems=[{
                           "id": "trade", "releaseRequired": True, "stages": {},
                           "sourceChecks": {"dataComplete": True, "runtimeIntegrated": True, "playerFacingComplete": True}}])
        closure = build_closure(data, A)
        self.assertEqual(closure.actionable, ["runtime:evidence"])
        runtime["systems"][0]["sourceChecks"]["runtimeIntegrated"] = False
        self.assertEqual(build_closure(data, A).actionable, ["runtime:trade"])

    def test_package_census_waits_for_final_artifact(self):
        data = bundle(findings=["artifact", "catalogues", "REQ-0002.01"])
        closure = build_closure(data, A)
        self.assertIn("traceability:artifact", closure.actionable)
        self.assertIn(KEY, closure.actionable)
        self.assertNotIn("traceability:catalogues", closure.actionable)

    def test_missing_malformed_and_stale_reports_fail_closed(self):
        for data in ({}, [], {"revision": A, "regenerated": True, "reports": []},
                     {"revision": A, "regenerated": True, "reports": {"release": None}}, bundle(B)):
            with self.subTest(data=data):
                closure = build_closure(data, A)
                self.assertTrue(closure.active)
                self.assertIn("audit:traceability", closure.blockers)
        data = bundle()
        data["reports"]["traceability"]["report"] = {"status": "pass"}
        self.assertTrue(build_closure(data, A).active)
        data = bundle()
        data["reports"]["runtime"]["report"]["sourceRevision"] = B
        self.assertIn("audit:runtime", build_closure(data, A).blockers)
        self.assertTrue(build_closure(bundle(), A, checkout_current=False).active)

    def test_saved_pass_flags_cannot_replace_regeneration(self):
        data = bundle()
        data["regenerated"] = False
        self.assertTrue(build_closure(data, A).active)

    def test_audit_crash_retains_known_findings_and_independent_repairs(self):
        data = bundle(findings=["REQ-0002.01"])
        data["reports"]["traceability"]["error"] = "audit crashed"
        closure = build_closure(data, A)
        self.assertIn(KEY, closure.actionable)
        self.assertIn("audit:traceability", closure.actionable)

    def test_failed_regeneration_does_not_repeat_closed_repair_from_stale_findings(self):
        data = bundle(B, ["REQ-0002.01"])
        data["reports"]["traceability"]["error"] = "audit crashed"
        closure = build_closure(data, B, [issue(state="CLOSED", revision=A)])
        self.assertNotIn(KEY, closure.actionable)
        self.assertIn("audit:traceability", closure.actionable)
        self.assertTrue(closure.active)

    def test_open_issue_or_pr_suppresses_renamed_duplicate(self):
        for issues, prs in (([issue()], []), ([], [issue()]),
                            ([issue(state="CLOSED")], [dict(issue(keys=()), closingIssuesReferences=[{"number": 410}])])):
            with self.subTest(issues=issues, prs=prs):
                closure = self.closure(issues=issues, prs=prs)
                self.assertEqual(closure.actionable, [])
                self.assertTrue(closure.active)

    def test_legacy_stable_id_references_are_deduplicated(self):
        legacy = issue(keys=())
        legacy["body"] = "Repair REQ-0002.01 and its production entry."
        self.assertEqual(self.closure(issues=[legacy]).actionable, [])
        self.assertEqual(self.closure(prs=[legacy]).actionable, [])

    def test_closed_work_needs_new_main_audit_before_followup(self):
        repaired = issue(state="CLOSED")
        self.assertEqual(self.closure(issues=[repaired]).actionable, [])
        stale = build_closure(bundle(A, ["REQ-0002.01"]), B, [repaired])
        self.assertNotIn(KEY, stale.actionable)
        fresh = build_closure(bundle(B, ["REQ-0002.01"]), B, [repaired])
        self.assertIn(KEY, fresh.actionable)
        followup = issue(411, revision=B)
        self.assertNotIn(KEY, build_closure(bundle(B, ["REQ-0002.01"]), B, [repaired, followup]).actionable)

    def test_merge_only_closes_blocker_after_fresh_clean_audit(self):
        repaired = issue(state="CLOSED")
        merged = issue(412, state="MERGED")
        stale = build_closure(bundle(A), B, [repaired], [merged])
        self.assertTrue(stale.active)
        still_failing = build_closure(bundle(B, ["REQ-0002.01"]), B, [repaired], [merged])
        self.assertTrue(still_failing.active)
        clean = build_closure(bundle(B), B, [repaired], [merged])
        self.assertFalse(clean.active)
        self.assertEqual(worker.eligible_planned_issues([RELEASE], ROADMAP, {}, clean), [RELEASE])

    def test_launch_397_stays_planned_for_findings_stale_evidence_or_open_repair(self):
        for closure in (self.closure(), build_closure(bundle(), B), self.closure(findings=(), issues=[issue()])):
            with self.subTest(closure=closure):
                self.assertEqual(worker.eligible_planned_issues([RELEASE], ROADMAP, {}, closure), [])
                with mock.patch.object(worker, "run") as mutation:
                    self.assertEqual(worker.promote_planned_issues(worker.Config(Path("/repo"), Path("/state")), closure=closure), [])
                    mutation.assert_not_called()
        self.assertEqual(worker.eligible_planned_issues([RELEASE], ROADMAP, {}), [])

    def test_planned_launch_citations_do_not_claim_prerequisite_repairs(self):
        launch = dict(RELEASE, body="Launch after REQ-0002.01 has executed production evidence.")
        closure = self.closure(issues=[launch])
        self.assertIn(KEY, closure.actionable)
        self.assertEqual(closure.open_repairs, [])
        self.assertEqual(worker.eligible_planned_issues([launch], ROADMAP, {}, closure), [])
        clean = self.closure(findings=(), issues=[launch])
        self.assertEqual(worker.eligible_planned_issues([launch], ROADMAP, {}, clean), [launch])
        # Deferring an explicitly marked repair never exempts it from closure.
        deferred = self.closure(findings=(), issues=[issue(prefix="planned")])
        self.assertTrue(deferred.active)

    def test_dependency_repairs_precede_dependent_validation(self):
        data = bundle(findings=["REQ-0002.01", "DEP-save-travel"])
        report = data["reports"]["traceability"]["report"]
        report["requirements"] = report["requirements"][:1]
        report["dependencies"] = [{"id": "DEP-save-travel", "requirements": ["REQ-0002.01"], "interaction": "save then travel"}]
        parent, child = issue(), issue(411, keys=(DEPENDENT,))
        child["body"] += "\nValidation depends on production repair REQ-0002.01."
        closure = build_closure(data, A)
        self.assertEqual(closure.actionable, [KEY])
        self.assertEqual(worker.select_issue([child, parent], {"issues": {}}, 3, closure=closure), parent)
        with self.assertRaisesRegex(ValueError, "actionable"):
            worker.prepare_plan_items(plan((DEPENDENT,)), [], 10, closure=closure)
        # Closing the parent's issue is insufficient while its finding remains.
        parent["state"] = "CLOSED"
        closure = build_closure(data, A, [parent])
        self.assertFalse(closure.permits_issue(child))
        report["blockers"] = report["blockers"][1:]
        report["blockerCount"] = 1
        self.assertEqual(build_closure(data, A, [parent]).actionable, [DEPENDENT])

    def test_explicit_issue_dependencies_hold_even_when_audit_prerequisite_clears(self):
        child = issue(411)
        child["body"] += "\nDepends on: #410"
        closure = self.closure(issues=[issue(410, keys=(OTHER,)), child])
        self.assertIsNone(worker.select_issue([child], {"issues": {}}, 3, closure=closure))
        closure = self.closure(issues=[issue(410, keys=(OTHER,), state="CLOSED"), child])
        self.assertEqual(worker.select_issue([child], {"issues": {}}, 3, closure=closure), child)

    def test_audit_dependencies_wait_for_open_prerequisite_repairs(self):
        data = bundle(B, ["DEP-save-travel"])
        data["reports"]["traceability"]["report"]["requirements"] = [{
            "id": "REQ-0002.01", "text": "Production path", "status": "pass"}]
        data["reports"]["traceability"]["report"]["dependencies"] = [{
            "id": "DEP-save-travel", "requirements": ["REQ-0002.01"], "interaction": "save then travel"}]
        parent, child = issue(), issue(411, keys=(DEPENDENT,))
        # A clean audit alone does not finish outstanding repair work, including
        # a PR whose linked issue has already been closed.
        for issues, prs in (([parent], []), ([issue(state="CLOSED")], [
                dict(issue(412, keys=()), closingIssuesReferences=[{"number": 410}])])):
            with self.subTest(issues=issues, prs=prs):
                closure = build_closure(data, B, issues, prs)
                self.assertNotIn(DEPENDENT, closure.actionable)
                self.assertFalse(closure.permits_issue(child))
        closure = build_closure(data, B, [issue(state="CLOSED")], [issue(412, state="MERGED")])
        self.assertIn(DEPENDENT, closure.actionable)
        self.assertTrue(closure.permits_issue(child))

    def test_duplicate_blocker_in_one_plan_is_created_once(self):
        response = plan()
        response["issues"] += plan(title="Another title for the same repair")["issues"]
        items = worker.prepare_plan_items(response, [], 10, closure=self.closure())
        self.assertEqual(len(items), 1)

    def test_duplicate_title_does_not_hide_a_valid_followup_in_the_same_plan(self):
        response = plan()
        response["issues"] += plan(title="Follow up on still failing integration evidence")["issues"]
        items = worker.prepare_plan_items(response, [response["issues"][0]["title"]], 10, closure=self.closure())
        self.assertEqual(len(items), 1)
        self.assertIn("Follow up", items[0]["title"])

    def test_design_decision_holds_only_dependent_repairs(self):
        design = issue(prefix="needs-design")
        closure = self.closure(findings=["REQ-0002.01", "REQ-0003.01"], issues=[design])
        self.assertEqual(closure.actionable, [OTHER])
        self.assertEqual(worker.select_issue([design, issue(411, keys=(OTHER,))], {"issues": {}}, 3,
                                            {410}, closure=closure)["number"], 411)
        new_plan = plan(kind="needs-design")
        new_plan["issues"] += plan((OTHER,), title="Independent save repair",
                                   body="Independent of the open rule decision.\n" + BODY)["issues"]
        items = worker.prepare_plan_items(new_plan, [], 10, closure=self.closure(findings=["REQ-0002.01", "REQ-0003.01"]))
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0]["title"].startswith("[needs-design]"))

    def test_clean_closure_resumes_ordinary_roadmap(self):
        closure = self.closure(findings=())
        optional = issue(keys=())
        self.assertEqual(worker.select_issue([optional], {"issues": {}}, 3, closure=closure), optional)
        self.assertEqual(len(worker.prepare_plan_items(plan(()), [], 10, closure=closure)), 1)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "docs").mkdir()
        (self.root / "docs/ROADMAP.md").write_text(ROADMAP)
        self.config = worker.Config(self.root, self.root / "state")

    def test_complete_history_is_not_limited_to_queue_preview(self):
        first = [issue(n) for n in range(100)]
        with mock.patch.object(worker, "gh_json", side_effect=[first, [*first, issue(999, state="CLOSED")]]) as gh:
            rows = worker.list_history(self.config, "issue")
        self.assertEqual(len(rows), 101)
        self.assertIn("200", gh.call_args.args[1])

    def test_creation_rechecks_stable_ids_in_issue_and_pr_history(self):
        closure = build_closure(bundle(findings=["REQ-0002.01"]), A)
        items = worker.prepare_plan_items(plan(), [], 10, closure=closure)
        for issues, prs in (([issue()], []), ([], [issue()])):
            with self.subTest(issues=issues, prs=prs), \
                 mock.patch.object(worker, "list_history", side_effect=[issues, prs]), \
                 mock.patch.object(worker, "default_branch", return_value="main"), \
                 mock.patch.object(worker, "remote_branch_oid", return_value=A), \
                 mock.patch.object(worker, "run") as mutation:
                self.assertEqual(worker.create_plan_issues(self.config, items, closure), 0)
                mutation.assert_not_called()

    def test_main_advance_rejects_plan_creation_and_release_promotion(self):
        closure = build_closure(bundle(), A)
        with mock.patch.object(worker, "list_history", return_value=[]), \
             mock.patch.object(worker, "default_branch", return_value="main"), \
             mock.patch.object(worker, "remote_branch_oid", return_value=B), \
             mock.patch.object(worker, "list_planned_issues", return_value=[RELEASE]), \
             mock.patch.object(worker, "run") as mutation:
            self.assertEqual(worker.promote_planned_issues(self.config, closure=closure), [])
            with self.assertRaisesRegex(ValueError, "main advanced"):
                worker.create_plan_issues(self.config, [{"title": "new", "body": BODY}], closure)
            mutation.assert_not_called()

    def test_new_repair_issue_racing_promotion_keeps_release_planned(self):
        with mock.patch.object(worker, "list_history", side_effect=[[issue()], []]), \
             mock.patch.object(worker, "default_branch", return_value="main"), \
             mock.patch.object(worker, "remote_branch_oid", return_value=A), \
             mock.patch.object(worker, "list_planned_issues", return_value=[RELEASE]), \
             mock.patch.object(worker, "run") as mutation:
            self.assertEqual(worker.promote_planned_issues(self.config, closure=build_closure(bundle(), A)), [])
            mutation.assert_not_called()

    def test_merge_during_history_refresh_keeps_release_planned(self):
        revision = A

        def history(config, kind):
            nonlocal revision
            if kind == "pr":
                revision = B
            return []

        with mock.patch.object(worker, "list_history", side_effect=history), \
             mock.patch.object(worker, "default_branch", return_value="main"), \
             mock.patch.object(worker, "remote_branch_oid", side_effect=lambda *_: revision), \
             mock.patch.object(worker, "list_planned_issues", return_value=[RELEASE]), \
             mock.patch.object(worker, "run") as mutation:
            self.assertEqual(worker.promote_planned_issues(self.config, closure=build_closure(bundle(), A)), [])
            mutation.assert_not_called()

    def test_each_promotion_requires_current_main_and_closed_repairs(self):
        reservations = [dict(RELEASE, number=396), RELEASE]
        for change in ("merge", "new_repair"):
            revision = A
            repairs = []

            def promote(*args, **kwargs):
                nonlocal revision, repairs
                if change == "merge":
                    revision = B
                else:
                    repairs = [issue()]

            with self.subTest(change=change), \
                 mock.patch.object(worker, "list_history", side_effect=lambda _, kind: repairs if kind == "issue" else []), \
                 mock.patch.object(worker, "default_branch", return_value="main"), \
                 mock.patch.object(worker, "remote_branch_oid", side_effect=lambda *_: revision), \
                 mock.patch.object(worker, "list_planned_issues", return_value=reservations), \
                 mock.patch.object(worker, "run", side_effect=promote) as mutation:
                self.assertEqual(worker.promote_planned_issues(self.config, closure=build_closure(bundle(), A)), reservations[:1])
                mutation.assert_called_once()
                self.assertEqual(mutation.call_args.args[0][3], "396")

    def test_pr_service_skips_optional_expansion_during_closure(self):
        state = {"issues": {"10": {"status": "pr_open", "pr": 20}}}
        with mock.patch.object(worker, "gh_json") as gh, mock.patch.object(worker, "run") as mutation:
            self.assertFalse(worker.service_open_prs(self.config, state, allowed_issues={410}))
            gh.assert_not_called()
            mutation.assert_not_called()

    def test_pr_service_obeys_issue_dependencies_and_design_decisions(self):
        design = issue(410, keys=(OTHER,), prefix="needs-design")
        dependent = issue(411)
        dependent["body"] += "\nDepends on: #410"
        missing = issue(412)
        missing["body"] += "\nBlocked by: #999"
        independent = issue(413, keys=("traceability:REQ-0004.01",))
        closure = build_closure(bundle(findings=["REQ-0002.01", "REQ-0003.01", "REQ-0004.01"]),
                                A, [design, dependent, missing, independent])
        context = {"issues": closure.issues, "pull_requests": [], "closure": closure}
        with mock.patch.object(worker, "make_config", return_value=self.config), \
             mock.patch.object(worker, "planning_context", return_value=context), \
             mock.patch.object(worker, "service_open_prs", return_value=True) as service:
            self.assertEqual(worker.main([]), 0)
        self.assertEqual(service.call_args.args[2], {413})

    def test_issue_body_file_preserves_newlines_and_literal_shell_text(self):
        item = {"title": "[agent-ready] A repair", "body": BODY + "\nLiteral `code` and $(text).", "question": ""}
        def create(args, **kwargs):
            self.assertEqual(args[:3], ["gh", "issue", "create"])
            self.assertEqual(Path(args[args.index("--body-file") + 1]).read_text(), item["body"])
            return mock.Mock(stdout="https://example/issues/411\n")
        with mock.patch.object(worker, "list_history", return_value=[]), mock.patch.object(worker, "run", side_effect=create):
            self.assertEqual(worker.create_plan_issues(self.config, [item]), 1)

    def run_controller(self, closure, response, *, dry_run=False, state=None):
        context = {"issues": closure.issues, "pull_requests": closure.prs, "closure": closure}
        output = io.StringIO()
        with mock.patch.object(worker, "make_config", return_value=self.config), \
             mock.patch.object(worker, "planning_context", return_value=context), \
             mock.patch.object(worker, "refresh_validation_repair_bases"), \
             mock.patch.object(worker, "service_open_prs", return_value=False), \
             mock.patch.object(worker, "load_state", return_value=state or {"version": 2, "runs": [], "issues": {}}), \
             mock.patch.object(worker, "invoke_planner", return_value=response) as planner, \
             mock.patch.object(worker, "create_plan_issues", return_value=1) as create, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.assertEqual(worker.main(["--dry-run"] if dry_run else []), 0)
        return planner, create, output.getvalue()

    def test_healthy_optional_queue_does_not_bypass_blocker_planning(self):
        optional = [issue(n, keys=()) for n in range(1, 12)]
        closure = build_closure(bundle(findings=["REQ-0002.01"]), A, optional)
        planner, create, _ = self.run_controller(closure, plan())
        planner.assert_called_once()
        create.assert_called_once()
        self.assertEqual(marked_keys(create.call_args.args[1][0]), {KEY})

    def test_cached_design_exhaustion_does_not_skip_new_blocker(self):
        design = issue(100, keys=(), prefix="needs-design")
        closure = build_closure(bundle(findings=["REQ-0002.01"]), A, [design])
        state = {"version": 2, "runs": [], "issues": {}, "planning_exhausted_for_blockers": [100]}
        planner, _, _ = self.run_controller(closure, plan(), state=state)
        planner.assert_called_once()
        self.assertNotIn("planning_exhausted_for_blockers", state)

    def test_controller_rejects_exhausted_without_creating_or_caching(self):
        closure = build_closure(bundle(findings=["REQ-0002.01"]), A)
        _, create, output = self.run_controller(closure, {"outcome": "exhausted", "issues": []})
        create.assert_not_called()
        state = json.loads((self.config.state_dir / "state.json").read_text())
        self.assertNotIn("planning_exhausted_for_blockers", state)
        self.assertIn("exhausted is forbidden", output)

    def test_exhaustion_rechecks_audits_after_planning(self):
        clean = build_closure(bundle(), A)
        dirty = build_closure(bundle(findings=["REQ-0002.01"]), A)
        contexts = [{"issues": [], "pull_requests": [], "closure": closure} for closure in (clean, dirty)]
        output = io.StringIO()
        with mock.patch.object(worker, "make_config", return_value=self.config), \
             mock.patch.object(worker, "planning_context", side_effect=contexts) as audits, \
             mock.patch.object(worker, "promote_planned_issues", return_value=[]), \
             mock.patch.object(worker, "refresh_validation_repair_bases"), \
             mock.patch.object(worker, "service_open_prs", return_value=False), \
             mock.patch.object(worker, "invoke_planner", return_value={"outcome": "exhausted", "issues": []}), \
             mock.patch.object(worker, "create_plan_issues") as create, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.assertEqual(worker.main([]), 0)
        self.assertEqual(audits.call_count, 2)
        create.assert_not_called()
        self.assertIn("exhausted cannot be accepted", output.getvalue())
        self.assertNotIn("planning_exhausted_for_blockers", json.loads((self.config.state_dir / "state.json").read_text()))

    def test_dry_run_selects_blocker_before_optional_queue(self):
        closure = build_closure(bundle(findings=["REQ-0002.01"]), A, [issue(1, keys=()), issue()])
        planner, create, output = self.run_controller(closure, plan(), dry_run=True)
        planner.assert_not_called()
        create.assert_not_called()
        self.assertIn("next task: #410", output)

    def test_all_blockers_owned_never_refills_with_optional_work(self):
        repair = issue(prefix="needs-design")
        closure = build_closure(bundle(findings=["REQ-0002.01"]), A, [repair, issue(1, keys=())])
        planner, create, output = self.run_controller(closure, plan(()))
        planner.assert_not_called()
        create.assert_not_called()
        self.assertIn("release closure pending", output)

    def test_read_closure_regenerates_on_main_and_detects_merge_during_audit(self):
        def command(args, **kwargs):
            if "planning_audit.py" in " ".join(args):
                return mock.Mock(stdout=json.dumps(bundle()))
            return mock.Mock(stdout=A if args[1] == "rev-parse" else "")
        for revisions, expected in (([A, A], False), ([A, B], True)):
            with self.subTest(revisions=revisions), \
                 mock.patch.object(worker, "default_branch", return_value="main"), \
                 mock.patch.object(worker, "remote_branch_oid", side_effect=revisions), \
                 mock.patch.object(worker, "run", side_effect=command) as invoked:
                closure = worker.read_closure(self.config, [], [])
                self.assertEqual(closure.active, expected)
                self.assertTrue(any("planning_audit.py" in " ".join(call.args[0]) for call in invoked.call_args_list))


if __name__ == "__main__":
    unittest.main()
