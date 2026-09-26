from datetime import datetime, timedelta, timezone
import unittest

from automation.warcraftmap_agent.budget import (
    budget_available,
    recent_runs,
    usage_summary,
)


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)

    def stamp(self, delta):
        return (self.now - delta).isoformat().replace("+00:00", "Z")

    def run(self, delta, tokens):
        return {
            "timestamp": self.stamp(delta),
            "tokens": tokens,
            "telemetry": "reported" if tokens is not None else "missing",
        }

    def test_daily_token_limit(self):
        history = [self.run(timedelta(hours=1), 100_000_000)]
        allowed, reason = budget_available(
            history, self.now, 100_000_000, 500_000_000, 10, 50
        )
        self.assertFalse(allowed)
        self.assertIn("daily Codex token", reason)

    def test_rolling_week_token_limit(self):
        history = [
            self.run(timedelta(days=day), 100_000_000)
            for day in range(1, 6)
        ]
        allowed, reason = budget_available(
            history, self.now, 100_000_000, 500_000_000, 10, 50
        )
        self.assertFalse(allowed)
        self.assertIn("seven-day Codex token", reason)

    def test_daily_emergency_run_cap(self):
        history = [
            self.run(timedelta(hours=hour + 1), 1)
            for hour in range(10)
        ]
        allowed, reason = budget_available(
            history, self.now, 100_000_000, 500_000_000, 10, 50
        )
        self.assertFalse(allowed)
        self.assertIn("daily emergency", reason)

    def test_unknown_telemetry_counts_as_run_not_zero_token_claim(self):
        history = [self.run(timedelta(hours=1), None)]
        summary = usage_summary(history, self.now)
        self.assertEqual(summary["daily_tokens"], 0)
        self.assertEqual(summary["daily_runs"], 1)
        self.assertEqual(summary["daily_unknown_runs"], 1)
        allowed, reason = budget_available(
            history, self.now, 100_000_000, 500_000_000, 10, 50
        )
        self.assertTrue(allowed)
        self.assertIn("telemetry-missing", reason)

    def test_old_entries_are_discarded(self):
        history = [
            self.run(timedelta(days=8), 400_000_000),
            self.run(timedelta(days=2), 1_000),
        ]
        self.assertEqual(recent_runs(history, self.now), history[1:])
        self.assertTrue(
            budget_available(
                history, self.now, 100_000_000, 500_000_000, 10, 50
            )[0]
        )


if __name__ == "__main__":
    unittest.main()
