"""Expand: distributing, FOIL, special squares, binomial theorem."""

from __future__ import annotations

import math
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
)

TRACK = "Expand"


def _fmt_terms(terms: list[tuple[int, str, int]]) -> str:
    pieces: list[str] = []
    for c, var, exp in terms:
        if c == 0:
            continue
        s = coef_str(abs(c), var, exp)
        if not pieces:
            pieces.append(("-" if c < 0 else "") + s)
        else:
            pieces.append((" + " if c > 0 else " - ") + s)
    return "".join(pieces) if pieces else "0"


def _distribute(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    form = rng.choice(
        {
            1: ["mono_bi"],
            2: ["mono_bi", "bi_bi"],
            3: ["bi_bi", "foil_full"],
            4: ["foil_full", "special"],
            5: ["foil_full", "special", "cubic_bi"],
        }[d]
    )
    if form == "mono_bi":
        a, b, c = nz(rng, -9, 9), ri(rng, 1, 9), nz(rng, -9, 9)
        prompt = f"{mono(a, 'x')}({mono(b, 'x')}{sign_prefix(c)})"
        terms = [(a * b, "x", 2), (a * c, "x", 1)]
        steps = [
            f"Distribute {mono(a, 'x')} to both terms: {mono(a, 'x')} * {mono(b, 'x')} = {coef_str(a * b, 'x', 2)} "
            f"and {mono(a, 'x')} * {c} = {mono(a * c, 'x')}.",
            f"= {_fmt_terms(terms)}.",
        ]
    elif form == "bi_bi":
        b, c = ri(rng, 1, 9), nz(rng, -9, 9)
        prompt = f"(x + {b})(x {sign_prefix(c)})"
        terms = [(1, "x", 2), (b + c, "x", 1), (b * c, "", 0)]
        steps = [
            f"FOIL: x*x = x^2, x*({c}) = {mono(c, 'x')}, {b}*x = {mono(b, 'x')}, {b}*({c}) = {b * c}.",
            f"Combine middle terms: {_fmt_terms(terms)}.",
        ]
    elif form == "foil_full":
        a, b, c, e = nz(rng, -5, 5) or 2, nz(rng, -6, 6), nz(rng, -5, 5) or 3, nz(rng, -6, 6)
        prompt = f"({mono(a, 'x')} {sign_prefix(b)})({mono(c, 'x')} {sign_prefix(e)})"
        terms = [(a * c, "x", 2), (a * e + b * c, "x", 1), (b * e, "", 0)]
        steps = [
            f"First: {mono(a, 'x')} * {mono(c, 'x')} = {coef_str(a * c, 'x', 2)}.",
            f"Outer: {mono(a, 'x')} * {e} = {mono(a * e, 'x')}. Inner: {b} * {mono(c, 'x')} = {mono(b * c, 'x')}.",
            f"Last: {b} * {e} = {b * e}. Combine x terms: {_fmt_terms(terms)}.",
        ]
    elif form == "special":
        a, b = nz(rng, -6, 6) or 2, nz(rng, -9, 9)
        kind = rng.choice(["square", "diff"])
        if kind == "square":
            prompt = f"({mono(a, 'x')} {sign_prefix(b)})^2"
            terms = [(a * a, "x", 2), (2 * a * b, "x", 1), (b * b, "", 0)]
            steps = [
                "Perfect square: (px + q)^2 = p^2 x^2 + 2pq x + q^2 - never 'p^2 x^2 + q^2'.",
                f"Middle term: 2 * {a} * {b} = {2 * a * b}.",
                f"= {_fmt_terms(terms)}.",
            ]
        else:
            prompt = f"({mono(a, 'x')} + {b})({mono(a, 'x')} {sign_prefix(-b)})"
            terms = [(a * a, "x", 2), (-(b * b), "", 0)]
            steps = [
                "Difference of squares: (px + q)(px - q) = p^2 x^2 - q^2.",
                f"= {_fmt_terms(terms)}.",
            ]
    else:  # cubic_bi
        a, b = nz(rng, -4, 4) or 2, nz(rng, -5, 5)
        prompt = f"({coef_str(a, 'x', 2)} {sign_prefix(b)})(x + 3)"
        # (ax^2 + b)(x + 3) = ax^3 + 3ax^2 + bx + 3b
        terms = [(a, "x", 3), (3 * a, "x", 2), (b, "x", 1), (3 * b, "", 0)]
        steps = [
            f"Distribute: {coef_str(a, 'x', 2)} * x = {coef_str(a, 'x', 3)}, {coef_str(a, 'x', 2)} * 3 = {coef_str(3 * a, 'x', 2)}, "
            f"{b} * x = {mono(b, 'x')}, {b} * 3 = {3 * b}.",
            f"= {_fmt_terms(terms)}.",
        ]
    hint = "FOIL = First, Outer, Inner, Last. Then combine like terms."
    return make_problem("distribute", d, prompt, _fmt_terms(terms), "expr", hint, tuple(steps))


def _binomial_coeff(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    n = {1: 2, 2: 3, 3: rng.choice([3, 4]), 4: rng.choice([4, 5]), 5: rng.choice([5, 6])}[d]
    two_var = d >= 4 and rng.random() < 0.4
    if two_var:
        n = rng.choice([4, 5, 6])
        k = ri(rng, 1, n - 1)
        prompt = f"coefficient of x^{n - k} y^{k} in (x + y)^{n}"
        answer = str(math.comb(n, k))
        steps = [
            f"Binomial theorem: the x^{n - k} y^{k} term is C({n},{k}) x^{n - k} y^{k}.",
            f"C({n},{k}) = {n}!/({k}!({n - k})!) = {answer}.",
        ]
    else:
        a = nz(rng, -3, 3) or 2
        b = nz(rng, -4, 4)
        k = ri(rng, 0, n)
        prompt = f"coefficient of x^{k} in ({mono(a, 'x')} {sign_prefix(b)})^{n}"
        answer = str(math.comb(n, k) * a**k * b ** (n - k))
        steps = [
            f"The x^{k} term of (px + q)^{n} is C({n},{k}) (px)^{k} q^({n - k}).",
            f"C({n},{k}) = {math.comb(n, k)}, times {a}^{k} * ({b})^{n - k} = "
            f"{a**k} * {b ** (n - k)}.",
            f"= {math.comb(n, k)} * {a**k * b ** (n - k)} = {answer}.",
        ]
    hint = "Term with x^k uses C(n, k) * (first)^(n-k) * (second)^k."
    return make_problem(
        "binomial_coeff", d, prompt, answer, "expr", hint, tuple(steps), crosscheck_prompt=False
    )


def _pascal_row(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    n = {1: 4, 2: 5, 3: 6, 4: 7, 5: rng.choice([8, 9, 10])}[d]
    row = [math.comb(n, k) for k in range(n + 1)]
    prompt = f"list row {n} of Pascal's triangle (all entries, left to right)"
    answer = " ".join(str(v) for v in row)
    steps = [
        f"Row {n} entries are C({n},0), C({n},1), ..., C({n},{n}).",
        "Each entry = (previous entry) * (n - k + 1) / k working left to right.",
        f"= {answer}.",
    ]
    hint = "Row n starts and ends with 1; each entry is C(n, k)."
    return make_problem("pascal_row", d, prompt, answer, "int_list", hint, tuple(steps))


TOPICS: tuple[Topic, ...] = (
    Topic("distribute", "Distribute & FOIL", TRACK,
          "Multiplying out monomials, binomials, special products", _distribute),
    Topic("binomial_coeff", "Binomial theorem", TRACK,
          "Coefficients in (ax+b)^n via C(n,k)", _binomial_coeff),
    Topic("pascal_row", "Pascal's triangle", TRACK,
          "Recall rows of Pascal's triangle", _pascal_row),
)
