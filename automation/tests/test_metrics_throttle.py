"""Regression tests: incomplete historic PR metrics must not starve Codex."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from automation.warcraftmap_agent import integration, worker


NOW = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)


def record(number: int, status: str = "merged", observed: datetime | None = None) -> dict:
    row = {"pr": 500 + number, "status": status}
    data = integration.metrics(row)
    data["ci_unattributed_runs"] = 6
    if observed is not None:
        data["ci_observed_at"] = observed.isoformat()
    return row


class HistoricalMetricsThrottleTests(TestCase):
    def test_live_metrics_first_and_at_most_two_old_merged_per_wake(self):
        history = {str(n): record(n, observed=NOW - timedelta(days=n))
                   for n in range(1, 8)}
        history["99"] = record(99, "pr_open")
        due = worker.due_pr_metrics({"issues": history}, NOW)
        self.assertEqual(["99", "7", "6"], [n for n, _ in due])
        self.assertTrue(all(history[n]["metrics"]["ci_unattributed_runs"] == 6
                            for n in history))

    def test_recent_incomplete_historical_receipt_does_not_republish_hourly(self):
        row = record(1, observed=NOW - timedelta(minutes=15))
        self.assertEqual([], worker.due_pr_metrics({"issues": {"1": row}}, NOW))
        self.assertNotIn("metrics_finalized", row)

    def test_closed_unmerged_pr_is_historical_not_an_active_run(self):
        rows = {
            "1": record(1, status="pr_closed", observed=NOW - timedelta(days=10)),
            "2": record(2, status="pr_closed", observed=NOW - timedelta(days=10)),
            "3": record(3, status="pr_closed", observed=NOW - timedelta(days=10)),
        }
        self.assertEqual(2, len(worker.due_pr_metrics({"issues": rows}, NOW)))
        rows["1"]["metrics_last_attempt_at"] = (NOW - timedelta(minutes=5)).isoformat()
        rows["1"]["metrics_last_attempt_status"] = "pr_closed"
        self.assertEqual(["2", "3"], [n for n, _ in
                         worker.due_pr_metrics({"issues": rows}, NOW)])

    def test_status_transition_refreshes_immediately_even_with_recent_poll(self):
        row = record(1, observed=NOW - timedelta(minutes=5))
        row["metrics_last_attempt_at"] = (NOW - timedelta(minutes=5)).isoformat()
        row["metrics_last_attempt_status"] = "pr_open"
        self.assertEqual(["1"], [n for n, _ in
                         worker.due_pr_metrics({"issues": {"1": row}}, NOW)])

    def test_publishing_merged_backlog_rotates_instead_of_repeating_all(self):
        with TemporaryDirectory() as directory:
            config = worker.Config(Path(directory), Path(directory) / "state")
            history = {str(n): record(n, observed=NOW - timedelta(days=30))
                       for n in range(1, 7)}
            history["99"] = record(99, "pr_open")
            state = {"version": 3, "issues": history, "runs": []}
            with mock.patch.object(worker, "collect_ci_metrics") as collect, \
                 mock.patch.object(worker, "gh_json", return_value={"body": "Owner text"}), \
                 mock.patch.object(worker, "run"):
                worker.emit_pr_metrics(config, state)
                first = [n for n, row in history.items()
                         if row.get("metrics_last_attempt_at")]
                self.assertEqual(2, len(first))
                self.assertEqual(3, collect.call_count)  # 2 historic + 1 live
                self.assertTrue(all(not history[n].get("metrics_finalized") for n in first))
                worker.emit_pr_metrics(config, state)
                second = [n for n, row in history.items()
                          if row.get("metrics_last_attempt_at")]
                self.assertEqual(4, len(second))
                self.assertEqual(6, collect.call_count)
                self.assertEqual("pr_open", history["99"]["status"])


if __name__ == "__main__":
    import unittest
    unittest.main()
