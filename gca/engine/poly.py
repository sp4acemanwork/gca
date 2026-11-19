"""Exact multivariate polynomial and rational-function arithmetic.

Canonical form: a :class:`Poly` stores its variables in sorted order and a
dense-in-sparse-representation dict mapping exponent tuples to exact
:class:`Fraction` coefficients (zero coefficients are never stored).  A
:class:`RatFunc` is a ratio of two polynomials with a nonzero denominator.

Equality/equivalence never needs division: two rational functions ``p1/q1``
and ``p2/q2`` are equal exactly when ``p1*q2 - p2*q1`` is the zero polynomial.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Iterable, Mapping

Exp = tuple[int, ...]


def _merge_vars(*var_sets: Iterable[str]) -> tuple[str, ...]:
    """Union variable names, sorted, deduplicated."""
    out: set[str] = set()
    for vs in var_sets:
        out.update(vs)
    return tuple(sorted(out))


def _embed(
    exp: Exp,
    old_vars: tuple[str, ...],
    new_vars: tuple[str, ...],
) -> Exp:
    """Re-express an exponent tuple written over ``old_vars`` over ``new_vars``."""
    if old_vars == new_vars:
        return exp
    index = {v: e for v, e in zip(old_vars, exp)}
    return tuple(index.get(v, 0) for v in new_vars)


def _add_into(
    target: dict[Exp, Fraction],
    exp: Exp,
    coef: Fraction,
) -> None:
    """Add ``coef`` at ``exp``, dropping the term if it cancels to zero."""
    total = target.get(exp, Fraction(0)) + coef
    if total == 0:
        target.pop(exp, None)
    else:
        target[exp] = total


class Poly:
    """A multivariate polynomial with exact rational coefficients.

    Invariants:
      * ``vars`` is sorted and unique.
      * Every key of ``coeffs`` has the same width as ``vars``.
      * No zero coefficients are stored (the zero polynomial has no terms).
    """

    __slots__ = ("vars", "coeffs")

    def __init__(
        self,
        vars: tuple[str, ...] = (),
        coeffs: Mapping[Exp, Fraction] | None = None,
    ) -> None:
        self.vars = vars
        self.coeffs: dict[Exp, Fraction] = dict(coeffs) if coeffs else {}
        assert list(self.vars) == sorted(set(self.vars)), "vars must be sorted+unique"
        width = len(self.vars)
        self.coeffs = {
            exp: c for exp, c in self.coeffs.items() if c != 0 and len(exp) == width
        }

    # ------------------------------------------------------------------ #
    # Constructors
    # ------------------------------------------------------------------ #

    @classmethod
    def constant(cls, value: Fraction | int) -> "Poly":
        v = value if isinstance(value, Fraction) else Fraction(value)
        if v == 0:
            return cls((), {})
        return cls((), {(): v})

    @classmethod
    def variable(cls, name: str) -> "Poly":
        return cls((name,), {(1,): Fraction(1)})

    @classmethod
    def zero(cls) -> "Poly":
        return cls((), {})

    # ------------------------------------------------------------------ #
    # Predicates / accessors
    # ------------------------------------------------------------------ #

    def is_zero(self) -> bool:
        return not self.coeffs

    def is_constant(self) -> bool:
        return not self.vars and len(self.coeffs) <= 1

    def const(self) -> Fraction:
        """Value of a polynomial with no variables.

        Raises :class:`ValueError` if the polynomial has any variables.
        """
        if self.vars:
            raise ValueError(f"not a constant polynomial: vars={self.vars}")
        if not self.coeffs:
            return Fraction(0)
        (coef,) = self.coeffs.values()
        return coef

    # ------------------------------------------------------------------ #
    # Arithmetic
    # ------------------------------------------------------------------ #

    def _binop(self, other: "Poly", sign: int) -> "Poly":
        vars = _merge_vars(self.vars, other.vars)
        out: dict[Exp, Fraction] = {
            _embed(e, self.vars, vars): c for e, c in self.coeffs.items()
        }
        for e, c in other.coeffs.items():
            _add_into(out, _embed(e, other.vars, vars), sign * c)
        return Poly(vars, out)

    def __add__(self, other: "Poly") -> "Poly":
        return self._binop(other, 1)

    def __sub__(self, other: "Poly") -> "Poly":
        return self._binop(other, -1)

    def __neg__(self) -> "Poly":
        return Poly(self.vars, {e: -c for e, c in self.coeffs.items()})

    def __mul__(self, other: "Poly") -> "Poly":
        vars = _merge_vars(self.vars, other.vars)
        out: dict[Exp, Fraction] = {}
        for e1, c1 in self.coeffs.items():
            a1 = _embed(e1, self.vars, vars)
            for e2, c2 in other.coeffs.items():
                a2 = _embed(e2, other.vars, vars)
                _add_into(out, tuple(x + y for x, y in zip(a1, a2)), c1 * c2)
        return Poly(vars, out)

    def __pow__(self, n: int) -> "Poly":
        if n < 0:
            raise ValueError("polynomial powers must have nonnegative exponents")
        result = Poly.constant(1)
        base = self
        while n > 0:
            if n & 1:
                result = result * base
            base = base * base
            n >>= 1
        return result

    def scaled(self, factor: Fraction) -> "Poly":
        if factor == 0:
            return Poly.zero()
        return Poly(self.vars, {e: c * factor for e, c in self.coeffs.items()})

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Poly):
            return NotImplemented
        return self.vars == other.vars and self.coeffs == other.coeffs

    def __hash__(self) -> int:  # pragma: no cover - dicts are unhashable
        raise TypeError("Poly is unhashable")

    def __repr__(self) -> str:
        return f"Poly(vars={self.vars!r}, coeffs={self.coeffs!r})"


class RatFunc:
    """A rational function ``num / den`` with a nonzero denominator ``den``."""

    __slots__ = ("num", "den")

    def __init__(self, num: Poly, den: Poly) -> None:
        if den.is_zero():
            raise ZeroDivisionError("zero denominator in rational function")
        self.num = num
        self.den = den

    # ------------------------------------------------------------------ #
    # Constructors
    # ------------------------------------------------------------------ #

    @classmethod
    def from_number(cls, value: Fraction | int) -> "RatFunc":
        f = value if isinstance(value, Fraction) else Fraction(value)
        return cls(Poly.constant(f), Poly.constant(1))

    @classmethod
    def variable(cls, name: str) -> "RatFunc":
        return cls(Poly.variable(name), Poly.constant(1))

    # ------------------------------------------------------------------ #
    # Predicates / accessors
    # ------------------------------------------------------------------ #

    def is_number(self) -> bool:
        return not self.num.vars and not self.den.vars

    def number(self) -> Fraction:
        """Value of a numeric (constant) rational function.

        Raises :class:`ValueError` if the function has any variables.
        """
        if not self.is_number():
            raise ValueError(f"not a number: vars={self.num.vars or self.den.vars}")
        return self.num.const() / self.den.const()

    def is_zero(self) -> bool:
        return self.num.is_zero()

    # ------------------------------------------------------------------ #
    # Arithmetic
    # ------------------------------------------------------------------ #

    def __add__(self, other: "RatFunc") -> "RatFunc":
        return RatFunc(
            self.num * other.den + other.num * self.den,
            self.den * other.den,
        )

    def __sub__(self, other: "RatFunc") -> "RatFunc":
        return RatFunc(
            self.num * other.den - other.num * self.den,
            self.den * other.den,
        )

    def __mul__(self, other: "RatFunc") -> "RatFunc":
        return RatFunc(self.num * other.num, self.den * other.den)

    def __truediv__(self, other: "RatFunc") -> "RatFunc":
        if other.num.is_zero():
            raise ZeroDivisionError("division by zero")
        return RatFunc(self.num * other.den, self.den * other.num)

    def __neg__(self) -> "RatFunc":
        return RatFunc(-self.num, self.den)

    def __pow__(self, n: int) -> "RatFunc":
        if n < 0:
            if self.num.is_zero():
                raise ZeroDivisionError("0 to a negative power")
            return RatFunc(self.den ** (-n), self.num ** (-n))
        return RatFunc(self.num**n, self.den**n)

    def equiv(self, other: "RatFunc") -> bool:
        """Structural equality: ``p1/q1 == p2/q2`` iff ``p1*q2 - p2*q1 == 0``."""
        return (self.num * other.den - other.num * self.den).is_zero()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RatFunc):
            return NotImplemented
        return self.equiv(other)

    def __hash__(self) -> int:  # pragma: no cover
        raise TypeError("RatFunc is unhashable")

    def __repr__(self) -> str:
        return f"RatFunc(num={self.num!r}, den={self.den!r})"
