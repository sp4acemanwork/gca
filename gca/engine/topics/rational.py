"""Rational expressions: simplify, add/subtract/multiply."""

from __future__ import annotations

import random

from gca.engine.generate import (
    Problem,
    Topic,
    coef_str,
    make_problem,
    mono,
    nz,
    ri,
    sign_prefix,
    sum_str,
    xbinom,
)

TRACK = "Rational expressions"


def _rat_simplify(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    if d <= 2:
        p, q = ri(rng, 1, 8), nz(rng, -8, 8)
        while p + q == 0:
            q = nz(rng, -8, 8)
        top = sum_str([(1, "x", 2), (p + q, "x", 1), (p * q, "", 0)])
        prompt = f"({top})/({xbinom(1, p)})"
        answer = f"{xbinom(1, q)}"
        steps = [
            f"Factor the top: {top} = (x + {p})(x + {q}).",
            f"Cancel the common factor (x + {p}) - valid since x != {-p}.",
            f"= {xbinom(1, q)}.",
        ]
    elif d == 3:
        k = ri(rng, 2, 3)
        p = ri(rng, 1, 6)
        prompt = f"({coef_str(k, 'x', 2)} - {k * p * p})/({xbinom(1, p)})"
        answer = f"{mono(k, 'x')} {sign_prefix(-k * p)}"
        steps = [
            f"Factor top: {coef_str(k, 'x', 2)} - {k * p * p} = {k}(x + {p})(x - {p}).",
            f"Cancel (x + {p}): left with {k}(x - {p}).",
            f"= {mono(k, 'x')} {sign_prefix(-k * p)}.",
        ]
    elif d == 4:
        prompt = "(x^3 + x^2)/(x + 1)"
        answer = "x^2"
        steps = [
            "Factor the top by GCF: x^2(x + 1).",
            "Cancel (x + 1) - valid since x != -1.",
            "= x^2.",
        ]
    else:
        p = ri(rng, 1, 6)
        prompt = (f"({coef_str(1, 'x', 2)} - {p * p})/"
                  f"({coef_str(1, 'x', 2)} {sign_prefix(2 * p)}x {sign_prefix(p * p)})")
        answer = f"{xbinom(1, -p)}/{xbinom(1, p)}"
        steps = [
            f"Factor top: (x + {p})(x - {p}). Factor bottom: (x + {p})^2.",
            f"Cancel one (x + {p}).",
            f"= {xbinom(1, -p)}/{xbinom(1, p)}.",
        ]
    hint = "Factor top and bottom completely, then cancel the common factor (note the excluded value)."
    return make_problem("rat_simplify", d, prompt, answer, "expr", hint, tuple(steps))


def _rat_ops(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    if d == 1:
        a, b = ri(rng, 1, 8), ri(rng, 1, 8)
        prompt = f"{a}/x + {b}/x"
        answer = f"{a + b}/x"
        steps = [
            "Same denominator: add numerators.",
            f"= ({a} + {b})/x = {answer}.",
        ]
    elif d == 2:
        a, b = ri(rng, 1, 6), ri(rng, 1, 6)
        c = nz(rng, 1, 5)
        prompt = f"{a}/x + {b}/(x + {c})"
        answer = f"({coef_str(a + b)}x {sign_prefix(a * c)})/(x(x + {c}))"
        steps = [
            f"LCD is x(x + {c}).",
            f"First fraction -> {a if a != 1 else ''}(x + {c})/LCD; second -> {mono(b, 'x')}/LCD.",
            f"Add numerators: ({a + b})x + {a * c} over x(x + {c}).",
            f"= {answer}.",
        ]
    elif d == 3:
        p = ri(rng, 1, 5)
        prompt = f"(x/(x + {p})) * ((x^2 {sign_prefix(-(p * p))})/x)"
        answer = f"x {sign_prefix(-p)}"
        steps = [
            "Multiply straight across: numerator x(x^2 - p^2), denominator (x + p)x.",
            f"Factor x^2 - p^2 = (x + {p})(x - {p}); cancel everything possible.",
            f"= x - {p}.",
        ]
    elif d == 4:
        a, b = ri(rng, 1, 5), ri(rng, 1, 5)
        prompt = f"{a}/(x - {b}) - {a}/(x + {b})"
        answer = f"{2 * a * b}/(x^2 - {b * b})"
        steps = [
            f"LCD is (x - {b})(x + {b}) = x^2 - {b * b}.",
            f"{a}(x + {b}) - {a}(x - {b}) = {2 * a * b}.",
            f"= {answer}.",
        ]
    else:
        a = ri(rng, 2, 6)
        prompt = f"(x + {a})/x - {a}/x"
        answer = "1"
        steps = [
            "Same denominator: ((x + a) - a)/x = x/x.",
            f"= 1 (x != 0).",
        ]
    hint = "Find the LCD, rewrite each fraction over it, then combine and simplify."
    return make_problem("rat_ops", d, prompt, answer, "expr", hint, tuple(steps))


TOPICS: tuple[Topic, ...] = (
    Topic("rat_simplify", "Simplify rational expressions", TRACK,
          "Factor and cancel", _rat_simplify),
    Topic("rat_ops", "Add/subtract/multiply rationals", TRACK,
          "LCD work and multiplication of rational expressions", _rat_ops),
)
