"""Local checks for benchmark construction and temporal ablation."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from evaluate import graph_context, longmemeval_cases, parse_date, synthetic_correct
from synthetic import cases


class BenchmarkChecks(unittest.TestCase):
    def test_synthetic_ground_truth_is_complete_and_unique(self):
        all_cases = cases()
        self.assertEqual(len(all_cases), 20)
        self.assertEqual(len({x["id"] for x in all_cases}), 20)
        for case in all_cases:
            self.assertEqual(len(case["episodes"]), 2)
            self.assertEqual(len(case["questions"]), 3)
            self.assertLess(case["episodes"][0]["date"], case["episodes"][1]["date"])

    def test_ablation_removes_only_temporal_metadata(self):
        edge = SimpleNamespace(
            fact="Maya works at Harbor Studio",
            valid_at=datetime(2024, 4, 15, tzinfo=timezone.utc),
            invalid_at=None,
        )
        with_time = graph_context([edge], True)
        without_time = graph_context([edge], False)
        self.assertIn(edge.fact, with_time)
        self.assertIn(edge.fact, without_time)
        self.assertIn("valid_at=", with_time)
        self.assertNotIn("valid_at=", without_time)

    def test_date_scoring_and_public_selection(self):
        self.assertTrue(synthetic_correct("2024-04-03", "April 3, 2024"))
        self.assertFalse(synthetic_correct("2024-04-03", "April 4, 2024"))
        self.assertEqual(parse_date("2023/04/10 (Mon) 17:50").hour, 17)
        sample = longmemeval_cases(1, 5660, 30000)
        self.assertEqual(len(sample), 3)
        for case in sample:
            self.assertNotIn("has_answer", str(case["episodes"]))
            self.assertTrue(all(set(e) == {"date", "body", "session_id"} for e in case["episodes"]))


if __name__ == "__main__":
    unittest.main()

