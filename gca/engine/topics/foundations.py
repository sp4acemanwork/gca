"""Foundations: integer arithmetic, fractions, signed-power traps."""

from __future__ import annotations

import math
import random
from fractions import Fraction

from gca.engine.generate import Problem, Topic, make_problem, nz, ri

TRACK = "Foundations"


def _frac_arith(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    top = {1: 9, 2: 12, 3: 15, 4: 24, 5: 40}[d]
    style = rng.choice(
        {
            1: ["add", "sub"],
            2: ["add", "sub", "mul"],
            3: ["add", "sub", "mul", "div"],
            4: ["add", "sub", "mul", "div"],
            5: ["add", "sub", "mul", "div", "compound"],
        }[d]
    )
    a = Fraction(ri(rng, 1, top), ri(rng, 2, top))
    b = Fraction(ri(rng, 1, top), ri(rng, 2, top))
    steps: list[str]
    if style == "add":
        prompt = f"{a} + {b}"
        value = a + b
        lcd = math.lcm(a.denominator, b.denominator)
        steps = [
            f"LCD of {a.denominator} and {b.denominator} is {lcd}: "
            f"{a} = {a.numerator * lcd // a.denominator}/{lcd}, "
            f"{b} = {b.numerator * lcd // b.denominator}/{lcd}.",
            f"Add numerators: {value.numerator}/{lcd} = {value}.",
        ]
    elif style == "sub":
        prompt = f"{a} - {b}"
        value = a - b
        lcd = math.lcm(a.denominator, b.denominator)
        steps = [
            f"LCD of {a.denominator} and {b.denominator} is {lcd}: "
            f"{a} = {a.numerator * lcd // a.denominator}/{lcd}, "
            f"{b} = {b.numerator * lcd // b.denominator}/{lcd}.",
            f"Subtract numerators: {value.numerator}/{lcd} = {value}.",
        ]
    elif style == "mul":
        prompt = f"{a} * {b}"
        value = a * b
        steps = [
            f"Multiply straight across: {a.numerator}*{b.numerator} over "
            f"{a.denominator}*{b.denominator} = {value.numerator}/{value.denominator}.",
            f"Reduce: {value}.",
        ]
    elif style == "div":
        prompt = f"({a}) / ({b})"
        value = a / b
        steps = [
            f"Dividing by {b} multiplies by its reciprocal {b.denominator}/{b.numerator}.",
            f"= {value}.",
        ]
    else:
        c = Fraction(ri(rng, 1, top), ri(rng, 2, top))
        prompt = f"({a} + {b}) / ({c})"
        value = (a + b) / c
        inner = a + b
        steps = [
            f"Parentheses first: {a} + {b} = {inner}.",
            f"Then divide: {inner} * {c.denominator}/{c.numerator} = {value}.",
        ]
    hint = "Never round - LCD for +/-, multiply across for x, flip for /."
    return make_problem(
        "fraction_arith", d, prompt, str(value), "expr", hint, tuple(steps)
    )


def _int_arith(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    steps: list[str]
    if d == 1:
        a, b = ri(rng, -20, 20), ri(rng, -20, 20)
        op = rng.choice("+-")
        prompt = f"{a} {op} {b}"
        value = a + b if op == "+" else a - b
        steps = [f"{a} {op} {b} = {value}. Remember: subtracting a negative adds."]
    elif d == 2:
        a, b = ri(rng, -12, 12), ri(rng, -12, 12)
        op = rng.choice("*+")
        prompt = f"{a} {op} {b}"
        value = a * b if op == "*" else a + b
        steps = [f"{a} {op} {b} = {value}."]
    elif d == 3:
        a, b, c = ri(rng, -12, 12), ri(rng, -12, 12), ri(rng, -10, 10)
        prompt = f"{a} * {b} + {c}"
        value = a * b + c
        steps = [
            "Multiplication before addition (order of operations).",
            f"{a} * {b} = {a * b}, then {a * b} + {c} = {value}.",
        ]
    elif d == 4:
        a, b, c = ri(rng, -9, 9), ri(rng, -9, 9), ri(rng, -9, 9)
        prompt = f"({a} + {b}) * {c}"
        value = (a + b) * c
        steps = [
            f"Parentheses first: {a} + {b} = {a + b}.",
            f"Then ({a + b}) * {c} = {value}.",
        ]
    else:
        a, b, c = ri(rng, 12, 25), ri(rng, 3, 9), ri(rng, 5, 20)
        prompt = f"{a * b} / {b} - {c}"
        value = a - c
        steps = [
            "Division before subtraction.",
            f"{a * b} / {b} = {a}, then {a} - {c} = {value}.",
        ]
    hint = "Order of operations: ( ) then * / then + -. Watch double signs."
    return make_problem(
        "int_arith", d, prompt, str(value), "expr", hint, tuple(steps)
    )


def _signed_powers(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    base = nz(rng, -9, 9) if d < 3 else nz(rng, -12, 12)
    exp = {1: 2, 2: rng.choice([2, 3]), 3: rng.choice([2, 3]),
           4: rng.choice([2, 3, 4]), 5: rng.choice([3, 4])}[d]
    form = rng.choice(
        {
            1: ["paren", "noparen"],
            2: ["paren", "noparen", "prefix"],
            3: ["paren", "prefix", "double"],
            4: ["paren", "prefix", "double"],
            5: ["paren", "double", "triple"],
        }[d]
    )
    if form == "paren":
        prompt = f"({base})^{exp}"
        value = base**exp
        steps = [
            f"({base})^{exp} means {base} multiplied by itself {exp} times.",
            f"= {value}.",
        ]
    elif form == "noparen":
        prompt = f"-{abs(base)}^{exp}"
        value = -(abs(base) ** exp)
        steps = [
            f"-{abs(base)}^{exp} = -({abs(base)}^{exp}): the power applies first, then the minus.",
            f"{abs(base)}^{exp} = {abs(base) ** exp}, so the value is {value}.",
        ]
    elif form == "prefix":
        prompt = f"-({base})^{exp}"
        value = -(base**exp)
        steps = [f"Compute ({base})^{exp} = {base**exp}, then negate: {value}."]
    elif form == "double":
        a, b = nz(rng, -6, 6), nz(rng, -6, 6)
        prompt = f"({a})^2 * ({b})^2"
        value = a**2 * b**2
        steps = [
            f"({a})^2 = {a**2} and ({b})^2 = {b**2}.",
            f"Product: {value}.",
        ]
    else:
        a, b = nz(rng, -5, 5), nz(rng, -5, 5)
        prompt = f"({a})^3 - ({b})^3"
        value = a**3 - b**3
        steps = [
            f"({a})^3 = {a**3} and ({b})^3 = {b**3}.",
            f"Difference: {value}.",
        ]
    hint = "-3^2 = -9 but (-3)^2 = 9: the exponent grabs only what it touches."
    return make_problem(
        "signed_powers", d, prompt, str(value), "expr", hint, tuple(steps)
    )


TOPICS: tuple[Topic, ...] = (
    Topic("int_arith", "Integer arithmetic", TRACK,
          "Signed +, -, x, / with order-of-operations practice", _int_arith),
    Topic("fraction_arith", "Fraction arithmetic", TRACK,
          "Exact fraction + - x / with reducing", _frac_arith),
    Topic("signed_powers", "Signed power traps", TRACK,
          "-3^2 vs (-3)^2 and friends", _signed_powers),
)
