"""Generator sanity: every topic, every difficulty, self-grades correct."""

from __future__ import annotations

import random
import unittest

from gca.engine.generate import all_topics
from gca.engine.grade import check


class TestGenerators(unittest.TestCase):
    def test_all_topics_generate_and_self_grade(self) -> None:
        topics = all_topics()
        self.assertGreaterEqual(len(topics), 15)
        for topic in topics:
            for difficulty in range(1, 6):
                for seed in range(6):
                    problem = topic.gen(random.Random(seed * 7 + difficulty), difficulty)
                    with self.subTest(
                        topic=topic.id, difficulty=difficulty, seed=seed
                    ):
                        self.assertTrue(problem.prompt.strip(), "empty prompt")
                        self.assertTrue(problem.answer.strip(), "empty answer")
                        self.assertTrue(problem.hint.strip(), "empty hint")
                        self.assertGreaterEqual(len(problem.steps), 1)
                        result = check(problem.answer, problem.answer, problem.kind)
                        self.assertTrue(
                            result.correct,
                            f"self-grade failed: {problem.answer!r}: {result.message}",
                        )

    def test_difficulty_clamped(self) -> None:
        for topic in all_topics():
            for difficulty in (0, -3, 99):
                problem = topic.gen(random.Random(1), difficulty)
                self.assertTrue(1 <= problem.difficulty <= 5)


if __name__ == "__main__":
    unittest.main()
