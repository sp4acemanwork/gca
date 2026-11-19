"""Combinatorics algebra: factorial simplification, binomial identities,
solving counting equations."""

from __future__ import annotations

import math
import random

from gca.engine.generate import Problem, Topic, make_problem, ri

TRACK = "Combinatorics algebra"


def _factorial_simplify(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    numeric = d <= 2 or (d >= 4 and rng.random() < 0.4)
    if numeric:
        n = {1: ri(rng, 4, 7), 2: ri(rng, 6, 9), 4: ri(rng, 7, 10), 5: ri(rng, 9, 12)}[d if d >= 1 else 1]
        k = ri(rng, 1, 3)
        prompt = f"{n}!/{n - k}!"
        value = math.prod(range(n - k + 1, n + 1))
        answer = str(value)
        steps = [
            f"Expand both factorials: {n}!/{n - k}! = {n}({n - 1})...({n - k + 1}) - "
            f"everything below {n - k + 1} cancels.",
            f"= {value}.",
        ]
    else:
        k = {3: 2, 4: 1, 5: 3}[d]
        if k == 1:
            prompt = "(n + 1)!/n!"
            answer = "n + 1"
            steps = [
                "(n + 1)! = (n + 1) * n!, so the n! cancels.",
                "= n + 1.",
            ]
        else:
            prompt = f"n!/(n - {k})!"
            answer = "n(n-1)" if k == 2 else "n(n-1)(n-2)"
            steps = [
                f"n! = n(n-1)...(n-{k}+1) * (n-{k})!, so (n-{k})! cancels.",
                f"= {answer}.",
            ]
    hint = "Expand only as far as needed: n!/(n-k)! is the product of the k factors n, n-1, ..."
    return make_problem(
        "factorial_simplify", d, prompt, answer, "expr", hint, tuple(steps),
        crosscheck_prompt=numeric,  # symbolic factorials can't be evaluated
    )


def _binom_eval(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    if d == 1:
        n, k = ri(rng, 4, 7), ri(rng, 1, 3)
        prompt = f"C({n},{k})"
        answer = str(math.comb(n, k))
        steps = [
            f"C({n},{k}) = {n}!/({k}!({n - k})!).",
            f"= {n}*{n - 1}*... down {k} factors divided by {k}! = {answer}.",
        ]
    elif d == 2:
        n, k = ri(rng, 6, 9), ri(rng, 2, 4)
        prompt = f"C({n},{k})"
        answer = str(math.comb(n, k))
        steps = [
            f"C({n},{k}) = {n}!/({k}!({n - k})!) = {answer}.",
            "Tip: cancel (n-k)! from the top before computing.",
        ]
    elif d == 3:
        n = ri(rng, 8, 12)
        k = n - ri(rng, 1, 3)  # symmetry trap: large k
        prompt = f"C({n},{k})"
        answer = str(math.comb(n, k))
        steps = [
            f"Large k? Use symmetry C(n,k) = C(n,n-k): C({n},{k}) = C({n},{n - k}).",
            f"C({n},{n - k}) = {answer}.",
        ]
    elif d == 4:
        n = ri(rng, 5, 8)
        k = ri(rng, 1, n - 2)
        prompt = f"C({n},{k}) + C({n},{k + 1})"
        answer = str(math.comb(n + 1, k + 1))
        steps = [
            f"Pascal's identity: C(n,k) + C(n,k+1) = C(n+1,k+1).",
            f"So this equals C({n + 1},{k + 1}) = {answer}.",
        ]
    else:
        c = math.comb(ri(rng, 5, 8), 2)
        prompt = f"solve C(n,2) = {c} for the positive integer n"
        n = 0
        for i in range(4, 30):
            if math.comb(i, 2) == c:
                n = i
        answer = str(n)
        steps = [
            f"C(n,2) = n(n-1)/2, so n(n-1) = {2 * c}.",
            f"Solve n^2 - n - {2 * c} = 0: factors to (n - {n})(n + {n - 1}) = 0.",
            f"Positive root: n = {n}.",
        ]
    hint = "C(n,k)=n!/(k!(n-k)!); use symmetry for big k and Pascal's identity for sums."
    return make_problem("binom_eval", d, prompt, answer, "expr", hint, tuple(steps))


def _solve_counting(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    if d <= 2:
        n = ri(rng, 5, 12)
        prompt = f"solve n^2 = {n * n} for the positive n"
        answer = str(n)
        steps = [f"n = sqrt({n * n}) = {n} (take the positive root)."]
    elif d == 3:
        n = ri(rng, 5, 12)
        prompt = f"solve n(n - 1) = {n * (n - 1)} for the positive n"
        answer = str(n)
        steps = [
            f"Expand: n^2 - n - {n * (n - 1)} = 0.",
            f"Factor: (n - {n})(n + {n - 1}) = 0.",
            f"Positive root: n = {n}.",
        ]
    elif d == 4:
        n = ri(rng, 4, 9)
        prompt = f"solve n(n - 1)(n - 2) = {n * (n - 1) * (n - 2)} for the positive n"
        answer = str(n)
        steps = [
            "This is n!/(n-3)! = P(n,3): consecutive factors multiply to the target.",
            f"{n} * {n - 1} * {n - 2} = {n * (n - 1) * (n - 2)}, so n = {n}.",
            "(Check nearby candidates to be sure you found the right one.)",
        ]
    else:
        n = ri(rng, 6, 10)
        k = ri(rng, 2, n // 2)
        target = math.comb(n, k)
        prompt = f"solve C(n,{k}) = {target} for the positive integer n"
        answer = str(n)
        steps = [
            f"Try n near {n}: C({n},{k}) = {target}.",
            f"C({n - 1},{k}) and C({n + 1},{k}) miss the target, so n = {n}.",
        ]
    hint = "Set up the product, then factor (quadratic) or hunt consecutive factors."
    return make_problem("solve_counting", d, prompt, answer, "expr", hint, tuple(steps))


TOPICS: tuple[Topic, ...] = (
    Topic("factorial_simplify", "Factorial simplification", TRACK,
          "n!/(n-k)! style expressions", _factorial_simplify),
    Topic("binom_eval", "Binomial coefficient identities", TRACK,
          "C(n,k), symmetry, Pascal's identity", _binom_eval),
    Topic("solve_counting", "Solve counting equations", TRACK,
          "n(n-1)=56-style setups", _solve_counting),
)
