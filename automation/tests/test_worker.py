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
    load_env,
    load_state,
    parse_codex_token_usage,
    create_plan_issues,
    decision_question,
    notify_design_blocker,
    prepare_plan_items,
    queue_refill_count,
    reconcile_ready_issue_states,
    select_issue,
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

    def test_resolved_design_issue_reenters_queue(self):
        issues = [{"number": 73, "title": "[agent-ready] resumed", "createdAt": "2026-01-01"}]
        state = {"issues": {"73": {"attempts": 1, "status": "needs_design", "last_failure": "old question"}}}
        reconcile_ready_issue_states(issues, state)
        self.assertEqual(state["issues"]["73"]["status"], "queued")
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

    def test_pr_merge_does_not_delete_branch_checked_out_by_worktree(self):
        command = build_pr_merge_command(17)
        self.assertEqual(command, ["gh", "pr", "merge", "17", "--merge"])
        self.assertNotIn("--delete-branch", command)

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
