"""Evaluate parser ASTs into exact values.

The result of evaluation is either a :class:`~gca.engine.poly.RatFunc`
(covering plain numbers, polynomials and rational functions) or a
:class:`~gca.engine.radicals.Radical` (square-root values).  Every operation
is exact — no floating point anywhere.
"""

from __future__ import annotations

import math
from fractions import Fraction

from gca.engine.parser import (
    Add,
    Call,
    Div,
    Fact,
    Mul,
    Neg,
    Node,
    Num,
    Pow,
    Sub,
    Var,
)
from gca.engine.poly import Poly, RatFunc
from gca.engine.radicals import Radical, add as rad_add, div as rad_div, mul as rad_mul, pow_int as rad_pow, scale as rad_scale, sqrt_of_fraction, sub as rad_sub

MAX_FACTORIAL: int = 1000


class MathEvalError(ValueError):
    """Raised when an expression cannot be evaluated exactly."""


Value = RatFunc | Radical

_ONE = Fraction(1)


def _as_value(x: Radical | RatFunc) -> Value:
    """Collapse a radical with no radical parts into a plain RatFunc."""
    if isinstance(x, Radical) and not x.parts:
        return RatFunc.from_number(x.whole)
    return x


def _number(value: Value, what: str) -> Fraction:
    """Extract a rational number from a value, or fail with a clear message."""
    if isinstance(value, Radical):
        if value.parts:
            raise MathEvalError(f"{what} must be a plain number, not a radical")
        return value.whole
    if not value.is_number():
        raise MathEvalError(f"{what} must be a plain number, not an expression with variables")
    return value.number()


def _is_int(f: Fraction) -> bool:
    return f.denominator == 1


def _exact_int_root(n: int, k: int) -> int | None:
    """Exact integer k-th root of ``n >= 0``, or None if not a perfect power."""
    if k <= 0:
        raise ValueError("root index must be positive")
    if n in (0, 1):
        return n
    guess = round(n ** (1.0 / k))
    for candidate in (guess - 1, guess, guess + 1):
        if candidate >= 0 and candidate**k == n:
            return candidate
    return None


def _exact_root(f: Fraction, k: int) -> Fraction | None:
    """Exact rational k-th root of a nonnegative rational, or None."""
    if f < 0:
        return None
    num = _exact_int_root(f.numerator, k)
    if num is None:
        return None
    den = _exact_int_root(f.denominator, k)
    if den is None:
        return None
    return Fraction(num, den)


def _eval_factorial(operand: Node) -> RatFunc:
    f = _number(evaluate(operand), "factorial argument")
    if not _is_int(f) or f < 0:
        raise MathEvalError("factorials need a nonnegative whole number")
    if f > MAX_FACTORIAL:
        raise MathEvalError(f"factorial argument too large (max {MAX_FACTORIAL})")
    return RatFunc.from_number(math.factorial(int(f)))


def _combinatoric(name: str, args: tuple[Node, ...]) -> RatFunc:
    if len(args) != 2:
        raise MathEvalError(f"{name}(a, b) takes exactly two arguments")
    a = _number(evaluate(args[0]), f"{name} argument")
    b = _number(evaluate(args[1]), f"{name} argument")
    if not _is_int(a) or not _is_int(b) or a < 0 or b < 0:
        raise MathEvalError(f"{name}(a, b) needs nonnegative whole numbers")
    if b > a:
        raise MathEvalError(f"{name}(a, b) needs b <= a, got {name}({int(a)}, {int(b)})")
    fn = math.comb if name in ("C", "choose", "binom") else math.perm
    return RatFunc.from_number(fn(int(a), int(b)))


def _pow_value(base: Value, exponent: Value) -> Value:
    e = _number(exponent, "exponent")
    if _is_int(e):
        n = int(e)
        if isinstance(base, Radical):
            return _as_value(rad_pow(base, n))
        return _as_value(base**n)  # type: ignore[operator]
    # Rational exponent: only numeric bases supported.
    p, q = e.numerator, e.denominator
    if isinstance(base, Radical):
        raise MathEvalError("fractional exponents on radicals are not supported")
    if not base.is_number():
        raise MathEvalError(
            "variables can only be raised to whole-number exponents"
        )
    value = base.number()
    if q == 2:
        if value < 0:
            raise MathEvalError("sqrt of a negative number")
        return _as_value(rad_pow(sqrt_of_fraction(value), p))
    if value < 0 and q % 2 == 0:
        raise MathEvalError("even root of a negative number")
    r = _exact_root(abs(value), q)
    if r is None:
        raise MathEvalError(
            f"{value}^({e}) is not exact; answers must avoid irrational results "
            "except simple square roots (use sqrt(...))"
        )
    result = r**p if p >= 0 else Fraction(1) / r**(-p)
    if value < 0 and q % 2 == 1:
        result = -result
    return RatFunc.from_number(result)


