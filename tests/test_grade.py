"""Tests for answer grading across all answer kinds."""

from __future__ import annotations

import unittest

from gca.engine.grade import check


class TestExprKind(unittest.TestCase):
    def test_equivalent_forms(self) -> None:
        cases: list[tuple[str, str]] = [
            ("x^2-9", "(x-3)(x+3)"),
            ("x^2-9", "(x+3)(x-3)"),
            ("6/8", "3/4"),
            ("n(n-1)", "n^2-n"),
            ("x^2+5x+6", "(x+2)(x+3)"),
            ("sqrt(72)", "6sqrt(2)"),
            ("2x", "x+x"),
            ("0.5", "1/2"),
        ]
        for expected, user in cases:
            with self.subTest(expected=expected, user=user):
                self.assertTrue(check(expected, user, "expr").correct)

    def test_wrong_answers(self) -> None:
        for expected, user in (("x^2", "x^3"), ("2x+1", "2x-1"), ("8^(2/3)", "6")):
            with self.subTest(expected=expected, user=user):
                self.assertFalse(check(expected, user, "expr").correct)

    def test_errors_are_reported_not_raised(self) -> None:
        result = check("x^2", "x++", "expr")
        self.assertFalse(result.correct)
        self.assertTrue(result.message)

        result = check("x^2", "x/(x-x)", "expr")
        self.assertFalse(result.correct)
        self.assertTrue(result.message)

    def test_empty_input(self) -> None:
        self.assertFalse(check("x", "", "expr").correct)


class TestFactoredKind(unittest.TestCase):
    def test_factored_forms_accepted(self) -> None:
        self.assertTrue(check("(x+2)(x+3)", "(x+3)(x+2)", "factored").correct)
        self.assertTrue(check("(x+2)(x+3)", "(x+2)*(x+3)", "factored").correct)
        self.assertTrue(check("(x+2)^2", "(x+2)(x+2)", "factored").correct)
        self.assertTrue(check("3x(x-4)", "3x(x-4)", "factored").correct)
        self.assertTrue(check("x^2+4x+4", "(x+2)^2", "factored").correct)

    def test_expanded_form_rejected(self) -> None:
        self.assertFalse(check("(x+2)(x+3)", "x^2+5x+6", "factored").correct)
        self.assertFalse(check("x^2+4x+4", "x^2+4x+4", "factored").correct)

    def test_equivalent_but_wrong_shape_hinted(self) -> None:
        result = check("(x+2)(x+3)", "x^2+5x+6", "factored")
        self.assertFalse(result.correct)
        self.assertIn("factored", result.message.lower())


class TestSetKind(unittest.TestCase):
    def test_order_and_separators(self) -> None:
        self.assertTrue(check("8, -7", "8, -7", "set").correct)
        self.assertTrue(check("8, -7", "-7 and 8", "set").correct)
        self.assertTrue(check("8, -7", "8;-7", "set").correct)

    def test_wrong_solutions(self) -> None:
        self.assertFalse(check("8, -7", "8", "set").correct)
        self.assertFalse(check("8, -7", "8, -7, 0", "set").correct)
        self.assertFalse(check("8, -7", "9, -8", "set").correct)


class TestIntListKind(unittest.TestCase):
    def test_pascal_rows(self) -> None:
        self.assertTrue(check("1 4 6 4 1", "1 4 6 4 1", "int_list").correct)
        self.assertTrue(check("1 4 6 4 1", "1, 4, 6, 4, 1", "int_list").correct)
        self.assertTrue(check("1 4 6 4 1", "1 4 6 4 1", "int_list").correct)
        self.assertFalse(check("1 4 6 4 1", "1 4 6 5 1", "int_list").correct)
        self.assertFalse(check("1 4 6 4 1", "1 4 6 4", "int_list").correct)

    def test_reversed_accepts_symmetric_reading(self) -> None:
        self.assertTrue(check("1 5 10 10 5 1", "1 5 10 10 5 1", "int_list").correct)


if __name__ == "__main__":
    unittest.main()
