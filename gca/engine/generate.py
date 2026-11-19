"""Problem generation registry.

Each topic owns a generator function ``gen(rng, difficulty) -> Problem``.
Difficulty runs 1..5; generators clamp internally if a topic's designed
range is narrower.  Every authored answer string is validated against
itself at creation time so a broken generator fails loudly in tests,
not in a practice session.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from dataclasses import dataclass

from gca.engine.grade import GradeResult, check
from gca.engine.parser import MathSyntaxError, parse

_DOUBLE_SPACE: re.Pattern[str] = re.compile(r"  +")


def tidy(s: str) -> str:
    """Collapse accidental double spaces from template concatenation."""
    return _DOUBLE_SPACE.sub(" ", s.strip())


@dataclass(frozen=True)
class Problem:
    """One practice question with everything needed to teach from a miss."""

    topic: str
    difficulty: int
    prompt: str
    answer: str
    kind: str  # "expr" | "factored" | "set" | "int_list"
    hint: str
    steps: tuple[str, ...]


@dataclass(frozen=True)
class Topic:
    """A drill topic: id, display metadata and its generator."""

    id: str
    title: str
    track: str
    blurb: str
    gen: Callable[[random.Random, int], Problem]


REGISTRY: dict[str, Topic] = {}
TRACK_ORDER: tuple[str, ...] = (
    "Foundations",
    "Exponents",
    "Expand",
    "Factor",
    "Rational expressions",
    "Combinatorics algebra",
    "Word problems",
)


def register(topic: Topic) -> Topic:
    if topic.id in REGISTRY:
        raise ValueError(f"duplicate topic id: {topic.id}")
    REGISTRY[topic.id] = topic
    return topic


def all_topics() -> list[Topic]:
    """Registry entries ordered by track then title."""
    order = {t: i for i, t in enumerate(TRACK_ORDER)}
    return sorted(
        REGISTRY.values(),
        key=lambda t: (order.get(t.track, 99), t.title),
    )


def get_topic(topic_id: str) -> Topic:
    return REGISTRY[topic_id]


def make_problem(
    topic_id: str,
    difficulty: int,
    prompt: str,
    answer: str,
    kind: str,
    hint: str,
    steps: tuple[str, ...],
    crosscheck_prompt: bool = True,
) -> Problem:
    """Build a Problem, validating that the authored answer grades correct.

    For expression prompts the prompt is also cross-checked against the
    answer (they must be equivalent).  Pass ``crosscheck_prompt=False`` for
    word-style or symbolic prompts (e.g. factorials of variables) that the
    evaluator cannot verify.
    """
    real_kind = kind
    selfcheck = check(answer, answer, real_kind)
    if not selfcheck.correct:
        raise ValueError(
            f"generator bug in {topic_id!r} (difficulty {difficulty}): "
            f"answer {answer!r} does not grade correct: {selfcheck.message}"
        )
    if real_kind in ("expr", "factored") and crosscheck_prompt:
        # The prompt must be an equivalent expression to the answer (for
        # factored problems the prompt is the expanded form).  Prompts that
        # are not parseable (word problems, "solve n^2 = 64 ...") are skipped.
        try:
            parse(prompt)
        except MathSyntaxError:
            parse_ok = False
        else:
            parse_ok = True
        cross = check(prompt, answer, "expr") if parse_ok else GradeResult(True, "")
        if not cross.correct:
            raise ValueError(
                f"generator bug in {topic_id!r} (difficulty {difficulty}): "
                f"prompt {prompt!r} and answer {answer!r} disagree: {cross.message}"
            )
    return Problem(
        topic=topic_id,
        difficulty=difficulty,
        prompt=tidy(prompt),
        answer=tidy(answer),
        kind=real_kind,
        hint=tidy(hint),
        steps=tuple(tidy(s) for s in steps),
    )


# --------------------------------------------------------------------- #
# Shared random/formatting helpers for generators
# --------------------------------------------------------------------- #


def sum_str(terms: list[tuple[int, str, int]]) -> str:
    """Format a polynomial sum like ``3x^2 - x + 4`` from (coef, var, exp)."""
    combined: dict[int, int] = {}
    var = terms[0][1] if terms else "x"
    for c, _, e in terms:
        combined[e] = combined.get(e, 0) + c
    out = ""
    for e in sorted(combined, reverse=True):
        c = combined[e]
        if c == 0:
            continue
        s = coef_str(abs(c), var, e)
        out = (("-" + s) if c < 0 else s) if not out else (out + (f" + {s}" if c > 0 else f" - {s}"))
    return out or "0"




def ri(rng: random.Random, lo: int, hi: int) -> int:
    """Random integer in [lo, hi]."""
    return rng.randint(lo, hi)


def nz(rng: random.Random, lo: int, hi: int) -> int:
    """Random nonzero integer in [lo, hi]."""
    return rng.choice([v for v in range(lo, hi + 1) if v != 0])


def sign_prefix(c: int) -> str:
    """Format ``c`` as ``" + c"`` / ``" - |c|"`` for building expressions."""
    return f" + {c}" if c >= 0 else f" - {-c}"


def mono(c: int, var: str = "x") -> str:
    """Format a signed monomial attached to ``var``: ``3x``, ``-x``, ``x``.

    ``var`` may already include its own exponent, e.g. ``"x^2y"``.
    """
    if c == 1 and var:
        return var
    if c == -1 and var:
        return f"-{var}"
    return f"{c}{var}"


def signed_monomial(c: int, var: str = "x") -> str:
    """Format ``c`` as ``" + x"`` / ``" - 2x"`` (coefficient 1 elided).

    ``var`` may itself carry an exponent, e.g. ``"x^2y"``.
    """
    if not var:
        return sign_prefix(c)
    sign = " + " if c >= 0 else " - "
    return sign + mono(abs(c), var)


def xbinom(a: int, b: int) -> str:
    """Format a linear binomial like ``(x - 3)`` / ``(3x + 2)`` / ``(-x + 4)``."""
    return f"({mono(a, 'x')} {sign_prefix(b)})"


def coef_str(c: int, var: str = "", exp: int = 0) -> str:
    """Format one monomial like ``3x^2``, ``-x``, ``7``.

    Coefficient 1/-1 is elided when a variable follows.
    """
    body = (f"{var}^{exp}" if exp != 1 else var) if var and exp else ""
    if c == 1 and body:
        return body
    if c == -1 and body:
        return f"-{body}"
    return f"{c}{body}"


def poly_str(terms: list[tuple[int, str, int]], var_default: str = "x") -> str:
    """Format a sum of (coef, var, exp) monomials, highest degree first-ish.

    Assumes terms are already ordered as the author wants them displayed.
    """
    pieces: list[str] = []
    for c, var, exp in terms:
        s = coef_str(abs(c), var, exp)
        if not pieces:
            pieces.append(("-" if c < 0 else "") + s)
        else:
            pieces.append((" + " if c > 0 else " - ") + s)
    if not pieces:
        return "0"
    return "".join(pieces)
