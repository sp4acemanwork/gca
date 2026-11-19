"""Textual TUI for the algebra drill trainer.

Screens: Menu (topic picker + difficulty override), Practice (question ->
typed answer -> graded feedback with hints/steps), Summary, Stats.
Designed to fit an 80x24 editor terminal.
"""

from __future__ import annotations

import random
import time
from collections.abc import Sequence

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from gca.engine.generate import Problem, TRACK_ORDER, all_topics, get_topic
from gca.engine.grade import check
from gca.stats import DEFAULT_SESSION_LENGTH, MAX_LEVEL, Outcome, Stats

MENU_CSS = """
#menu-list { height: 1fr; }
#menu-list > ListItem { padding: 0 1; }
Label.section { color: $accent; text-style: bold; padding: 1 0 0 0; }
"""

PRACTICE_CSS = """
#problem { border: round $accent; padding: 0 2; margin: 1 2; height: auto; max-height: 6; }
#problem-text { text-style: bold; }
#feedback { margin: 0 2; height: auto; max-height: 12; }
#answer { margin: 1 2; }
#progress { color: $text-muted; margin: 0 2; height: 1; }
#hint-line { color: $warning; }
#steps { color: $text; }
#reveal { color: $success; text-style: bold; }
"""

SUMMARY_CSS = """
#summary-body { margin: 1 2; }
Table { margin: 1 0; }
"""


class GcaApp(App[None]):
    """Root application."""

    CSS = PRACTICE_CSS + MENU_CSS + SUMMARY_CSS
    TITLE = "gca - algebra drills"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self, seed: int | None = None) -> None:
        super().__init__()
        self.stats: Stats = Stats.load()
        self.seed = seed

    def on_mount(self) -> None:
        self.push_screen(MenuScreen(self.stats))


class MenuScreen(Screen[None]):
    """Topic picker with adaptive/fixed difficulty toggle."""

    BINDINGS = [
        Binding("d", "toggle_difficulty", "Difficulty"),
        Binding("s", "show_stats", "Stats"),
        Binding("escape", "app.pop_screen", "Back"),
        Binding("j", "vim_down", "Down", show=False),
        Binding("k", "vim_up", "Up", show=False),
        Binding("g", "vim_top", "Top", show=False),
        Binding("G", "vim_bottom", "Bottom", show=False),
    ]
    LEVEL_NAMES: tuple[str, ...] = ("Auto", "1", "2", "3", "4", "5")

    def __init__(self, stats: Stats) -> None:
        super().__init__()
        self.stats = stats
        self.difficulty_index = 0  # 0 = adaptive, 1..5 = fixed
        self.session_length = DEFAULT_SESSION_LENGTH

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static(self._header_text(), id="menu-header")
            yield ListView(id="menu-list")
        yield Footer()

    def on_mount(self) -> None:
        self._rebuild_list()

    def _list(self) -> ListView:
        return self.query_one("#menu-list", ListView)

    def action_vim_down(self) -> None:
        self._list().action_cursor_down()

    def action_vim_up(self) -> None:
        self._list().action_cursor_up()

    def action_vim_top(self) -> None:
        self._list().index = 0

    def action_vim_bottom(self) -> None:
        self._list().index = len(self._list()) - 1

    def _header_text(self) -> str:
        mode = self.LEVEL_NAMES[self.difficulty_index]
        return (
            f" Pick a track/topic and press Enter. [b]j/k[/b] navigate, [b]g/G[/b] top/bottom - "
            f"[b]d[/b] difficulty: [b]{mode}[/b] - "
            f"[b]s[/b] stats - {self.session_length} questions/session"
        )

    def _rebuild_list(self) -> None:
        lv = self.query_one("#menu-list", ListView)
        lv.clear()
        topics = all_topics()
        current_track: str | None = None
        for topic in topics:
            if topic.track != current_track:
                current_track = topic.track
                lv.append(ListItem(Label(topic.track, classes="section"), disabled=True))
            stat = self.stats.topic(topic.id)
            lv.append(ListItem(Label(
                f"  {topic.title} - {topic.blurb} "
                f"[Lv {stat.level} / {stat.accuracy * 100:.0f}%]"
            )))
        lv.append(ListItem(Label("  Mixed drill - adaptive across all topics")))
        lv.focus()

    def action_toggle_difficulty(self) -> None:
        self.difficulty_index = (self.difficulty_index + 1) % (MAX_LEVEL + 1)
        self.query_one("#menu-header", Static).update(self._header_text())

    def action_show_stats(self) -> None:
        self.app.push_screen(StatsScreen(self.stats))

    @on(ListView.Selected)
    def start_practice(self, event: ListView.Selected) -> None:
        index = event.list_view.index
        if index is None:
            return
        topics = all_topics()
        override = None if self.difficulty_index == 0 else self.difficulty_index
        if index < len(topics):
            self.app.push_screen(
                PracticeScreen(
                    [topics[index].id], self.stats, override, self.session_length,
                    seed=getattr(self.app, "seed", None),
                )
            )
        else:
            self.app.push_screen(
                PracticeScreen(
                    [t.id for t in topics], self.stats, override, self.session_length,
                    seed=getattr(self.app, "seed", None),
                )
            )


