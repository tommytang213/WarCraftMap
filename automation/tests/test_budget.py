from datetime import datetime, timedelta, timezone
import unittest

from automation.warcraftmap_agent.budget import budget_available, recent_invocations


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)

    def stamp(self, delta):
        return (self.now - delta).isoformat().replace("+00:00", "Z")

    def test_daily_limit(self):
        allowed, reason = budget_available([self.stamp(timedelta(hours=1))], self.now, 1, 5)
        self.assertFalse(allowed)
        self.assertIn("daily", reason)

    def test_rolling_week_limit(self):
        history = [self.stamp(timedelta(days=day)) for day in range(1, 6)]
        allowed, reason = budget_available(history, self.now, 1, 5)
        self.assertFalse(allowed)
        self.assertIn("seven-day", reason)

    def test_old_entries_are_discarded(self):
        history = [self.stamp(timedelta(days=8)), self.stamp(timedelta(days=2))]
        self.assertEqual(recent_invocations(history, self.now), history[1:])
        self.assertTrue(budget_available(history, self.now, 1, 5)[0])


if __name__ == "__main__":
    unittest.main()

