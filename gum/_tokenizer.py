from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator

from gum._errors import GumDecodeError


class TokenType(Enum):
    BARE_KEY = auto()
    QUOTED_STRING = auto()
    MULTILINE_STRING = auto()
    INTEGER = auto()
    FLOAT = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    EQUALS = auto()
    COMMA = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    DOT = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str | None = None
    lineno: int = 1
    colno: int = 1


class Tokenizer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.lineno = 1
        self.colno = 1

    def tokenize(self) -> Iterator[Token]:
        if self.source.startswith("\ufeff"):
            self.pos = 1
            self.colno = 2

        while self.pos < len(self.source):
            token = self._next_token()
            if token is not None:
                yield token

        yield Token(TokenType.EOF, lineno=self.lineno, colno=self.colno)

    def _next_token(self) -> Token | None:
        ch = self._peek()

        if ch in (" ", "\t"):
            self._advance()
            return None

        if ch == "\n":
            self._advance()
            return Token(TokenType.NEWLINE, lineno=self.lineno, colno=self.colno)
        if ch == "\r" and self._peek_ahead() == "\n":
            self._advance()
            self._advance()
            return Token(TokenType.NEWLINE, lineno=self.lineno, colno=self.colno)

        if ch == "#":
            self._advance()
            while self.pos < len(self.source) and self._peek() not in ("\n", "\r"):
                self._advance()
            return None

        symbol_map = {
            "=": TokenType.EQUALS,
            ",": TokenType.COMMA,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ".": TokenType.DOT,
        }
        if ch in symbol_map:
            self._advance()
            return Token(symbol_map[ch], lineno=self.lineno, colno=self.colno)

        if self._starts_with('"""'):
            return self._read_multiline_string()

        if ch == '"':
            return self._read_quoted_string()

        if ch.isalpha() or ch == "_":
            return self._read_bare_key_or_literal()

        if ch.isdigit() or ch in ("+", "-"):
            return self._read_number()

        raise GumDecodeError(f"unexpected character {ch!r}", self.lineno, self.colno)

    def _read_quoted_string(self) -> Token:
        start_line, start_col = self.lineno, self.colno
        self._advance()
        result = []

        while self.pos < len(self.source):
            ch = self._peek()
            if ch == '"':
                self._advance()
                return Token(TokenType.QUOTED_STRING, "".join(result), start_line, start_col)
            if ch == "\\":
                result.append(self._read_escape())
            elif ord(ch) < 0x20 and ch not in ("\n", "\r"):
                raise GumDecodeError("invalid control character in string", self.lineno, self.colno)
            else:
                result.append(ch)
                self._advance()

        raise GumDecodeError("unclosed string", start_line, start_col)

    def _read_multiline_string(self) -> Token:
        start_line, start_col = self.lineno, self.colno
        self._advance()
        self._advance()
        self._advance()

        if self._peek() == "\n":
            self._advance()
        elif self._peek() == "\r" and self._peek_ahead() == "\n":
            self._advance()
            self._advance()

        result = []
        while self.pos < len(self.source):
            if self._starts_with('"""'):
                self._advance()
                self._advance()
                self._advance()
                return Token(TokenType.MULTILINE_STRING, "".join(result), start_line, start_col)
            if self._peek() == "\\":
                next_pos = self.pos + 1
                while next_pos < len(self.source) and self.source[next_pos] in (" ", "\t"):
                    next_pos += 1
                if next_pos < len(self.source) and self.source[next_pos] in ("\n", "\r"):
                    self._advance()
                    while self._peek() in (" ", "\t"):
                        self._advance()
                    if self._peek() == "\n":
                        self._advance()
                    elif self._peek() == "\r" and self._peek_ahead() == "\n":
                        self._advance()
                        self._advance()
                    continue
            if self._peek() == "\\":
                result.append(self._read_escape())
            else:
                result.append(self._peek())
                self._advance()

        raise GumDecodeError("unclosed multiline string", start_line, start_col)

    def _read_bare_key_or_literal(self) -> Token:
        start_line, start_col = self.lineno, self.colno
        start = self.pos

        while self.pos < len(self.source) and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()

        value = self.source[start:self.pos]
        reserved = {"true": TokenType.TRUE, "false": TokenType.FALSE, "null": TokenType.NULL}

        if value in reserved:
            return Token(reserved[value], value, start_line, start_col)
        return Token(TokenType.BARE_KEY, value, start_line, start_col)

    def _read_number(self) -> Token:
        start_line, start_col = self.lineno, self.colno
        start = self.pos

        if self._peek() in ("+", "-"):
            self._advance()

        if not self._peek().isdigit():
            raise GumDecodeError("invalid number: no digits after sign", start_line, start_col)

        while self.pos < len(self.source) and self._peek().isdigit():
            self._advance()

        has_exp = False

        if self._peek() == ".":
            if not self.source[start:self.pos][-1:].isdigit():
                raise GumDecodeError("invalid float: no digits before decimal", start_line, start_col)
            self._advance()
            if not self._peek().isdigit():
                raise GumDecodeError("invalid float: no digits after decimal", start_line, start_col)
            while self.pos < len(self.source) and self._peek().isdigit():
                self._advance()

        if self._peek() in ("e", "E"):
            has_exp = True
            self._advance()
            if self._peek() in ("+", "-"):
                self._advance()
            if not self._peek().isdigit():
                raise GumDecodeError("invalid float: no digits in exponent", start_line, start_col)
            while self.pos < len(self.source) and self._peek().isdigit():
                self._advance()

        value = self.source[start:self.pos]

        if "." in value or has_exp:
            return Token(TokenType.FLOAT, value, start_line, start_col)
        return Token(TokenType.INTEGER, value, start_line, start_col)

    def _read_escape(self) -> str:
        self._advance()
        ch = self._peek()
        self._advance()

        escapes = {
            '"': '"',
            "\\": "\\",
            "b": "\b",
            "f": "\f",
            "n": "\n",
            "r": "\r",
            "t": "\t",
        }

        if ch in escapes:
            return escapes[ch]
        if ch == "u":
            return self._read_unicode(4)
        if ch == "U":
            return self._read_unicode(8)

        raise GumDecodeError(f"invalid escape sequence \\{ch}", self.lineno, self.colno)

    def _read_unicode(self, length: int) -> str:
        start = self.pos
        for _ in range(length):
            if self.pos >= len(self.source) or self._peek() not in "0123456789abcdefABCDEF":
                raise GumDecodeError("invalid unicode escape", self.lineno, self.colno)
            self._advance()
        hex_str = self.source[start:self.pos]
        return chr(int(hex_str, 16))

    def _peek(self) -> str:
        if self.pos >= len(self.source):
            return ""
        return self.source[self.pos]

    def _peek_ahead(self) -> str:
        if self.pos + 1 >= len(self.source):
            return ""
        return self.source[self.pos + 1]

    def _starts_with(self, s: str) -> bool:
        return self.source[self.pos:self.pos + len(s)] == s

    def _advance(self) -> None:
        if self.pos >= len(self.source):
            return
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.lineno += 1
            self.colno = 1
        else:
            self.colno += 1
