from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass
from typing import IO, Optional


class TokenType(Enum):
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    EQUALS = auto()
    COMMA = auto()
    DOT = auto()
    STRING = auto()
    NUMBER = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    IDENT = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str | None
    line: int
    col: int


class GumError(Exception):
    def __init__(self, message: str, line: int, col: int) -> None:
        self.line = line
        self.col = col
        super().__init__(f"{message} at line {line}, col {col}")


class Tokenizer:
    KEYWORDS: dict[str, TokenType] = {
        "true": TokenType.TRUE,
        "false": TokenType.FALSE,
        "null": TokenType.NULL,
    }

    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self._current: Optional[Token] = None
        self._advance()

    def peek(self) -> Optional[Token]:
        return self._current

    def advance(self) -> Optional[Token]:
        tok = self._current
        self._advance()
        return tok

    def expect(self, *types: TokenType) -> Optional[Token]:
        tok = self._current
        if tok is not None and tok.type not in types:
            expected = " or ".join(t.name for t in types)
            raise GumError(
                f"Expected {expected}, got {tok.type.name}",
                tok.line,
                tok.col,
            )
        self._advance()
        return tok

    def _advance(self) -> None:
        self._skip_ws_and_comments()
        if self.pos >= len(self.source):
            self._current = Token(TokenType.EOF, None, self.line, self.col)
            return

        ch = self.source[self.pos]

        if ch == "\n":
            self._current = Token(TokenType.NEWLINE, None, self.line, self.col)
            self._take_newline()
        elif ch == "\r":
            cr_line = self.line
            cr_col = self.col
            self._take_char()
            if self.pos < len(self.source) and self.source[self.pos] == "\n":
                self._current = Token(TokenType.NEWLINE, None, cr_line, cr_col)
                self._take_char()
            else:
                raise GumError(
                    "Unexpected character: \\r",
                    self.line,
                    self.col - 1,
                )
        elif ch == "{":
            self._current = Token(TokenType.LBRACE, None, self.line, self.col)
            self._take_char()
        elif ch == "}":
            self._current = Token(TokenType.RBRACE, None, self.line, self.col)
            self._take_char()
        elif ch == "[":
            self._current = Token(TokenType.LBRACKET, None, self.line, self.col)
            self._take_char()
        elif ch == "]":
            self._current = Token(TokenType.RBRACKET, None, self.line, self.col)
            self._take_char()
        elif ch == "=":
            self._current = Token(TokenType.EQUALS, None, self.line, self.col)
            self._take_char()
        elif ch == ",":
            self._current = Token(TokenType.COMMA, None, self.line, self.col)
            self._take_char()
        elif ch == ".":
            self._current = self._read_number_or_dot()
        elif ch == '"':
            self._current = self._read_string_or_multiline()
        elif ch == "-" or ("0" <= ch <= "9"):
            self._current = self._read_number()
        elif ("A" <= ch <= "Z") or ("a" <= ch <= "z") or ch == "_":
            self._current = self._read_ident()
        else:
            raise GumError(
                f"Unexpected character: {ch!r}",
                self.line,
                self.col,
            )

    def _take_char(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _take_newline(self) -> None:
        self.pos += 1
        self.line += 1
        self.col = 1

    def _skip_ws_and_comments(self) -> None:
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == " " or ch == "\t":
                self.pos += 1
                self.col += 1
            elif ch == "#":
                while self.pos < len(self.source):
                    c = self.source[self.pos]
                    if c == "\n" or c == "\r":
                        break
                    self.pos += 1
                    self.col += 1
            else:
                break

    def _read_string_or_multiline(self) -> Token:
        start_line = self.line
        start_col = self.col
        self._take_char()
        if (
            self.pos + 1 < len(self.source)
            and self.source[self.pos] == '"'
            and self.source[self.pos + 1] == '"'
        ):
            self.pos += 2
            self.col += 2
            return self._read_multiline_string(start_line, start_col)
        return self._read_quoted_string(start_line, start_col)

    def _read_quoted_string(self, start_line: int, start_col: int) -> Token:
        chars: list[str] = []
        while self.pos < len(self.source):
            ch = self._take_char()
            if ch == '"':
                return Token(TokenType.STRING, "".join(chars), start_line, start_col)
            if ch == "\\":
                ch = self._read_escape()
                chars.append(ch)
            else:
                code = ord(ch)
                if (code <= 0x08 or (0x0A <= code <= 0x1F) or code == 0x7F):
                    raise GumError(
                        f"Control character U+{code:04X} must be escaped",
                        self.line,
                        self.col - 1,
                    )
                chars.append(ch)
        raise GumError("Unterminated string", start_line, start_col)

    def _read_multiline_string(self, start_line: int, start_col: int) -> Token:
        chars: list[str] = []
        if self.pos < len(self.source) and self.source[self.pos] == "\n":
            self._take_char()
        elif (
            self.pos + 1 < len(self.source)
            and self.source[self.pos] == "\r"
            and self.source[self.pos + 1] == "\n"
        ):
            self._take_char()
            self._take_char()
        while self.pos < len(self.source):
            if (
                self.source[self.pos] == '"'
                and self.pos + 2 < len(self.source)
                and self.source[self.pos + 1] == '"'
                and self.source[self.pos + 2] == '"'
            ):
                self.pos += 3
                self.col += 3
                raw = "".join(chars)
                return Token(
                    TokenType.STRING, self._dedent_multiline(raw), start_line, start_col
                )
            ch = self._take_char()
            if ch == "\\":
                ch = self._read_escape()
                chars.append(ch)
            elif ch == "\r":
                # Normalize CRLF to LF
                if self.pos < len(self.source) and self.source[self.pos] == "\n":
                    self._take_char()
                chars.append("\n")
            else:
                chars.append(ch)
        raise GumError("Unterminated multiline string", start_line, start_col)

    def _dedent_multiline(self, raw: str) -> str:
        # Normalize any remaining \r\n to \n
        raw = raw.replace("\r\n", "\n")
        lines = raw.split("\n")
        if not lines:
            return raw
        last_line = ""
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip():
                last_line = lines[i]
                break
        indent = len(last_line) - len(last_line.lstrip())
        result: list[str] = []
        for i, line in enumerate(lines):
            if indent > 0 and len(line) >= indent and line[:indent].isspace():
                result.append(line[indent:])
            else:
                result.append(line)
        s = "\n".join(result)
        if s.endswith("\n"):
            s = s[:-1]
        return s

    def _read_escape(self) -> str:
        if self.pos >= len(self.source):
            raise GumError("Unterminated escape sequence", self.line, self.col)
        ch = self._take_char()
        mapping: dict[str, str] = {
            "b": "\b",
            "t": "\t",
            "n": "\n",
            "f": "\f",
            "r": "\r",
            '"': '"',
            "/": "/",
            "\\": "\\",
        }
        if ch == "u":
            hex_str = ""
            for _ in range(4):
                if self.pos >= len(self.source):
                    raise GumError("Unterminated unicode escape", self.line, self.col)
                hex_str += self._take_char()
            try:
                return chr(int(hex_str, 16))
            except ValueError:
                raise GumError(f"Invalid unicode escape: \\u{hex_str}", self.line, self.col)
        if ch in mapping:
            return mapping[ch]
        raise GumError(f"Invalid escape sequence: \\{ch}", self.line, self.col)

    def _read_number(self) -> Token:
        start_line = self.line
        start_col = self.col
        chars: list[str] = []
        if self.source[self.pos] == "-":
            chars.append(self._take_char())
        while self.pos < len(self.source) and "0" <= self.source[self.pos] <= "9":
            chars.append(self._take_char())
        if self.pos < len(self.source) and self.source[self.pos] == ".":
            chars.append(self._take_char())
            while self.pos < len(self.source) and "0" <= self.source[self.pos] <= "9":
                chars.append(self._take_char())
        return Token(TokenType.NUMBER, "".join(chars), start_line, start_col)

    def _read_number_or_dot(self) -> Token:
        start_line = self.line
        start_col = self.col
        self._take_char()
        if self.pos < len(self.source) and "0" <= self.source[self.pos] <= "9":
            chars: list[str] = ["."]
            while self.pos < len(self.source) and "0" <= self.source[self.pos] <= "9":
                chars.append(self._take_char())
            return Token(TokenType.NUMBER, "".join(chars), start_line, start_col)
        return Token(TokenType.DOT, None, start_line, start_col)

    def _read_ident(self) -> Token:
        start_line = self.line
        start_col = self.col
        chars: list[str] = []
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if (
                ("A" <= ch <= "Z")
                or ("a" <= ch <= "z")
                or ("0" <= ch <= "9")
                or ch == "_"
            ):
                chars.append(self._take_char())
            else:
                break
        word = "".join(chars)
        tok_type = self.KEYWORDS.get(word, TokenType.IDENT)
        return Token(tok_type, word, start_line, start_col)
