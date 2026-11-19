"""Exponents: product/quotient/power rules, zero & negative exponents,
rational exponents on numeric bases."""

from __future__ import annotations

import random
from fractions import Fraction

from gca.engine.generate import Problem, Topic, make_problem, ri

TRACK = "Exponents"


def _exp_rules(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    exp_lo, exp_hi = (1, 4) if d <= 2 else (1, 7 if d >= 4 else 6)
    form = rng.choice(
        {
            1: ["product"],
            2: ["product", "quotient", "power"],
            3: ["product", "quotient", "power", "combo"],
            4: ["quotient", "power", "combo", "negative"],
            5: ["combo", "negative", "rational"],
        }[d]
    )
    var = rng.choice(["x", "n", "a"])
    a, b, c = ri(rng, exp_lo, exp_hi), ri(rng, exp_lo, exp_hi), ri(rng, 2, 5 if d < 4 else 9)
    if form == "product":
        prompt = f"{var}^{a} * {var}^{b}"
        answer = f"{var}^{a + b}"
        steps = [
            f"Product rule: same base multiplied -> add exponents.",
            f"{var}^{a} * {var}^{b} = {var}^({a}+{b}) = {answer}.",
        ]
    elif form == "quotient":
        hi, lo = max(a, b), min(a, b)
        prompt = f"{var}^{hi} / {var}^{lo}"
        if d >= 4 and rng.random() < 0.5:
            prompt = f"{var}^{lo} / {var}^{hi}"
            answer = f"{var}^{lo - hi}" if d == 4 else f"1/{var}^{hi - lo}"
            steps = [
                "Quotient rule: same base divided -> subtract exponents.",
                f"{var}^({lo}-{hi}) = {answer} (a negative exponent means reciprocal).",
            ]
        else:
            answer = f"{var}^{hi - lo}"
            steps = [
                "Quotient rule: same base divided -> subtract exponents.",
                f"{var}^({hi}-{lo}) = {answer}.",
            ]
    elif form == "power":
        prompt = f"({var}^{a})^{b}"
        answer = f"{var}^{a * b}"
        steps = [
            "Power of a power -> multiply exponents.",
            f"({var}^{a})^{b} = {var}^({a}*{b}) = {answer}.",
        ]
    elif form == "combo":
        prompt = f"({c}{var}^{a})^{2}"
        answer = f"{c * c}{var}^{2 * a}"
        steps = [
            "The power hits the coefficient too: (c x^a)^2 = c^2 x^(2a).",
            f"= {c * c}{var}^{2 * a}.",
        ]
    elif form == "negative":
        prompt = f"{c}{var}^{-a}"
        answer = f"{c}/({var}^{a})"
        steps = [
            f"Negative exponent = reciprocal: {c}{var}^{-a} = {c}/{var}^{a}.",
            f"= {answer}.",
        ]
    else:  # rational exponent on a numeric base
        root = rng.choice([2, 3])
        base = rng.choice([4, 8, 9, 16, 25, 27, 32, 64, 125])
        p = ri(rng, 1, 2)
        r = round(base ** (1 / root))
        if r**root != base:
            return _exp_rules(rng, d)  # keep answers whole; retry
        value = Fraction(r) ** p
        prompt = f"{base}^({p}/{root})"
        answer = str(value)
        steps = [
            f"{base}^({p}/{root}) means take the {root}-th root first, then the power: "
            f"({root}-th root of {base})^{p}.",
            f"Root {root} of {base} = {r}, then ^{p} = {value}.",
        ]
    hint = "Same base multiply -> add exponents; divide -> subtract; power of power -> multiply."
    return make_problem("exp_rules", d, prompt, answer, "expr", hint, tuple(steps))


TOPICS: tuple[Topic, ...] = (
    Topic("exp_rules", "Exponent rules", TRACK,
          "Product/quotient/power rules, negatives, rational exponents", _exp_rules),
)
