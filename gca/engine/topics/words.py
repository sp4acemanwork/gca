"""Word problems: the setup-then-solve muscle memory."""

from __future__ import annotations

import random

from gca.engine.generate import Problem, Topic, make_problem, ri

TRACK = "Word problems"


def _word_problems(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    if d == 1:
        a = ri(rng, 3, 9)
        b = ri(rng, 1, a + 20)
        s = a + b
        prompt = f"Two numbers add to {s}. One is {a}. What is the other?"
        answer = str(b)
        steps = [
            f"Setup: x + {a} = {s}.",
            f"x = {s} - {a} = {b}.",
        ]
    elif d == 2:
        n = ri(rng, 4, 12)
        prompt = (
            f"The product of two consecutive integers is {n * (n + 1)}. "
            "What is the larger one?"
        )
        answer = str(n + 1)
        steps = [
            f"Setup: x(x + 1) = {n * (n + 1)} -> x^2 + x - {n * (n + 1)} = 0.",
            f"Factor: (x + {n + 1})(x - {n}) = 0.",
            f"x = {n} (drop the negative root), so the larger is {n + 1}.",
        ]
    elif d == 3:
        gap = ri(rng, 4, 10)
        b = ri(rng, 1, gap - 1)
        a = b + gap
        years = gap - b
        prompt = (
            f"Ana is {gap} years older than Ben. In {years} years, Ana will be "
            f"twice as old as Ben. How old is Ana now?"
        )
        answer = str(a)
        steps = [
            f"Setup: Ana now = x, Ben now = x - {gap}.",
            f"In {years} years: x + {years} = 2(x - {gap} + {years}).",
            f"Solve: x + {years} = 2x - {2 * gap} + {2 * years} -> x = {2 * gap - years} = {a}.",
            f"Check: Ben is {b} now; in {years} years Ana is {a + years} = 2 * {b + years} = {2 * (b + years)}.",
        ]
    elif d == 4:
        speed = ri(rng, 6, 15) * 10
        hours = ri(rng, 2, 6)
        dist = speed * hours
        prompt = (
            f"A train covers {dist} km at a steady {speed} km/h. "
            "How many hours did the trip take?"
        )
        answer = str(hours)
        steps = [
            f"distance = speed * time: {dist} = {speed} * t.",
            f"t = {dist}/{speed} = {hours} h.",
        ]
    else:
        n = ri(rng, 8, 12)
        games = n * (n - 1) // 2
        prompt = (
            f"In a league every team plays every other team exactly once. "
            f"{games} games were played in total. How many teams are there?"
        )
        answer = str(n)
        steps = [
            f"Setup: each unordered pair of teams plays once -> C(n,2) = {games}.",
            f"n(n-1)/2 = {games} -> n(n-1) = {2 * games}.",
            f"n^2 - n - {2 * games} = 0 = (n - {n})(n + {n - 1}); positive root n = {n}.",
        ]
    hint = "Translate words into an equation first, solve, and sanity-check the answer."
    return make_problem("word_problems", d, prompt, answer, "expr", hint, tuple(steps))


TOPICS: tuple[Topic, ...] = (
    Topic("word_problems", "Word problems", TRACK,
          "Consecutive integers, ages, rates, round-robin counts", _word_problems),
)
