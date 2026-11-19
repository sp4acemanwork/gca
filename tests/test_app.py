"""Smoke test: the TUI boots, asks questions, grades typed answers."""

from __future__ import annotations

import os
import random
import tempfile
import unittest
from pathlib import Path

from textual.containers import VerticalScroll
from textual.widgets import ListView

from gca.app import GcaApp, PracticeScreen, StatsScreen
from gca.engine.generate import get_topic
from gca.stats import Outcome, Stats


class TestAppSmoke(unittest.IsolatedAsyncioTestCase):
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

    async def test_practice_screen_answers_questions(self) -> None:
        app = GcaApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            # Push straight into practice on a numeric topic.
            app.stats = Stats()  # fresh stats, level 1
            screen = PracticeScreen(
                ["int_arith"], Stats(), difficulty_override=1, count=2, seed=42
            )
            app.push_screen(screen)
            await pilot.pause()
            self.assertIsNotNone(screen.problem)
            answer = screen.problem.answer
            for ch in answer:
                await pilot.press(ch)
            await pilot.press("enter")
            await pilot.pause()
            feedback = str(screen.query_one("#feedback").render())
            self.assertIn("Correct", feedback)
            # Resolved; Enter advances to question 2.
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(screen.q_index, 1)
            self.assertIsNotNone(screen.problem)

    async def test_wrong_answer_then_reveal(self) -> None:
        app = GcaApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            screen = PracticeScreen(
                ["int_arith"], Stats(), difficulty_override=1, count=1, seed=42
            )
            app.push_screen(screen)
            await pilot.pause()
            assert screen.problem is not None
            for _ in range(2):
                for ch in "999999":
                    await pilot.press(ch)
                await pilot.press("enter")
                await pilot.pause()
            self.assertTrue(screen.problem is None)
            self.assertIn("Answer:", str(screen.query_one("#feedback").render()))

    async def test_vim_nav_on_menu(self) -> None:
        app = GcaApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            lv = app.screen.query_one("#menu-list", ListView)
            self.assertIsNone(lv.index)  # nothing highlighted until a nav key
            await pilot.press("j", "j", "k")
            await pilot.pause()
            self.assertEqual(lv.index, 1)  # first j -> 0, second -> 1, k -> back
            await pilot.press("G")
            await pilot.pause()
            self.assertEqual(lv.index, len(lv) - 1)
            await pilot.press("g")
            await pilot.pause()
            self.assertEqual(lv.index, 0)

    async def test_vim_scroll_on_stats_screen(self) -> None:
        app = GcaApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            problem = get_topic("int_arith").gen(random.Random(1), 1)
            app.stats.record(problem, Outcome("int_arith", 1, True, True, 2.0))
            app.push_screen(StatsScreen(app.stats))
            await pilot.pause()
            scroller = app.screen.query_one(VerticalScroll)
            self.assertEqual(scroller.scroll_y, 0)
            await pilot.press("j", "j")
            await pilot.pause()
            self.assertGreaterEqual(scroller.scroll_target_y, 0)
            await pilot.press("G")
            await pilot.pause()
            await pilot.press("g")
            await pilot.pause()
            self.assertLessEqual(scroller.scroll_target_y, scroller.max_scroll_y)


if __name__ == "__main__":
    unittest.main()