def _mixed_number(value: Value, side: str) -> Fraction:
    """Extract a plain number when mixing radicals with RatFuncs."""
    if isinstance(value, Radical):
        if value.parts:
            raise MathEvalError(f"cannot combine radicals with variables ({side})")
        return value.whole
    if not value.is_number():
        raise MathEvalError(f"cannot combine radicals with variables ({side})")
    return value.number()


def _apply_rad_binary(
    left: Value,
    right: Value,
    op: str,
) -> Value:
    """Apply + - * / when at least one side is a Radical."""
    if isinstance(left, Radical) and isinstance(right, Radical):
        if op == "+":
            return _as_value(rad_add(left, right))
        if op == "-":
            return _as_value(rad_sub(left, right))
        if op == "*":
            return _as_value(rad_mul(left, right))
        return _as_value(rad_div(left, right))
    if isinstance(left, Radical):
        f = _mixed_number(right, "left side")
        return _apply_rad_scalar(left, f, op, right_side=False)
    assert isinstance(right, Radical)
    f = _mixed_number(left, "right side")
    return _apply_rad_scalar(right, f, op, right_side=True)


def _apply_rad_scalar(rad: Radical, f: Fraction, op: str, *, right_side: bool) -> Value:
    if op in ("+", "-"):
        if not right_side and op == "-":
            raise MathEvalError("cannot subtract an expression with variables from a radical")
        term = Radical(f, {})
        return _as_value(rad_add(rad, term) if op == "+" else rad_sub(rad, term))
    if op == "*":
        return _as_value(rad_scale(rad, f))
    # Division
    if right_side:
        if f == 0:
            raise MathEvalError("division by zero")
        return _as_value(rad_scale(rad, 1 / f))
    # f / rad
    return _as_value(rad_div(Radical(f, {}), rad))


def evaluate(node: Node) -> Value:
    """Evaluate an AST to a :class:`RatFunc` or :class:`Radical`.

    Raises :class:`MathEvalError` when the expression has no exact value
    (division by zero, irrational results, radicals mixed with variables...).
    """
    if isinstance(node, Num):
        return RatFunc.from_number(node.value)
    if isinstance(node, Var):
        return RatFunc.variable(node.name)
    if isinstance(node, Neg):
        inner = evaluate(node.operand)
        if isinstance(inner, Radical):
            return _as_value(rad_scale(inner, Fraction(-1)))
        return -inner
    if isinstance(node, (Add, Sub, Mul, Div)):
        left = evaluate(node.left)
        right = evaluate(node.right)
        op = {Add: "+", Sub: "-", Mul: "*", Div: "/"}[type(node)]
        if isinstance(left, Radical) or isinstance(right, Radical):
            return _apply_rad_binary(left, right, op)
        if op == "+":
            return left + right  # type: ignore[operator]
        if op == "-":
            return left - right  # type: ignore[operator]
        if op == "*":
            return left * right  # type: ignore[operator]
        return _as_value(left / right)  # type: ignore[operator]
    if isinstance(node, Pow):
        return _pow_value(evaluate(node.base), evaluate(node.exponent))
    if isinstance(node, Fact):
        return _eval_factorial(node.operand)
    if isinstance(node, Call):
        if node.name == "sqrt":
            if len(node.args) != 1:
                raise MathEvalError("sqrt takes exactly one argument")
            arg = evaluate(node.args[0])
            f = _number(arg, "sqrt argument")
            if f < 0:
                raise MathEvalError("sqrt of a negative number")
            return _as_value(sqrt_of_fraction(f))
        return _combinatoric(node.name, node.args)
    raise AssertionError(f"unhandled AST node: {node!r}")


def evaluate_str(src: str) -> Value:
    """Convenience: parse then evaluate a string expression."""
    from gca.engine.parser import MathSyntaxError, parse

    try:
        return evaluate(parse(src))
    except MathSyntaxError:
        raise
    except ZeroDivisionError as exc:
        raise MathEvalError(str(exc) or "division by zero") from exc
