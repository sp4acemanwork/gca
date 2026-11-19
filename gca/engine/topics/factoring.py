"""Factor: GCF, difference of squares, trinomials, cubes, grouping,
quadratic-in-disguise."""

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
    signed_monomial,
    sign_prefix,
    sum_str,
    xbinom,
)

TRACK = "Factor"


def _factor_gcf(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    n_terms = 2 if d <= 2 else 3
    g = {1: ri(rng, 2, 6), 2: ri(rng, 2, 9), 3: ri(rng, 2, 9),
         4: ri(rng, 2, 12), 5: ri(rng, 3, 12)}[d]
    g_var = True  # GCF problems without an x factor are degenerate; always include one
    g_exp = ri(rng, 1, 2)
    exps: list[int] = []
    while len(exps) < n_terms:
        e = ri(rng, g_exp, g_exp + 3)
        if e not in exps:
            exps.append(e)
    exps.sort(reverse=True)
    inner: list[int] = []
    while len(set(inner)) < n_terms or any(v == 0 for v in inner):
        inner = [nz(rng, -9, 9) for _ in range(n_terms)]
    terms = [(g * inner[i], "x", e) for i, e in enumerate(exps)]
    prompt = sum_str(terms)
    gcf = coef_str(g, "x" if g_var else "", g_exp)
    inner_str = sum_str([(inner[i], "x", e - g_exp) for i, e in enumerate(exps)])
    answer = f"{gcf}({inner_str})"
    steps = [
        f"GCF of the coefficients is {g}"
        + (f"; lowest power of x present is x^{g_exp}" if g_var else "")
        + f", so the GCF is {gcf}.",
        f"Dividing each term by {gcf} leaves {inner_str}.",
        f"Check by distributing {gcf} back through: you get the original.",
        f"= {answer}",
    ]
    hint = "Pull out the GCF of the coefficients and the lowest power of the variable."
    return make_problem("factor_gcf", d, prompt, answer, "factored", hint, tuple(steps))


def _factor_ds(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    wrap = d >= 3 and rng.random() < 0.5
    two_var = not wrap and d >= 4 and rng.random() < 0.4
    if wrap:
        k = ri(rng, 2, 4)
        a, b = ri(rng, 2, 7), ri(rng, 2, 7)
        prompt = f"{coef_str(k * a * a, 'x', 2)} - {k * b * b}"
        answer = f"{k}({mono(a, 'x')} + {b})({mono(a, 'x')} - {b})"
        steps = [
            f"GCF first: {k}({coef_str(a * a, 'x', 2)} - {b * b}).",
            f"Inside, {coef_str(a * a, 'x', 2)} = ({mono(a, 'x')})^2 and {b * b} = {b}^2 - a difference of squares.",
            f"A^2 - B^2 = (A + B)(A - B), so the answer is {answer}.",
        ]
    elif two_var:
        a, b = ri(rng, 2, 7), ri(rng, 2, 7)
        prompt = f"x^{2 * a} - {b * b}y^2"
        answer = f"(x^{a} + {b}y)(x^{a} - {b}y)"
        steps = [
            f"This is (x^{a})^2 - ({b}y)^2.",
            f"A^2 - B^2 = (A + B)(A - B) with A = x^{a}, B = {b}y.",
            f"= {answer}.",
        ]
    else:
        a, b = ri(rng, 1, 9), ri(rng, 1, 9)
        prompt = f"{coef_str(a * a, 'x', 2)} - {b * b}"
        answer = f"({mono(a, 'x')} + {b})({mono(a, 'x')} - {b})"
        steps = [
            f"{coef_str(a * a, 'x', 2)} = ({mono(a, 'x')})^2 and {b * b} = {b}^2.",
            "Difference of squares: A^2 - B^2 = (A + B)(A - B).",
            f"= {answer}.",
        ]
    hint = "Spot A^2 - B^2 = (A+B)(A-B). Pull out a GCF first if there is one."
    return make_problem("factor_ds", d, prompt, answer, "factored", hint, tuple(steps))


def _factor_trinomial(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    if d >= 4:
        a, c = nz(rng, 1, 4), nz(rng, -5, 5)
        b, e = nz(rng, -6, 6), nz(rng, -6, 6)
        A, B, C = a * c, a * e + b * c, b * e
        prompt = sum_str([(A, "x", 2), (B, "x", 1), (C, "", 0)])
        wrap = d == 5 and rng.random() < 0.4
        if wrap:
            k = ri(rng, 2, 3)
            prompt = sum_str([(k * A, "x", 2), (k * B, "x", 1), (k * C, "", 0)])
            answer = f"{k}{xbinom(a, b)}{xbinom(c, e)}"
            steps = [
                f"GCF {k} out first: {k}({sum_str([(A, 'x', 2), (B, 'x', 1), (C, '', 0)])}).",
                f"AC method on the inside: a*c = {A}; two numbers with product "
                f"{A * C} and sum {B} are {b * c} and {a * e}.",
                f"Split the middle term {signed_monomial(B)} = {mono(b * c, 'x')} {sign_prefix(a * e)}, group.",
                f"= {k}({mono(a, 'x')}{signed_monomial(b)})({mono(c, 'x')}{signed_monomial(e)}).",
            ]
        else:
            answer = f"{xbinom(a, b)}{xbinom(c, e)}"
            steps = [
                f"AC method: a*c = {A}; two numbers with product {A * C} and "
                f"sum {B} are {b * c} and {a * e}.",
                f"Split the middle term into {mono(b * c, 'x')} {sign_prefix(a * e)} "
                f"and group.",
                f"= ({mono(a, 'x')}{signed_monomial(b)})({mono(c, 'x')}{signed_monomial(e)}).",
            ]
    else:
        p, q = ri(rng, 1, 9), nz(rng, -9, 9)
        if d == 1:
            q = abs(q)
        B, C = p + q, p * q
        prompt = sum_str([(1, "x", 2), (B, "x", 1), (C, "", 0)])
        answer = f"{xbinom(1, p)}{xbinom(1, q)}"
        steps = [
            f"Find two numbers with product {C} and sum {B}: {p} and {q}.",
            f"Then {prompt} = {xbinom(1, p)}{xbinom(1, q)}.",
        ]
    hint = "x^2+Bx+C: two numbers with product C, sum B. ax^2+Bx+C: AC method."
    return make_problem("factor_trinomial", d, prompt, answer, "factored", hint, tuple(steps))


def _factor_cubes(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    plus = rng.random() < 0.5
    sign_b = sign_prefix(1) if plus else sign_prefix(-1)  # sign on the B term
    cross = -1 if plus else 1  # opposite sign on the AB cross term
    two_var = d >= 3 and rng.random() < 0.3
    wrap = not two_var and d >= 4 and rng.random() < 0.5
    b = ri(rng, 1, 4) if d >= 2 else ri(rng, 1, 2)
    if two_var:
        a_exp = 2 if d >= 4 else 1
        prompt = f"x^{3 * a_exp} {sign_prefix(b**3) if plus else sign_prefix(-(b**3))}y^3"
        cross_y = -b if plus else b
        answer = (
            f"(x^{a_exp}{signed_monomial(b if plus else -b, 'y')})"
            f"(x^{2 * a_exp}{signed_monomial(cross_y, f'x^{a_exp}y')} {sign_prefix(b * b)}y^2)"
        )
        steps = [
            f"A^3 {'+' if plus else '-'} B^3 = (A {'+' if plus else '-'} B)(A^2 {'-' if plus else '+'} AB + B^2).",
            f"Here A^3 = x^{3 * a_exp} and B^3 = y^3, so A = x^{a_exp}, B = y.",
            f"= {answer}.",
        ]
    elif wrap:
        a = ri(rng, 1, 3)
        m = ri(rng, 1, 3)
        b = a * m
        prompt = f"{coef_str(a**3, 'x', 3)} {sign_prefix(b**3) if plus else sign_prefix(-(b**3))}"
        cross_m = -m if plus else m
        answer = (
            f"{a**3}(x {sign_prefix(m) if plus else sign_prefix(-m)})"
            f"(x^2{signed_monomial(cross_m, 'x')} {sign_prefix(m * m)})"
        )
        steps = [
            f"GCF first: both coefficients share {a**3}: {a**3}(x^3 {sign_prefix(m**3) if plus else sign_prefix(-(m**3))}).",
            f"Then A^3 {'+' if plus else '-'} B^3 = (A {'+' if plus else '-'} B)(A^2 {'-' if plus else '+'} AB + B^2) with A = x, B = {m}.",
            f"= {answer}.",
        ]
    else:
        prompt = f"x^3 {sign_prefix(b**3) if plus else sign_prefix(-(b**3))}"
        cross_b = -b if plus else b
        answer = (
            f"(x {sign_prefix(b) if plus else sign_prefix(-b)})"
            f"(x^2{signed_monomial(cross_b, 'x')} {sign_prefix(b * b)})"
        )
        steps = [
            f"{b**3} = {b}^3, so A = x, B = {b}.",
            f"A^3 {'+' if plus else '-'} B^3 = (A {'+' if plus else '-'} B)(A^2 {'-' if plus else '+'} AB + B^2).",
            f"The trinomial's AB term sign is opposite the binomial sign.",
            f"= {answer}.",
        ]
    hint = "A^3+B^3 = (A+B)(A^2-AB+B^2); A^3-B^3 = (A-B)(A^2+AB+B^2). Sign flips, squares stay positive."
    return make_problem("factor_cubes", d, prompt, answer, "factored", hint, tuple(steps))


def _factor_grouping(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    while True:
        k = ri(rng, 2, 3) if d >= 4 else 1
        p, q = nz(rng, -4, 4), nz(rng, -5, 5)  # binomial (px + q)
        a, b = nz(rng, 1, 5), nz(rng, -5, 5)  # quadratic binomial (ax^2 + b)
        # (px + q)(ax^2 + b) = pa x^3 + qa x^2 + pb x + qb
        A, B, C, D = (k * p * a, k * q * a, k * p * b, k * q * b)
        if B != 0 and C != 0 and D != 0 and A != C:
            break
    prompt = sum_str([(A, "x", 3), (B, "x", 2), (C, "x", 1), (D, "", 0)])
    prefix = f"{k}" if k != 1 else ""
    quad = f"({mono(a, 'x^2')} {sign_prefix(b)})"
    answer = f"{prefix}{xbinom(p, q)}{quad}"
    inner = sum_str([(A // k, "x", 3), (B // k, "x", 2), (C // k, "x", 1), (D // k, "", 0)])
    if k != 1:
        steps = [
            f"GCF {k} out first: {k}({inner}).",
            f"Group the inside: ({sum_str([(A // k, 'x', 3), (B // k, 'x', 2)])}) + ({sum_str([(C // k, 'x', 1), (D // k, '', 0)])}).",
            f"Factor each pair: {mono(a, 'x^2')}{xbinom(p, q)} and {mono(b, 'x')}{xbinom(p, q)} - both contain {xbinom(p, q)}.",
            f"= {answer}.",
        ]
    else:
        steps = [
            f"Group: ({sum_str([(A, 'x', 3), (B, 'x', 2)])}) + ({sum_str([(C, 'x', 1), (D, '', 0)])}).",
            f"Factor each pair: {mono(a, 'x^2')}{xbinom(p, q)} and {mono(b, 'x')}{xbinom(p, q)} - both contain {xbinom(p, q)}.",
            f"Pull it out: {answer}.",
        ]
    hint = "Group 4 terms into two pairs, factor each pair, pull out the shared binomial."
    return make_problem("factor_grouping", d, prompt, answer, "factored", hint, tuple(steps))


def _factor_quadform(rng: random.Random, difficulty: int) -> Problem:
    d = max(1, min(5, difficulty))
    double = d >= 4 and rng.random() < 0.4
    if double:
        t = ri(rng, 1, 6)
        prompt = f"x^4 - {t**4}"
        answer = f"(x^2 + {t * t})(x + {t})(x - {t})"
        steps = [
            f"Difference of squares: x^4 - {t**4} = (x^2 + {t * t})(x^2 - {t * t}).",
            f"x^2 - {t * t} factors AGAIN: (x + {t})(x - {t}).",
            f"= {answer}.",
        ]
    elif d <= 3:
        p, q = nz(rng, 1, 4), nz(rng, 1, 5)
        B, C = p + q, p * q
        prompt = f"x^4 {sign_prefix(B)}x^2 {sign_prefix(C)}"
        answer = f"(x^2 + {p})(x^2 + {q})"
        steps = [
            "Let u = x^2: the problem becomes u^2 " + f"{sign_prefix(B)}u {sign_prefix(C)}.",
            f"Two numbers with product {C}, sum {B}: {p} and {q}.",
            f"(u + {p})(u + {q}), then u = x^2: {answer}.",
        ]
    else:
        lead = ri(rng, 2, 4)
        c, e = nz(rng, 1, 4), nz(rng, 1, 4)
        p, q = nz(rng, 1, 4), nz(rng, 1, 4)
        A = lead * c * e
        B = lead * (c * q + e * p)
        C = lead * p * q
        prompt = sum_str([(A, "x", 4), (B, "x", 2), (C, "", 0)])
        answer = (f"({coef_str(lead * c, 'x', 2)} {sign_prefix(lead * p)})"
                  f"({coef_str(e, 'x', 2)} {sign_prefix(q)})")
        steps = [
            "Let u = x^2: this is a quadratic in u with leading coefficient "
            f"{A}: {sum_str([(A, 'u', 2), (B, 'u', 1), (C, '', 0)])}.",
            f"AC method on u, then substitute u = x^2.",
            f"= {answer}.",
        ]
    hint = "Substitute u = x^2, factor the quadratic in u, substitute back. Check for a second factoring!"
    return make_problem("factor_quadform", d, prompt, answer, "factored", hint, tuple(steps))


TOPICS: tuple[Topic, ...] = (
    Topic("factor_gcf", "Factor out GCF", TRACK,
          "Pull out the greatest common factor", _factor_gcf),
    Topic("factor_ds", "Difference of squares", TRACK,
          "A^2 - B^2 factoring, incl. GCF-first and two-variable", _factor_ds),
    Topic("factor_trinomial", "Factor trinomials", TRACK,
          "x^2+Bx+C and ax^2+Bx+C", _factor_trinomial),
    Topic("factor_cubes", "Sum/difference of cubes", TRACK,
          "Cubic factoring incl. GCF-first and two-variable", _factor_cubes),
    Topic("factor_grouping", "Factor by grouping", TRACK,
          "Four-term grouping", _factor_grouping),
    Topic("factor_quadform", "Quadratic in disguise", TRACK,
          "x^4 + Bx^2 + C forms and double factoring", _factor_quadform),
)
