import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from automation.warcraftmap_agent.worker import (
    Config,
    build_codex_command,
    build_pr_merge_command,
    check_state,
    codex_prompt,
    load_env,
    load_state,
    parse_codex_token_usage,
    create_plan_issues,
    decision_question,
    notify_design_blocker,
    eligible_planned_issues,
    normalized_work_title,
    planned_dependency_numbers,
    prepare_plan_items,
    promote_planned_issues,
    queue_refill_count,
    reconcile_ready_issue_states,
    refresh_validation_repair_bases,
    select_issue,
    service_open_prs,
)


class WorkerTests(unittest.TestCase):
    def test_load_env_does_not_execute_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config"
            path.write_text(
                'WARCRAFTMAP_AGENT_MODEL="small model"\n# comment\n',
                encoding="utf-8",
            )
            self.assertEqual(
                load_env(path)["WARCRAFTMAP_AGENT_MODEL"],
                "small model",
            )

    def test_selects_oldest_eligible_ready_issue(self):
        issues = [
            {
                "number": 2,
                "title": "[agent-ready] second",
                "createdAt": "2026-01-02",
            },
            {
                "number": 1,
                "title": "[agent-ready] first",
                "createdAt": "2026-01-01",
            },
        ]
        state = {
            "issues": {
                "1": {
                    "attempts": 3,
                    "status": "failed",
                }
            }
        }
        self.assertEqual(select_issue(issues, state, 3)["number"], 2)

    def test_planned_issue_is_never_directly_selected(self):
        issues = [{"number": 8, "title": "[planned] Phase 8: release", "createdAt": "2026-01-01"}]
        self.assertIsNone(select_issue(issues, {"issues": {}}, 3))

    def test_resolved_design_issue_reenters_queue(self):
        issues = [{"number": 73, "title": "[agent-ready] resumed", "createdAt": "2026-01-01"}]
        state = {"issues": {"73": {"attempts": 3, "status": "needs_design", "last_failure": "old question"}}}
        reconcile_ready_issue_states(issues, state)
        self.assertEqual(state["issues"]["73"]["status"], "queued")
        self.assertEqual(state["issues"]["73"]["attempts"], 0)
        self.assertNotIn("last_failure", state["issues"]["73"])
        self.assertEqual(select_issue(issues, state, 3)["number"], 73)

    def test_skips_open_pr(self):
        issues = [
            {
                "number": 1,
                "title": "[agent-ready] task",
                "createdAt": "2026-01-01",
            }
        ]
        state = {
            "issues": {
                "1": {
                    "attempts": 1,
                    "status": "pr_open",
                }
            }
        }
        self.assertIsNone(select_issue(issues, state, 3))


    def test_merge_conflict_repair_uses_separate_attempt_budget(self):
        issues = [{"number": 111, "title": "[agent-ready] Africa", "createdAt": "2026-01-01"}]
        state = {
            "issues": {
                "111": {
                    "attempts": 3,
                    "conflict_attempts": 1,
                    "status": "repair",
                    "repair_kind": "merge_conflict",
                    "pr": 119,
                }
            }
        }
        self.assertEqual(select_issue(issues, state, 3)["number"], 111)

    def test_exhausted_validation_repair_revives_when_base_is_recorded_or_advances(self):
        config = Config(
            repo_root=Path("/repo"),
            state_dir=Path("/state"),
            max_validation_repair_attempts=5,
        )
        state = {
            "issues": {
                "221": {
                    "attempts": 3,
                    "validation_repair_attempts": 5,
                    "repair_kind": "validation",
                    "status": "failed",
                    "last_failure": "command failed (1): ./automation/run_checks.sh",
                }
            }
        }
        with mock.patch("automation.warcraftmap_agent.worker.default_branch", return_value="main"), mock.patch(
            "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="new-base"
        ):
            refresh_validation_repair_bases(config, state)
        record = state["issues"]["221"]
        self.assertEqual(record["status"], "repair")
        self.assertEqual(record["validation_repair_attempts"], 0)
        self.assertEqual(record["validation_base_oid"], "new-base")

        record["validation_repair_attempts"] = 5
        record["status"] = "failed"
        with mock.patch("automation.warcraftmap_agent.worker.default_branch", return_value="main"), mock.patch(
            "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="new-base"
        ):
            refresh_validation_repair_bases(config, state)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["validation_repair_attempts"], 5)

        with mock.patch("automation.warcraftmap_agent.worker.default_branch", return_value="main"), mock.patch(
            "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="newer-base"
        ):
            refresh_validation_repair_bases(config, state)
        self.assertEqual(record["status"], "repair")
        self.assertEqual(record["validation_repair_attempts"], 0)
        self.assertEqual(record["validation_base_oid"], "newer-base")

    def test_validation_repair_uses_separate_attempt_budget_after_implementation_exhaustion(self):
        issues = [{"number": 217, "title": "[agent-ready] soak", "createdAt": "2026-01-01"}]
        state = {
            "issues": {
                "217": {
                    "attempts": 3,
                    "status": "failed",
                    "last_failure": "command failed (1): ./automation/run_checks.sh\nFAILED",
                }
            }
        }
        self.assertEqual(
            select_issue(
                issues,
                state,
                3,
                max_validation_repair_attempts=5,
                max_ci_repair_attempts=5,
                max_conflict_attempts=5,
            )["number"],
            217,
        )

    def test_ci_repair_uses_separate_attempt_budget_after_implementation_exhaustion(self):
        issues = [{"number": 207, "title": "[agent-ready] audio", "createdAt": "2026-01-01"}]
        state = {
            "issues": {
                "207": {
                    "attempts": 3,
                    "ci_repair_attempts": 1,
                    "status": "repair",
                    "repair_kind": "ci",
                    "pr": 215,
                }
            }
        }
        self.assertEqual(
            select_issue(
                issues, state, 3, max_ci_repair_attempts=5, max_conflict_attempts=5
            )["number"],
            207,
        )

    def test_legacy_ci_repair_state_recovers_without_manual_attempt_reset(self):
        issues = [{"number": 207, "title": "[agent-ready] audio", "createdAt": "2026-01-01"}]
        state = {
            "issues": {
                "207": {
                    "attempts": 3,
                    "status": "repair",
                    "pr": 215,
                    "last_failure": (
                        "GitHub CI failed on PR #215. Inspect it with gh pr checks 215 "
                        "and repair the implementation."
                    ),
                }
            }
        }
        self.assertEqual(
            select_issue(
                issues, state, 3, max_ci_repair_attempts=5, max_conflict_attempts=5
            )["number"],
            207,
        )

    def test_failed_ci_enters_ci_repair_lane_and_exhaustion_is_terminal(self):
        view = {
            "state": "OPEN",
            "mergeStateStatus": "UNSTABLE",
            "mergeable": "MERGEABLE",
            "baseRefName": "main",
            "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "FAILURE"}],
        }
        config = Config(
            repo_root=Path("/repo"),
            state_dir=Path("/state"),
            max_attempts=3,
            max_ci_repair_attempts=5,
            max_conflict_attempts=5,
        )
        state = {"issues": {"207": {"attempts": 3, "ci_repair_attempts": 4, "status": "pr_open", "pr": 215}}}
        with mock.patch("automation.warcraftmap_agent.worker.gh_json", return_value=view), mock.patch(
            "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="abc123"
        ):
            self.assertTrue(service_open_prs(config, state))
        record = state["issues"]["207"]
        self.assertEqual(record["status"], "repair")
        self.assertEqual(record["repair_kind"], "ci")
        self.assertEqual(record["ci_repair_attempts"], 4)

        record["status"] = "pr_open"
        record["ci_repair_attempts"] = 5
        with mock.patch("automation.warcraftmap_agent.worker.gh_json", return_value=view), mock.patch(
            "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="abc123"
        ):
            self.assertTrue(service_open_prs(config, state))
        self.assertEqual(record["status"], "failed")
        self.assertIn("CI-repair attempt limit (5) is exhausted", record["last_failure"])

    def test_failed_dirty_pr_reenters_conflict_repair(self):
        state = {
            "issues": {
                "111": {
                    "attempts": 3,
                    "status": "failed",
                    "pr": 119,
                    "last_failure": (
                        "PR #119 is unmergeable because main conflicts with the issue branch, "
                        "and the per-issue attempt limit (3) is exhausted."
                    ),
                }
            }
        }
        config = Config(repo_root=Path("/repo"), state_dir=Path("/state"), max_attempts=3)
        view = {"state": "OPEN", "mergeStateStatus": "DIRTY", "statusCheckRollup": []}
        with mock.patch("automation.warcraftmap_agent.worker.gh_json", return_value=view):
            self.assertTrue(service_open_prs(config, state))
        record = state["issues"]["111"]
        self.assertEqual(record["status"], "repair")
        self.assertEqual(record["repair_kind"], "merge_conflict")
        self.assertEqual(record.get("conflict_attempts", 0), 0)

    def test_pr_merge_does_not_delete_branch_checked_out_by_worktree(self):
        command = build_pr_merge_command(17)
        self.assertEqual(command, ["gh", "pr", "merge", "17", "--merge"])
        self.assertNotIn("--delete-branch", command)

    def test_codex_prompt_defers_unavailable_repository_validation_to_outer_worker(self):
        issue = {"number": 131, "title": "[agent-ready] travel", "body": "Implement it."}
        prompt = codex_prompt(issue, "")
        self.assertIn("outer worker performs the authoritative repository validation", prompt)
        self.assertIn('do NOT return "blocked" solely because', prompt)
        self.assertIn("Grill is unavailable", prompt)

    def test_codex_prompt_forbids_mutating_container_bind_mounts(self):
        issue = {"number": 321, "title": "[agent-ready] trade", "body": "Implement it."}
        prompt = codex_prompt(issue, "")
        self.assertIn("Never bind-mount this worktree read/write", prompt)
        self.assertIn("never run chown or chmod against this worktree", prompt)
        self.assertIn("mount the worktree read-only", prompt)
        self.assertIn("container-private temporary storage", prompt)

    def test_codex_command_uses_json_and_no_conflicting_sandbox_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(repo_root=root, state_dir=root / "state")
            command = build_codex_command(
                config,
                root / "worktree",
                root / "schema.json",
                root / "result.json",
            )
        self.assertIn("--approve-for-me", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--json", command)
        self.assertNotIn("--sandbox", command)

    def test_parse_codex_turn_completed_usage(self):
        output = "\n".join(
            [
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 1200,
                            "cached_input_tokens": 500,
                            "output_tokens": 300,
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 2000,
                            "output_tokens": 400,
                        },
                    }
                ),
            ]
        )
        self.assertEqual(parse_codex_token_usage(output), 3900)

    def test_parse_codex_token_count_fallback_uses_cumulative_max(self):
        output = "\n".join(
            [
                json.dumps(
                    {
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "total_token_usage": {
                                    "total_tokens": 1000,
                                }
                            },
                        }
                    }
                ),
                json.dumps(
                    {
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "total_token_usage": {
                                    "total_tokens": 1500,
                                }
                            },
                        }
                    }
                ),
            ]
        )
        self.assertEqual(parse_codex_token_usage(output), 1500)

    def test_parse_missing_telemetry_returns_none(self):
        self.assertIsNone(
            parse_codex_token_usage(
                '{"type":"item.completed","item":{"type":"agent_message"}}'
            )
        )

    def test_v1_state_migrates_to_token_aware_v2(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "invocations": ["2026-09-26T12:00:00Z"],
                        "issues": {"1": {"attempts": 1}},
                    }
                ),
                encoding="utf-8",
            )
            state = load_state(path)
        self.assertEqual(state["version"], 2)
        self.assertEqual(len(state["runs"]), 1)
        self.assertIsNone(state["runs"][0]["tokens"])
        self.assertEqual(state["runs"][0]["telemetry"], "legacy_missing")
        self.assertEqual(state["issues"]["1"]["attempts"], 1)

    def test_low_queue_refills_to_ten(self):
        self.assertEqual(queue_refill_count(0), 10)
        self.assertEqual(queue_refill_count(2), 8)

    def test_healthy_queue_is_a_noop(self):
        self.assertEqual(queue_refill_count(3), 0)
        self.assertEqual(queue_refill_count(10), 0)

    def test_ready_work_is_selectable_even_when_refill_is_needed(self):
        issues = [{"number": 75, "title": "[agent-ready] independent", "body": "", "createdAt": "2026-01-01"}]
        selected = select_issue(issues, {"issues": {}}, 3, {73})
        self.assertEqual(selected["number"], 75)
        self.assertGreater(queue_refill_count(1, design_blocked=True), 0)

    def test_open_design_block_allows_independent_queue_replanning(self):
        self.assertEqual(queue_refill_count(0, design_blocked=True), 10)
        self.assertEqual(queue_refill_count(2, design_blocked=True), 8)

    def test_plan_prevents_issue_and_pr_title_duplicates(self):
        plan = {
            "outcome": "planned",
            "issues": [
                {"kind": "agent-ready", "title": "Existing work!", "body": "## Acceptance criteria\n- done\n## Automated validation\n- test", "question": ""},
                {"kind": "agent-ready", "title": "New work", "body": "## Acceptance criteria\n- done\n## Automated validation\n- test", "question": ""},
            ],
        }
        items = prepare_plan_items(plan, ["[agent-ready] Existing work"], 10)
        self.assertEqual([item["title"] for item in items], ["[agent-ready] New work"])

    def test_planned_and_ready_titles_are_the_same_logical_work(self):
        self.assertEqual(
            normalized_work_title("[planned] Foo"),
            normalized_work_title("[agent-ready] Foo"),
        )
        plan = {"outcome": "planned", "issues": [{
            "kind": "agent-ready", "title": "Foo",
            "body": "## Acceptance criteria\n- done\n## Automated validation\n- test", "question": "",
        }]}
        self.assertEqual(prepare_plan_items(plan, ["[planned] Foo"], 10), [])

    def test_planned_promotion_requires_previous_phase_complete(self):
        issue = {"number": 8, "title": "[planned] Phase 8: release", "body": ""}
        incomplete = "## Phase 7 — Integration\n\n- [x] done\n- [ ] pending\n\n## Phase 8 — RC\n- [ ] release\n"
        complete = incomplete.replace("- [ ] pending", "- [x] pending")
        self.assertEqual(eligible_planned_issues([issue], incomplete, {}), [])
        self.assertEqual(eligible_planned_issues([issue], complete, {}), [issue])

    def test_all_planned_dependencies_block_until_closed(self):
        issue = {
            "number": 8, "title": "[planned] Phase 8: release",
            "body": "Depends on: #224\n\nDepends on: #225",
        }
        roadmap = "## Phase 7 — Integration\n- [x] done\n\n## Phase 8 — RC\n- [ ] release\n"
        self.assertEqual(planned_dependency_numbers(issue), {224, 225})
        self.assertEqual(eligible_planned_issues([issue], roadmap, {224: "OPEN", 225: "CLOSED"}), [])
        self.assertEqual(eligible_planned_issues([issue], roadmap, {224: "CLOSED", 225: "OPEN"}), [])
        self.assertEqual(eligible_planned_issues([issue], roadmap, {224: "CLOSED", 225: "CLOSED"}), [issue])

    def test_dry_run_reports_eligibility_without_mutation_and_promotion_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "scenario" / "docs"
            docs.mkdir(parents=True)
            (docs / "ROADMAP.md").write_text(
                "## Phase 7 — Integration\n- [x] done\n\n## Phase 8 — RC\n- [ ] release\n",
                encoding="utf-8",
            )
            config = Config(repo_root=root, state_dir=root / "state")
            issue = {"number": 8, "title": "[planned] Phase 8: release", "body": "", "url": "u", "createdAt": "c"}
            with mock.patch("automation.warcraftmap_agent.worker.list_planned_issues", return_value=[issue]), \
                 mock.patch("automation.warcraftmap_agent.worker.run") as mutation:
                self.assertEqual(promote_planned_issues(config, dry_run=True), [issue])
                mutation.assert_not_called()
            with mock.patch("automation.warcraftmap_agent.worker.list_planned_issues", side_effect=[[issue], []]), \
                 mock.patch("automation.warcraftmap_agent.worker.run") as mutation:
                self.assertEqual(promote_planned_issues(config), [issue])
                self.assertEqual(promote_planned_issues(config), [])
                mutation.assert_called_once()

    def test_general_planned_issue_is_not_promoted(self):
        issue = {"number": 9, "title": "[planned] General cleanup", "body": ""}
        roadmap = "## Phase 7 — Integration\n- [x] done\n"
        self.assertEqual(eligible_planned_issues([issue], roadmap, {}), [])

    def test_plan_preserves_phase_and_dependency_order(self):
        plan = {
            "outcome": "planned",
            "issues": [
                {"kind": "agent-ready", "title": "Phase 0 prerequisite", "body": "## Acceptance criteria\n- done\n## Automated validation\n- test", "question": ""},
                {"kind": "agent-ready", "title": "Phase 2 dependent", "body": "## Acceptance criteria\n- done\n## Automated validation\n- test", "question": ""},
            ],
        }
        items = prepare_plan_items(plan, [], 10)
        self.assertEqual([item["title"] for item in items], ["[agent-ready] Phase 0 prerequisite", "[agent-ready] Phase 2 dependent"])

    def test_design_block_stops_later_ready_work(self):
        plan = {
            "outcome": "planned",
            "issues": [
                {"kind": "needs-design", "title": "Choose map scale", "body": "A locked choice is required.", "question": "Which documented map scale should the source map use?"},
                {"kind": "agent-ready", "title": "Build dependent map", "body": "## Acceptance criteria\n- done\n## Automated validation\n- test", "question": ""},
            ],
        }
        items = prepare_plan_items(plan, [], 10)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["title"].startswith("[needs-design]"))
        self.assertIn("Which documented map scale", items[0]["body"])

    def test_dependent_work_is_skipped_but_unrelated_work_continues(self):
        issues = [
            {"number": 1, "title": "[agent-ready] dependent", "body": "Blocked by: #9", "createdAt": "2026-01-01"},
            {"number": 2, "title": "[agent-ready] independent", "body": "", "createdAt": "2026-01-02"},
        ]
        self.assertEqual(select_issue(issues, {"issues": {}}, 3, {9})["number"], 2)

    def test_duplicate_design_question_is_not_prepared(self):
        question = "Which map scale should be used?"
        plan = {"outcome": "planned", "issues": [{"kind": "needs-design", "title": "Scale again", "body": "", "question": question}]}
        self.assertEqual(prepare_plan_items(plan, [], 10, [question]), [])

    def test_decision_question_ignores_duplicated_decision_section(self):
        question = "What exact Africa regional-content specification should Phase 5 use?"
        body = (
            "Context.\n\n"
            "## Decision required\n\n"
            f"{question}\n\n"
            "## Decision required\n\n"
            f"{question}\n"
        )
        self.assertEqual(decision_question(body), question)

    def test_create_plan_issues_skips_duplicate_question_even_if_existing_body_repeats_heading(self):
        question = "What exact Africa regional-content specification should Phase 5 use?"
        existing = [{
            "number": 108,
            "title": "[needs-design] Define Africa scope",
            "body": (
                "Context.\n\n"
                "## Decision required\n\n"
                f"{question}\n\n"
                "## Decision required\n\n"
                f"{question}\n"
            ),
            "url": "https://example/issues/108",
            "state": "OPEN",
        }]
        item = {
            "title": "[needs-design] Use existing issue #108: Define Africa scope",
            "body": f"## Decision required\n\n{question}",
            "question": question,
        }
        config = Config(repo_root=Path("/repo"), state_dir=Path("/state"))
        with mock.patch(
            "automation.warcraftmap_agent.worker.gh_json",
            side_effect=[existing, []],
        ), mock.patch("automation.warcraftmap_agent.worker.run") as invoked:
            self.assertEqual(create_plan_issues(config, [item]), 0)
        invoked.assert_not_called()

    def test_create_plan_issues_skips_question_from_closed_resolved_issue(self):
        question = "What exact Africa regional-content specification should Phase 5 use?"
        existing = [{
            "number": 108,
            "title": "[resolved-design] Define Africa scope",
            "body": (
                "Context.\n\n"
                "## Decision required\n\n"
                f"{question}\n\n"
                "## Resolved design\n\n"
                "Use the global regional-content rules."
            ),
            "url": "https://example/issues/108",
            "state": "CLOSED",
        }]
        item = {
            "title": "[needs-design] Use existing issue #108: Define Africa scope",
            "body": f"## Decision required\n\n{question}",
            "question": question,
        }
        config = Config(repo_root=Path("/repo"), state_dir=Path("/state"))
        with mock.patch(
            "automation.warcraftmap_agent.worker.gh_json",
            side_effect=[existing, []],
        ), mock.patch("automation.warcraftmap_agent.worker.run") as invoked:
            self.assertEqual(create_plan_issues(config, [item]), 0)
        invoked.assert_not_called()

    def test_notification_payload_contains_required_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Config(repo_root=Path(directory), state_dir=Path(directory), design_notification_command="notify --stdin")
            completed = mock.Mock(returncode=0, stdout="", stderr="")
            with mock.patch("automation.warcraftmap_agent.worker.subprocess.run", return_value=completed) as invoked:
                notify_design_blocker(config, {"number": 12, "title": "[needs-design] Scale", "url": "https://example/issues/12"}, "Which scale?")
            payload = json.loads(invoked.call_args.kwargs["input"])
            self.assertEqual(payload, {"issue_number": 12, "title": "[needs-design] Scale", "url": "https://example/issues/12", "question": "Which scale?"})

    def test_notification_failure_does_not_undo_created_issue(self):
        item = {"title": "[needs-design] Scale", "body": "## Decision required\n\nWhich scale?", "question": "Which scale?"}
        config = Config(repo_root=Path("/repo"), state_dir=Path("/state"), design_notification_command="notify")
        created = mock.Mock(stdout="https://example/issues/12\n")
        with mock.patch("automation.warcraftmap_agent.worker.gh_json", side_effect=[[], []]), \
             mock.patch("automation.warcraftmap_agent.worker.run", return_value=created), \
             mock.patch("automation.warcraftmap_agent.worker.notify_design_blocker", side_effect=RuntimeError("offline")) as notified:
            self.assertEqual(create_plan_issues(config, [item]), 1)
        notified.assert_called_once()


    def test_plan_keeps_work_explicitly_independent_of_new_blocker(self):
        plan = {"outcome": "planned", "issues": [
            {"kind": "needs-design", "title": "Choose scale", "body": "", "question": "Which scale?"},
            {"kind": "agent-ready", "title": "Unrelated tooling", "body": "This is independent of the scale decision.\n## Acceptance criteria\n- done\n## Automated validation\n- test", "question": ""},
        ]}
        self.assertEqual(len(prepare_plan_items(plan, [], 10)), 2)


    def test_normalizes_both_github_check_shapes(self):
        self.assertEqual(
            check_state(
                {
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                }
            ),
            "passed",
        )
        self.assertEqual(check_state({"status": "IN_PROGRESS"}), "pending")
        self.assertEqual(check_state({"state": "SUCCESS"}), "passed")
        self.assertEqual(check_state({"state": "FAILURE"}), "failed")


if __name__ == "__main__":
    unittest.main()
