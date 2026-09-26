import json
import tempfile
import unittest
from pathlib import Path

from automation.warcraftmap_agent.worker import (
    Config,
    build_codex_command,
    check_state,
    load_env,
    load_state,
    parse_codex_token_usage,
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
