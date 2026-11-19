"""Tokenizer and recursive-descent parser for algebraic expressions.

Grammar (standard algebra precedence)::

    expr    := term  (('+' | '-') term)*
    term    := unary (('*' | '/') unary)*
    unary   := ('-' | '+') unary | power
    power   := postfix ('^' unary)?          # right-associative
    postfix := atom ('!')*
    atom    := NUMBER | VAR | FUNC '(' expr (',' expr)* ')' | '(' expr ')'

Implicit multiplication is inserted at the token level, so ``x(x+1)``,
``(x+1)(x+2)`` and ``2x`` all parse as products.  Unary minus binds looser
than ``^`` (so ``-3^2 == -9``) and ``!`` binds tighter than ``^``.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Final, Union

#: Names recognised as function calls (anything else letter-like becomes
#: single-letter variables, so ``xy`` means ``x*y``).
FUNCTIONS: Final[frozenset[str]] = frozenset(
    {"sqrt", "C", "choose", "binom", "perm"}
)

#: Variables users are likely to type; documented so error messages can
#: suggest splitting letter runs explicitly if a name is mistaken for a var.
KNOWN_VARS: Final[frozenset[str]] = frozenset({"x", "y", "n", "a", "b", "k", "m"})


class MathSyntaxError(ValueError):
    """Raised when input cannot be tokenized or parsed."""


# ---------------------------------------------------------------------- #
# AST
# ---------------------------------------------------------------------- #


@dataclass(frozen=True)
class Num:
    """An integer or decimal literal, stored exactly."""

    value: Fraction


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Neg:
    operand: "Node"


@dataclass(frozen=True)
class Add:
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Sub:
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Mul:
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Div:
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Pow:
    base: "Node"
    exponent: "Node"


@dataclass(frozen=True)
class Fact:
    """Postfix factorial: ``n!``."""

    operand: "Node"


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple["Node", ...]


Node = Union[
    Num, Var, Neg, Add, Sub, Mul, Div, Pow, Fact, Call
]


# ---------------------------------------------------------------------- #
# Tokens
# ---------------------------------------------------------------------- #

_KIND_NAMES: Final[dict[str, str]] = {
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "^": "CARET",
    "(": "LP",
    ")": "RP",
    ",": "COMMA",
    "!": "BANG",
}


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    pos: int  # 0-based offset into the source string


def tokenize(src: str) -> list[Token]:
    """Convert ``src`` into a token list with implicit ``*`` inserted."""
    tokens: list[Token] = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        if ch.isspace():
            i += 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and src[i + 1].isdigit()):
            j = i
            seen_dot = False
            while j < n and (src[j].isdigit() or (src[j] == "." and not seen_dot)):
                if src[j] == ".":
                    seen_dot = True
                j += 1
            tokens.append(Token("NUM", src[i:j], i))
            i = j
            continue
        if ch.isalpha():
            j = i
            while j < n and src[j].isalpha():
                j += 1
            word = src[i:j]
            if word in FUNCTIONS:
                tokens.append(Token("FUNC", word, i))
            else:
                for k, letter in enumerate(word):
                    tokens.append(Token("VAR", letter, i + k))
            i = j
            continue
        kind = _KIND_NAMES.get(ch)
        if kind is None:
            raise MathSyntaxError(
                f"unexpected character {ch!r} at position {i} in {src!r}"
            )
        tokens.append(Token(kind, ch, i))
        i += 1

    # Implicit multiplication: NUM/VAR/)/! followed by NUM/VAR/( or a function.
    multish: Final[frozenset[str]] = frozenset({"NUM", "VAR", "RP", "BANG"})
    startable: Final[frozenset[str]] = frozenset({"NUM", "VAR", "LP", "FUNC"})
    out: list[Token] = []
    prev: Token | None = None
    for tok in tokens:
        if prev is not None and prev.kind in multish and tok.kind in startable:
            out.append(Token("STAR", "*", prev.pos))
        out.append(tok)
        prev = tok
    return out


# ---------------------------------------------------------------------- #
# Parser
# ---------------------------------------------------------------------- #


class _Parser:
    def __init__(self, tokens: list[Token], src: str) -> None:
        self._tokens = tokens
        self._src = src
        self._i = 0

    def parse(self) -> Node:
        if not self._tokens:
            raise MathSyntaxError(f"empty expression: {self._src!r}")
        node = self._expr()
        tok = self._peek()
        if tok is not None:
            raise MathSyntaxError(
                f"unexpected {tok.text!r} at position {tok.pos} in {self._src!r}"
            )
        return node

    # -- helpers ------------------------------------------------------- #

    def _peek(self) -> Token | None:
        if self._i < len(self._tokens):
            return self._tokens[self._i]
        return None

    def _next(self) -> Token:
        tok = self._peek()
        if tok is None:
            raise MathSyntaxError(f"unexpected end of expression in {self._src!r}")
        self._i += 1
        return tok

    def _expect(self, kind: str) -> Token:
        tok = self._peek()
        if tok is None or tok.kind != kind:
            got = tok.text if tok else "end of expression"
            raise MathSyntaxError(f"expected {kind}, got {got!r} in {self._src!r}")
        return self._next()

    # -- grammar rules -------------------------------------------------- #

    def _expr(self) -> Node:
        node = self._term()
        while True:
            tok = self._peek()
            if tok is None or tok.kind not in ("PLUS", "MINUS"):
                return node
            self._next()
            rhs = self._term()
            node = Add(node, rhs) if tok.kind == "PLUS" else Sub(node, rhs)

    def _term(self) -> Node:
        node = self._unary()
        while True:
            tok = self._peek()
            if tok is None or tok.kind not in ("STAR", "SLASH"):
                return node
            self._next()
            rhs = self._unary()
            node = Mul(node, rhs) if tok.kind == "STAR" else Div(node, rhs)

    def _unary(self) -> Node:
        tok = self._peek()
        if tok is not None and tok.kind == "MINUS":
            self._next()
            return Neg(self._unary())
        if tok is not None and tok.kind == "PLUS":
            self._next()
            return self._unary()
        return self._power()

    def _power(self) -> Node:
        base = self._postfix()
        tok = self._peek()
        if tok is not None and tok.kind == "CARET":
            self._next()
            return Pow(base, self._unary())  # right-associative
        return base

    def _postfix(self) -> Node:
        node = self._atom()
        while (tok := self._peek()) is not None and tok.kind == "BANG":
            self._next()
            node = Fact(node)
        return node

    def _atom(self) -> Node:
        tok = self._next()
        if tok.kind == "NUM":
            return Num(Fraction(tok.text))
        if tok.kind == "VAR":
            return Var(tok.text)
        if tok.kind == "LP":
            node = self._expr()
            self._expect("RP")
            return node
        if tok.kind == "FUNC":
            fname = tok.text
            self._expect("LP")
            args: list[Node] = [self._expr()]
            while (sep := self._peek()) is not None and sep.kind == "COMMA":
                self._next()
                args.append(self._expr())
            self._expect("RP")
            return Call(fname, tuple(args))
        raise MathSyntaxError(
            f"unexpected {tok.text!r} at position {tok.pos} in {self._src!r}"
        )


def parse(src: str) -> Node:
    """Parse an algebraic expression string into an AST.

    Raises :class:`MathSyntaxError` on malformed input.
    """
    return _Parser(tokenize(src), src).parse()
