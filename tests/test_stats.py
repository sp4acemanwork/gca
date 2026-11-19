"""Stats: adaptive leveling and persistence round-trip."""

from __future__ import annotations

import json
import os
import random
import tempfile
import unittest
from pathlib import Path

from gca.engine.generate import get_topic
from gca.stats import Outcome, Stats, stats_path


class TestAdaptive(unittest.TestCase):
    def make_problem(self, topic: str = "factor_cubes", difficulty: int = 2):
        return get_topic(topic).gen(random.Random(1), difficulty)

    def setUp(self) -> None:
        self._old_env = os.environ.get("GCA_STATS")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        os.environ["GCA_STATS"] = str(Path(tmp.name) / "stats.json")

    def tearDown(self) -> None:
        if self._old_env is not None:
            os.environ["GCA_STATS"] = self._old_env
        else:
            os.environ.pop("GCA_STATS", None)

    def test_level_up_after_three(self) -> None:
        stats = Stats()
        problem = self.make_problem()
        for _ in range(3):
            stats.record(problem, Outcome(problem.topic, 1, True, True, 3.0))
        stat = stats.topic(problem.topic)
        self.assertEqual(stat.level, 2)
        self.assertEqual(stat.streak, 0)

    def test_level_down_after_two_misses(self) -> None:
        stats = Stats()
        problem = self.make_problem()
        stats.record(problem, Outcome(problem.topic, 3, False, True, 5.0))  # seed entry
        stats.record(problem, Outcome(problem.topic, 3, False, False, 5.0))  # reset runs
        stats.topic(problem.topic).level = 3
        for _ in range(2):
            stats.record(problem, Outcome(problem.topic, 3, False, False, 5.0))
        self.assertEqual(stats.topic(problem.topic).level, 2)

    def test_retry_counts_but_no_streak(self) -> None:
        stats = Stats()
        problem = self.make_problem()
        stats.record(problem, Outcome(problem.topic, 1, False, True, 4.0))
        stat = stats.topic(problem.topic)
        self.assertEqual(stat.retried_correct, 1)
        self.assertEqual(stat.streak, 0)

    def test_levels_capped(self) -> None:
        stats = Stats()
        problem = self.make_problem()
        for _ in range(20):
            stats.record(problem, Outcome(problem.topic, 1, True, True, 1.0))
        self.assertEqual(stats.topic(problem.topic).level, 5)

    def test_round_trip_persistence(self) -> None:
        stats = Stats()
        problem = self.make_problem()
        stats.record(problem, Outcome(problem.topic, 2, True, True, 2.5))
        stats.sessions_played = 3
        stats.save()
        loaded = Stats.load()
        self.assertEqual(
            loaded.topic(problem.topic).to_dict(),
            stats.topic(problem.topic).to_dict(),
        )
        self.assertEqual(loaded.sessions_played, 3)
        self.assertTrue(stats_path().exists())


if __name__ == "__main__":
    unittest.main()