class PracticeScreen(Screen[None]):
    """Ask questions, grade typed answers, coach on misses."""

    BINDINGS = [
        Binding("question_mark", "hint", "Hint", priority=True),
        Binding("ctrl+w", "steps", "Worked solution", priority=True),
        Binding("tab", "skip", "Skip", priority=True),
        Binding("escape", "back", "Back", priority=True),
    ]

    def __init__(
        self,
        topic_ids: Sequence[str],
        stats: Stats,
        difficulty_override: int | None,
        count: int = DEFAULT_SESSION_LENGTH,
        seed: int | None = None,
    ) -> None:
        super().__init__()
        self.topic_ids = list(topic_ids)
        self.stats = stats
        self.override = difficulty_override
        self.count = count
        self.rng = random.Random(seed)
        self.queue: list[Problem] = []
        self.results: list[tuple[Problem, Outcome]] = []
        self.q_index = -1
        self.problem: Problem | None = None
        self.attempt = 0
        self.started_at = 0.0
        self.hint_shown = False
        self._feedback: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("", id="progress")
            with VerticalScroll(id="problem"):
                yield Static("", id="problem-text")
            yield Static("", id="feedback")
            yield Input(placeholder="type your answer, Enter to submit", id="answer")
        yield Footer()

    def on_mount(self) -> None:
        self._next_question()
        self.query_one("#answer", Input).focus()

    # -- question flow --------------------------------------------------- #

    def _next_question(self) -> None:
        self.q_index += 1
        if self.q_index >= self.count:
            self.stats.sessions_played += 1
            self.stats.save()
            self.app.push_screen(
                SummaryScreen(
                    self.results,
                    self.stats,
                    self.topic_ids,
                    self.override,
                    self.count,
                )
            )
            return
        topic_id = self._pick_topic()
        level = self.override if self.override is not None else self.stats.level_for(topic_id)
        problem = get_topic(topic_id).gen(self.rng, level)
        self.problem = problem
        self.attempt = 0
        self.hint_shown = False
        self._feedback = []
        self.started_at = time.monotonic()
        self.query_one("#progress", Static).update(
            f"Q{self.q_index + 1}/{self.count} - "
            f"{get_topic(topic_id).title} - difficulty {problem.difficulty}"
        )
        self.query_one("#problem-text", Static).update(problem.prompt)
        self._render_feedback()
        answer_input = self.query_one("#answer", Input)
        answer_input.value = ""
        answer_input.disabled = False
        answer_input.focus()

    def _render_feedback(self) -> None:
        self.query_one("#feedback", Static).update("\n".join(self._feedback))

    def _pick_topic(self) -> str:
        if len(self.topic_ids) == 1:
            return self.topic_ids[0]
        # Weight weak topics higher: weight = 1 + misses + (5 - level)
        weights = []
        for tid in self.topic_ids:
            stat = self.stats.topic(tid)
            weights.append(1.0 + stat.missed + (MAX_LEVEL - stat.level))
        return self.rng.choices(self.topic_ids, weights=weights)[0]

    # -- grading ---------------------------------------------------------- #

    @on(Input.Submitted)
    def submit(self, event: Input.Submitted) -> None:
        if self.problem is None:
            self._next_question()
            return
        text = event.value
        if self.attempt >= 2:
            self._next_question()
            return
        self.attempt += 1
        result = check(self.problem.answer, text, self.problem.kind)
        if result.correct:
            outcome = Outcome(
                topic=self.problem.topic,
                difficulty=self.problem.difficulty,
                first_try=self.attempt == 1,
                solved=True,
                seconds=time.monotonic() - self.started_at,
            )
            self.stats.record(self.problem, outcome)
            self.results.append((self.problem, outcome))
            self._feedback = [
                "[b]Correct![/b] Enter for the next one."
                + ("" if self.attempt == 1 else " (after a retry)")
            ]
            self._render_feedback()
            self.problem = None  # resolved; next Enter advances
        elif self.attempt == 1:
            self._feedback = [
                f"[b]Not quite.[/b] {result.message}",
                "Try again - or [b]?[/b] for a hint, [b]ctrl+w[/b] for the worked solution.",
            ]
            self._render_feedback()
            self.action_hint()
        else:
            outcome = Outcome(
                topic=self.problem.topic,
                difficulty=self.problem.difficulty,
                first_try=False,
                solved=False,
                seconds=time.monotonic() - self.started_at,
            )
            self.stats.record(self.problem, outcome)
            self.results.append((self.problem, outcome))
            self._reveal(result.message)
            self.problem = None

    def _reveal(self, message: str) -> None:
        assert self.problem is not None
        self._feedback = [
            f"[b]Missed.[/b] {message}",
            f"[b]Answer:[/b] {self.problem.answer}",
            "",
            *self.problem.steps,
        ]
        self._render_feedback()
        self.query_one("#answer", Input).disabled = True

    # -- bindings ---------------------------------------------------------- #

    def action_hint(self) -> None:
        if self.problem is None or self.hint_shown:
            return
        self.hint_shown = True
        self._feedback.append(f"[hint]Hint:[/hint] {self.problem.hint}")
        self._render_feedback()

    def action_steps(self) -> None:
        if self.problem is None:
            return
        outcome = Outcome(
            topic=self.problem.topic,
            difficulty=self.problem.difficulty,
            first_try=False,
            solved=False,
            seconds=time.monotonic() - self.started_at,
        )
        self.stats.record(self.problem, outcome)
        self.results.append((self.problem, outcome))
        self._reveal("Worked solution shown - counts as a miss.")
        self.problem = None

    def action_skip(self) -> None:
        if self.problem is None:
            self._next_question()
            return
        outcome = Outcome(
            topic=self.problem.topic,
            difficulty=self.problem.difficulty,
            first_try=False,
            solved=False,
            seconds=time.monotonic() - self.started_at,
        )
        self.stats.record(self.problem, outcome)
        self.results.append((self.problem, outcome))
        self._reveal("Skipped.")
        self.problem = None

    def action_back(self) -> None:
        self.app.pop_screen()


