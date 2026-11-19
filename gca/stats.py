"""Persistent per-topic stats with adaptive difficulty.

Stored as JSON at ``~/.config/gca/stats.json`` (override with the
``GCA_STATS`` environment variable).  Adaptive rule:

* three first-try correct answers in a row -> level up (max 5)
* two misses in a row -> level down (min 1)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gca.engine.generate import Problem

MAX_LEVEL: int = 5
DEFAULT_SESSION_LENGTH: int = 10


def stats_path() -> Path:
    env = os.environ.get("GCA_STATS")
    if env:
        return Path(env)
    return Path.home() / ".config" / "gca" / "stats.json"


@dataclass
class TopicStat:
    """Rolling record for one topic."""

    level: int = 1
    streak: int = 0  # consecutive first-try corrects
    wrong_run: int = 0  # consecutive misses
    seen: int = 0
    first_try_correct: int = 0
    retried_correct: int = 0
    missed: int = 0

    @property
    def accuracy(self) -> float:
        if self.seen == 0:
            return 0.0
        return (self.first_try_correct + self.retried_correct) / self.seen

    def to_dict(self) -> dict[str, int]:
        return {
            "level": self.level,
            "streak": self.streak,
            "wrong_run": self.wrong_run,
            "seen": self.seen,
            "first_try_correct": self.first_try_correct,
            "retried_correct": self.retried_correct,
            "missed": self.missed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopicStat":
        known = {f: data.get(f, 0) for f in (
            "level", "streak", "wrong_run", "seen",
            "first_try_correct", "retried_correct", "missed",
        )}
        stat = cls(**known)  # type: ignore[arg-type]
        stat.level = max(1, min(MAX_LEVEL, int(stat.level)))
        return stat


@dataclass
class Outcome:
    """The result of one practice question."""

    topic: str
    difficulty: int
    first_try: bool  # solved on the first submission
    solved: bool  # solved at all (first try or retry)
    seconds: float


@dataclass
class SessionRecord:
    timestamp: float
    topic: str
    difficulty: int
    outcome: str  # "first_try" | "retried" | "missed"
    seconds: float


@dataclass
class Stats:
    topics: dict[str, TopicStat] = field(default_factory=dict)
    history: list[SessionRecord] = field(default_factory=list)
    sessions_played: int = 0

    # ------------------------------------------------------------------ #

    def topic(self, topic_id: str) -> TopicStat:
        return self.topics.setdefault(topic_id, TopicStat())

    def level_for(self, topic_id: str) -> int:
        return self.topic(topic_id).level

    def record(self, problem: Problem, outcome: Outcome) -> None:
        """Update stats for one answered question and persist."""
        stat = self.topic(problem.topic)
        stat.seen += 1
        if outcome.solved and outcome.first_try:
            stat.first_try_correct += 1
            stat.streak += 1
            stat.wrong_run = 0
            if stat.streak >= 3:
                stat.level = min(MAX_LEVEL, stat.level + 1)
                stat.streak = 0
        elif outcome.solved:
            stat.retried_correct += 1
            stat.streak = 0
            stat.wrong_run = 0
        else:
            stat.missed += 1
            stat.streak = 0
            stat.wrong_run += 1
            if stat.wrong_run >= 2:
                stat.level = max(1, stat.level - 1)
                stat.wrong_run = 0
        self.history.append(
            SessionRecord(
                timestamp=time.time(),
                topic=problem.topic,
                difficulty=outcome.difficulty,
                outcome=(
                    "first_try" if outcome.first_try and outcome.solved
                    else "retried" if outcome.solved
                    else "missed"
                ),
                seconds=outcome.seconds,
            )
        )
        if len(self.history) > 200:
            self.history = self.history[-200:]
        self.save()

    # ------------------------------------------------------------------ #

    def weakest(self) -> list[str]:
        """Topic ids ordered worst-first by accuracy (seen topics only)."""
        seen = [(tid, s) for tid, s in self.topics.items() if s.seen > 0]
        return [tid for tid, _ in sorted(seen, key=lambda kv: kv[1].accuracy)]

    def save(self) -> None:
        path = stats_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "topics": {tid: s.to_dict() for tid, s in self.topics.items()},
            "sessions_played": self.sessions_played,
            "history": [h.__dict__ for h in self.history[-50:]],
        }
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")

    @classmethod
    def load(cls) -> "Stats":
        path = stats_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        stats = cls(
            topics={
                tid: TopicStat.from_dict(sd)
                for tid, sd in data.get("topics", {}).items()
            },
            sessions_played=int(data.get("sessions_played", 0)),
        )
        stats.history = [
            SessionRecord(
                timestamp=float(h.get("timestamp", 0.0)),
                topic=str(h.get("topic", "")),
                difficulty=int(h.get("difficulty", 1)),
                outcome=str(h.get("outcome", "missed")),
                seconds=float(h.get("seconds", 0.0)),
            )
            for h in data.get("history", [])
        ]
        return stats
