"""Answer checking: canonical equivalence between expected and typed answers.

Every problem declares an :class:`AnswerKind`:

* ``EXPR``         — the answer is one expression; graded by exact canonical
                     equivalence (``x^2 - 9`` equals ``(x-3)(x+3)``).
* ``FACTORED``     — like ``EXPR`` but the typed answer must also *look*
                     factored (a product of at least two nonconstant factors,
                     or a power of exponent >= 2 of a nonconstant base), so
                     retyping the expanded form doesn't count.
* ``SET``          — a set of numbers separated by commas/``and``; order and
                     duplicates are ignored (used for equation roots).
* ``INT_LIST``     — an ordered (or reversed) list of integers, e.g. Pascal
                     triangle rows; separators may be spaces or commas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from gca.engine.evaluate import MathEvalError, Value, evaluate
from gca.engine.parser import (
    Add,
    Call,
    Div,
    Fact,
    MathSyntaxError,
    Mul,
    Neg,
    Node,
    Num,
    Pow,
    Sub,
    Var,
    parse,
)
from gca.engine.poly import RatFunc
from gca.engine.radicals import Radical

_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r"[\s,;]+|,?\band\b,?", re.IGNORECASE)


@dataclass(frozen=True)
class GradeResult:
    """Outcome of checking a user's answer against the expected one."""

    correct: bool
    message: str  # empty when correct; an explanation when not


def _normalize(value: Value) -> Value:
    if isinstance(value, Radical) and not value.parts:
        return RatFunc.from_number(value.whole)
    return value


def values_equal(a: Value, b: Value) -> bool:
    """Exact equality of two evaluated values."""
    a, b = _normalize(a), _normalize(b)
    if isinstance(a, RatFunc) and isinstance(b, RatFunc):
        return a.equiv(b)
    if isinstance(a, Radical) and isinstance(b, Radical):
        return a.whole == b.whole and a.parts == b.parts
    return False


def _nonconstant(node: Node) -> bool:
    """Best-effort check whether ``node`` evaluates to something with variables."""
    try:
        value = evaluate(node)
    except (MathEvalError, ZeroDivisionError):
        return True
    if isinstance(value, Radical):
        return bool(value.parts)
    return not value.is_number()


def _has_factor_shape(node: Node) -> bool:
    """True if the AST contains a product of two nonconstant factors,
    or a power >= 2 of a nonconstant base — i.e. it "looks factored"."""
    if isinstance(node, Mul):
        if _nonconstant(node.left) and _nonconstant(node.right):
            return True
    if isinstance(node, Pow):
        exp_val: Value | None = None
        try:
            exp_val = evaluate(node.exponent)
        except (MathEvalError, ZeroDivisionError):
            exp_val = None
        if (
            exp_val is not None
            and isinstance(exp_val, RatFunc)
            and exp_val.is_number()
            and exp_val.number().denominator == 1
            and exp_val.number() >= 2
            and _nonconstant(node.base)
            and not isinstance(node.base, Var)  # bare x^2 is just a monomial
        ):
            return True
    for child in _children(node):
        if _has_factor_shape(child):
            return True
    return False


def _children(node: Node) -> tuple[Node, ...]:
    if isinstance(node, (Add, Sub, Mul, Div)):
        return (node.left, node.right)  # type: ignore[return-value]
    if isinstance(node, Pow):
        return (node.base, node.exponent)
    if isinstance(node, Neg):
        return (node.operand,)
    if isinstance(node, Fact):
        return (node.operand,)
    if isinstance(node, Call):
        return node.args
    return ()


def _parse_and_eval(src: str) -> Value:
    """Parse then evaluate; errors carry a friendly message for the user."""
    return evaluate(parse(src))


def _split_set(src: str) -> list[str]:
    parts = [p for p in _SPLIT_RE.split(src.strip()) if p]
    return parts


def _to_number(value: Value) -> Fraction | None:
    if isinstance(value, Radical):
        if value.parts:
            return None
        return value.whole
    if value.is_number():
        return value.number()
    return None


def check(
    expected: str,
    user: str,
    kind: str,
) -> GradeResult:
    """Grade a user's typed answer.

    Args:
        expected: the canonical answer string authored by the generator.
        user: what the user typed.
        kind: one of ``"expr"``, ``"factored"``, ``"set"``, ``"int_list"``.

    Returns:
        A :class:`GradeResult`.  Never raises for user input problems —
        syntax/eval errors are reported as incorrect answers with a hint.
    """
    if not user.strip():
        return GradeResult(False, "Type an answer first.")
    try:
        if kind == "int_list":
            return _check_int_list(expected, user)
        if kind == "set":
            return _check_set(expected, user)
        return _check_expr(expected, user, factored=(kind == "factored"))
    except MathSyntaxError as exc:
        return GradeResult(False, f"Could not read that: {exc}")
    except MathEvalError as exc:
        return GradeResult(False, f"Could not compute that: {exc}")
    except ZeroDivisionError:
        return GradeResult(False, "That has a division by zero in it.")


def _check_expr(expected: str, user: str, *, factored: bool) -> GradeResult:
    user_ast = parse(user)
    user_value = _parse_and_eval(user)
    expected_value = _parse_and_eval(expected)
    if not values_equal(expected_value, user_value):
        return GradeResult(False, "Not equivalent to the correct answer.")
    if factored and not _has_factor_shape(user_ast):
        return GradeResult(
            False,
            "Right value, wrong form — write it fully factored, e.g. (x+2)(x+3).",
        )
    return GradeResult(True, "")


def _check_set(expected: str, user: str) -> GradeResult:
    expected_parts, user_parts = _split_set(expected), _split_set(user)
    expected_set = _number_set(expected_parts)
    user_set = _number_set(user_parts)
    if user_set is None or expected_set is None:
        return GradeResult(False, "Every solution should be a plain number.")
    if user_set != expected_set:
        return GradeResult(False, "Not the right set of solutions.")
    return GradeResult(True, "")


def _number_set(parts: list[str]) -> frozenset[Fraction] | None:
    out: set[Fraction] = set()
    for part in parts:
        try:
            num = _to_number(_parse_and_eval(part))
        except (MathSyntaxError, MathEvalError, ZeroDivisionError):
            return None
        if num is None:
            return None
        out.add(num)
    return frozenset(out)


def _check_int_list(expected: str, user: str) -> GradeResult:
    expected_list = _int_list(expected)
    user_list = _int_list(user)
    if user_list is None or expected_list is None:
        return GradeResult(False, "Every entry should be a whole number.")
    if user_list == expected_list or user_list == list(reversed(expected_list)):
        return GradeResult(True, "")
    return GradeResult(False, "Not the right list of numbers.")


def _int_list(src: str) -> list[int] | None:
    parts = [p for p in re.split(r"[\s,;]+", src.strip()) if p]
    out: list[int] = []
    for part in parts:
        try:
            num = _to_number(_parse_and_eval(part))
        except (MathSyntaxError, MathEvalError, ZeroDivisionError):
            return None
        if num is None or num.denominator != 1:
            return None
        out.append(int(num))
    return out
