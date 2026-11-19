"""Exact arithmetic with square-root (radical) values.

A :class:`Radical` represents a number of the form::

    whole + sum over m of ( coefficient_m * sqrt(m) )

where every ``m`` is a squarefree integer >= 2 and coefficients are exact
:class:`Fraction` values.  This canonical form lets us grade answers like
``sqrt(72) == 6sqrt(2)`` or ``sqrt(8) + sqrt(18) == 5sqrt(2)`` exactly.

Radicals cannot be combined with symbolic (variable) values; the evaluator
enforces that.  Reciprocals are only supported for purely rational values
and single-radical-term denominators (``1/sqrt(m) = sqrt(m)/m``).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Mapping


def factor_sqrt(n: int) -> tuple[int, int]:
    """Decompose ``n >= 1`` as ``square * squarefree`` and return ``(square, squarefree)``."""
    if n < 1:
        raise ValueError(f"factor_sqrt expects a positive integer, got {n}")
    square = 1
    m = n
    d = 2
    while d * d <= m:
        pair = d * d
        while m % pair == 0:
            m //= pair
            square *= d
        d += 1
    return square, m


class Radical:
    """``whole + sum(coef * sqrt(m))`` in canonical form.

    Invariants:
      * keys of ``parts`` are squarefree integers >= 2
      * no zero coefficients are stored
      * ``whole`` may be zero
    """

    __slots__ = ("whole", "parts")

    def __init__(self, whole: Fraction, parts: Mapping[int, Fraction]) -> None:
        self.whole = whole
        self.parts: dict[int, Fraction] = {}
        for m, coef in parts.items():
            if m < 2:
                raise ValueError(f"radical index must be >= 2, got {m}")
            if coef != 0:
                self.parts[m] = coef

    def is_pure_number(self) -> bool:
        """True when no radical parts remain (the value is just ``whole``)."""
        return not self.parts

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Radical):
            return NotImplemented
        return self.whole == other.whole and self.parts == other.parts

    def __repr__(self) -> str:
        return f"Radical(whole={self.whole!r}, parts={self.parts!r})"


def sqrt_of_fraction(f: Fraction) -> Radical:
    """Exact ``sqrt`` of a nonnegative rational, reduced to canonical form."""
    if f < 0:
        raise ValueError("sqrt of a negative number")
    p, q = f.numerator, f.denominator
    square, m = factor_sqrt(p * q)
    coef = Fraction(square, q)
    if m == 1:
        return Radical(coef, {})
    return Radical(Fraction(0), {m: coef})


def scale(a: Radical, factor: Fraction) -> Radical:
    """Multiply every term of ``a`` by the rational ``factor``."""
    if factor == 0:
        return Radical(Fraction(0), {})
    return Radical(a.whole * factor, {m: c * factor for m, c in a.parts.items()})


def add(a: Radical, b: Radical) -> Radical:
    """Add two radical values by combining like radicals."""
    parts: dict[int, Fraction] = dict(a.parts)
    for m, c in b.parts.items():
        total = parts.get(m, Fraction(0)) + c
        if total == 0:
            parts.pop(m, None)
        else:
            parts[m] = total
    return Radical(a.whole + b.whole, parts)


def sub(a: Radical, b: Radical) -> Radical:
    return add(a, scale(b, Fraction(-1)))


def mul(a: Radical, b: Radical) -> Radical:
    """Multiply two radical values, re-reducing cross terms like ``sqrt(2)*sqrt(8)``."""
    whole = a.whole * b.whole
    parts: dict[int, Fraction] = {}

    def bump(m: int, coef: Fraction) -> None:
        if m == 1:
            nonlocal whole
            whole += coef
        else:
            total = parts.get(m, Fraction(0)) + coef
            if total == 0:
                parts.pop(m, None)
            else:
                parts[m] = total

    for m, c in b.parts.items():
        bump(m, a.whole * c)
    for m, c in a.parts.items():
        bump(m, b.whole * c)
    for m1, c1 in a.parts.items():
        for m2, c2 in b.parts.items():
            square, m = factor_sqrt(m1 * m2)
            bump(m, c1 * c2 * square)
    return Radical(whole, parts)


def reciprocal(a: Radical) -> Radical:
    """Exact reciprocal of a rational value or a single radical term.

    ``1/sqrt(m) == sqrt(m)/m`` handles the single-term case; binomial radical
    denominators (``1/(1 + sqrt(2))``) are intentionally unsupported.
    """
    if not a.parts:
        if a.whole == 0:
            raise ZeroDivisionError("reciprocal of zero")
        return Radical(1 / a.whole, {})
    if a.whole != 0 or len(a.parts) != 1:
        raise ValueError(
            "cannot take an exact reciprocal of a sum of radicals; "
            "rewrite without a radical in the denominator"
        )
    (m, c), = a.parts.items()
    if c == 0:
        raise ZeroDivisionError("reciprocal of zero")
    return Radical(Fraction(0), {m: 1 / (c * m)})


def div(a: Radical, b: Radical) -> Radical:
    """Divide radical value ``a`` by radical value ``b``."""
    return mul(a, reciprocal(b))


def pow_int(a: Radical, n: int) -> Radical:
    """Raise a radical value to an integer power via square-and-multiply."""
    if n < 0:
        return pow_int(reciprocal(a), -n)
    result = Radical(Fraction(1), {})
    base = a
    while n > 0:
        if n & 1:
            result = mul(result, base)
        base = mul(base, base)
        n >>= 1
    return result