class VimScrollScreen(Screen[None]):
    """Base screen adding vim-style scrolling (j/k lines, g/G top/bottom).

    Subclasses must compose exactly one scrollable container.
    """

    BINDINGS = [
        Binding("j", "vim_down", "Scroll down", show=False),
        Binding("k", "vim_up", "Scroll up", show=False),
        Binding("g", "vim_top", "Top", show=False),
        Binding("G", "vim_bottom", "Bottom", show=False),
    ]

    def _scroller(self) -> VerticalScroll:
        return self.query_one(VerticalScroll)

    def action_vim_down(self) -> None:
        self._scroller().scroll_down()

    def action_vim_up(self) -> None:
        self._scroller().scroll_up()

    def action_vim_top(self) -> None:
        self._scroller().scroll_home()

    def action_vim_bottom(self) -> None:
        self._scroller().scroll_end()


class SummaryScreen(VimScrollScreen):
    """End-of-session breakdown."""

    BINDINGS = VimScrollScreen.BINDINGS + [
        Binding("escape", "back", "Back"),
        Binding("r", "repeat", "Run again"),
    ]

    def __init__(
        self,
        results: Sequence[tuple[Problem, Outcome]],
        stats: Stats,
        topic_ids: Sequence[str],
        difficulty_override: int | None,
        count: int = DEFAULT_SESSION_LENGTH,
    ) -> None:
        super().__init__()
        self.results = list(results)
        self.stats = stats
        self.topic_ids = list(topic_ids)
        self.override = difficulty_override
        self.count = count

    def compose(self) -> ComposeResult:
        yield Header()
        body: list[str] = []
        total = len(self.results)
        first_try = sum(1 for _, o in self.results if o.solved and o.first_try)
        retried = sum(1 for _, o in self.results if o.solved and not o.first_try)
        missed = sum(1 for _, o in self.results if not o.solved)
        avg = (sum(o.seconds for _, o in self.results) / total) if total else 0.0
        body.append(
            f"[b]Session:[/b] {total} questions - {first_try} first-try, "
            f"{retried} after retry, {missed} missed - avg {avg:.1f}s"
        )
        per_topic: dict[str, tuple[int, int, int]] = {}
        for p, o in self.results:
            seen, solved, missed_t = per_topic.get(p.topic, (0, 0, 0))
            per_topic[p.topic] = (seen + 1, solved + (1 if o.solved else 0), missed_t + (0 if o.solved else 1))
        body.append("")
        body.append("[b]Per topic:[/b]")
        for tid, (seen, solved, missed_t) in sorted(per_topic.items()):
            title = get_topic(tid).title
            stat = self.stats.topic(tid)
            body.append(
                f"  {title}: {solved}/{seen} correct ({missed_t} missed) - now Lv {stat.level}"
            )
        weakest = [t for t in self.stats.weakest() if per_topic.get(t, (0, 0, 0))[2] > 0]
        if weakest:
            body.append("")
            body.append(
                f"[b]Drill next:[/b] {', '.join(get_topic(t).title for t in weakest[:3])}"
            )
        body.append("")
        body.append("[b]r[/b] to run this session again, [b]Esc[/b] for the menu.")
        with VerticalScroll(id="summary-body"):
            yield Static("\n".join(body))
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_repeat(self) -> None:
        self.app.pop_screen()
        self.app.push_screen(
            PracticeScreen(self.topic_ids, self.stats, self.override, self.count)
        )


class StatsScreen(VimScrollScreen):
    """Overall progress across all topics."""

    BINDINGS = VimScrollScreen.BINDINGS + [Binding("escape", "back", "Back")]

    def __init__(self, stats: Stats) -> None:
        super().__init__()
        self.stats = stats

    def compose(self) -> ComposeResult:
        yield Header()
        lines: list[str] = ["[b]Topic progress[/b]", ""]
        order = {t: i for i, t in enumerate(TRACK_ORDER)}
        topics = sorted(
            self.stats.topics.items(),
            key=lambda kv: (order.get(get_topic(kv[0]).track, 99), get_topic(kv[0]).title),
        )
        if not topics:
            lines.append("No practice yet - do a session first!")
        for tid, stat in topics:
            title = get_topic(tid).title
            lines.append(
                f"  {title}: Lv {stat.level} - seen {stat.seen} - "
                f"first-try {stat.first_try_correct} - missed {stat.missed} - "
                f"accuracy {stat.accuracy * 100:.0f}%"
            )
        lines.append("")
        lines.append(f"Sessions played: {self.stats.sessions_played}")
        with VerticalScroll():
            yield Static("\n".join(lines))
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()
