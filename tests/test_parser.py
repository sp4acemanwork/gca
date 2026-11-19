"""Tests for the expression parser and evaluator."""

from __future__ import annotations

import unittest
from fractions import Fraction

from gca.engine.evaluate import MathEvalError, evaluate
from gca.engine.parser import MathSyntaxError, parse
from gca.engine.poly import RatFunc
from gca.engine.radicals import Radical


def num(value: Fraction | int) -> Fraction:
    """Evaluate an expression string to a rational number."""
    v = evaluate(parse(str(value)))
    if isinstance(v, Radical):
        assert not v.parts, f"not a number: {v}"
        return v.whole
    assert v.is_number(), f"not a number: {value}"
    return v.number()


def is_radical(src: str) -> bool:
    v = evaluate(parse(src))
    return isinstance(v, Radical)


def rf(src: str) -> RatFunc:
    """Evaluate an expression string to a rational function."""
    v = evaluate(parse(src))
    assert isinstance(v, RatFunc), f"not a rational function: {src}"
    return v


class TestNumbers(unittest.TestCase):
    def test_arithmetic(self) -> None:
        cases: list[tuple[str, str]] = [
            ("2+3*4", "14"),
            ("(2+3)*4", "20"),
            ("10/4", "5/2"),
            ("1.5+2", "7/2"),
            ("2^10", "1024"),
            ("2^-2", "1/4"),
            ("-3^2", "-9"),
            ("(-3)^2", "9"),
            ("--4", "4"),
            ("-(-4)", "4"),
            ("6/2*3", "9"),
        ]
        for src, want in cases:
            with self.subTest(src=src):
                self.assertEqual(num(src), Fraction(want))

    def test_right_assoc_power(self) -> None:
        self.assertEqual(num("2^3^2"), Fraction(512))

    def test_factorial_and_binomials(self) -> None:
        self.assertEqual(num("5!"), Fraction(120))
        self.assertEqual(num("3!^2"), Fraction(36))
        self.assertEqual(num("C(5,2)"), Fraction(10))
        self.assertEqual(num("binom(6,3)"), Fraction(20))
        self.assertEqual(num("choose(4,4)"), Fraction(1))
        self.assertEqual(num("perm(5,2)"), Fraction(20))

    def test_syntax_errors(self) -> None:
        for src in ("2+", "(x", "sqrt", "2//3", "C(5)", ""):
            with self.subTest(src=src):
                with self.assertRaises((MathSyntaxError, MathEvalError)):
                    evaluate(parse(src))


class TestPolynomials(unittest.TestCase):
    def test_implicit_multiplication(self) -> None:
        self.assertTrue(rf("x(x+1)").equiv(rf("x^2+x")))
        self.assertTrue(rf("2x^2").equiv(rf("2*x^2")))
        self.assertTrue(rf("(x+1)(x+2)").equiv(rf("x^2+3x+2")))
        self.assertTrue(rf("xy").equiv(rf("yx")))
        self.assertTrue(rf("xy").equiv(rf("x*y")))

    def test_variables(self) -> None:
        self.assertTrue(rf("x^3x").equiv(rf("x^4")))
        self.assertTrue(rf("x^2y^3").equiv(rf("y^3x^2")))
        self.assertTrue(not rf("x").equiv(rf("y")))

    def test_rational_functions(self) -> None:
        self.assertTrue(rf("(x^2-9)/(x+3)").equiv(rf("x-3")))

    def test_zero_denominator(self) -> None:
        with self.assertRaises(Exception):
            evaluate(parse("1/(x-x)"))

    def test_symbolic_fractional_exponent_rejected(self) -> None:
        with self.assertRaises(MathEvalError):
            evaluate(parse("x^(1/2)"))


class TestRadicals(unittest.TestCase):
    def test_simple_roots(self) -> None:
        self.assertEqual(num("sqrt(16)"), Fraction(4))
        self.assertEqual(
            evaluate(parse("sqrt(8)")),
            evaluate(parse("2sqrt(2)")),
        )

    def test_canonical_radicals(self) -> None:
        self.assertTrue(is_radical("sqrt(8)"))
        self.assertEqual(
            evaluate(parse("sqrt(72)")),
            evaluate(parse("6sqrt(2)")),
        )
        self.assertEqual(
            evaluate(parse("sqrt(8)+sqrt(18)")),
            evaluate(parse("5sqrt(2)")),
        )
        self.assertEqual(
            evaluate(parse("sqrt(2)*sqrt(8)")),
            evaluate(parse("4")),
        )
        self.assertEqual(
            evaluate(parse("1/sqrt(2)")),
            evaluate(parse("sqrt(2)/2")),
        )
        self.assertEqual(
            evaluate(parse("3sqrt(2) - sqrt(2)")),
            evaluate(parse("2sqrt(2)")),
        )

    def test_negative_sqrt_rejected(self) -> None:
        with self.assertRaises(MathEvalError):
            evaluate(parse("sqrt(-4)"))

    def test_radical_with_variables_rejected(self) -> None:
        with self.assertRaises(MathEvalError):
            evaluate(parse("x + sqrt(2)"))


class TestRationalExponents(unittest.TestCase):
    def test_perfect_roots(self) -> None:
        self.assertEqual(num("8^(2/3)"), Fraction(4))
        self.assertEqual(num("27^(1/3)"), Fraction(3))
        self.assertEqual(num("16^(3/4)"), Fraction(8))
        self.assertEqual(num("4^(-1/2)"), Fraction(1, 2))

    def test_irrational_rejected(self) -> None:
        with self.assertRaises(MathEvalError):
            evaluate(parse("2^(1/3)"))


if __name__ == "__main__":
    unittest.main()
