from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


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
    WHITESPACE = auto()
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
        self.message = message
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
        if source.startswith("\ufeff"):
            source = source[1:]
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
        self._current = None
        self._read_ws_or_comment()
        if self._current is not None:
            return
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
        elif ch == "-" or ch == "+" or ("0" <= ch <= "9"):
            self._current = self._read_number_or_check_ident()
        elif ("A" <= ch <= "Z") or ("a" <= ch <= "z") or ch == "_":
            if ch == "_" and self.pos + 1 < len(self.source) and "0" <= self.source[self.pos + 1] <= "9":
                raise GumError(
                    "Underscore cannot be leading",
                    self.line,
                    self.col,
                )
            self._current = self._read_ident()
        else:
            raise GumError(
                f"Unexpected character: {ch!r}",
                self.line,
                self.col,
            )

    def _advance_col_for_tab(self) -> None:
        self.col = ((self.col - 1) // 4 + 1) * 4 + 1

    def _take_char(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        elif ch == "\t":
            self._advance_col_for_tab()
        else:
            self.col += 1
        return ch

    def _take_newline(self) -> None:
        self.pos += 1
        self.line += 1
        self.col = 1

    def _read_ws_or_comment(self) -> None:
        """Skip comments silently; emit WHITESPACE token for runs of spaces/tabs."""
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == "#":
                # Consume comment to end of line
                while self.pos < len(self.source):
                    c = self.source[self.pos]
                    if c == "\n":
                        break
                    if c == "\r":
                        break
                    self.pos += 1
                # Don't consume the newline itself; let it become NEWLINE token
            elif ch == " " or ch == "\t":
                start_line = self.line
                start_col = self.col
                ws_chars: list[str] = []
                while self.pos < len(self.source) and self.source[self.pos] in (" ", "\t"):
                    ws_chars.append(self._take_char())
                self._current = Token(TokenType.WHITESPACE, "".join(ws_chars), start_line, start_col)
                return
            else:
                return

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
        """Parse a number: int, float, hex, binary, octal, scientific, with optional underscore separators."""
        start_line = self.line
        start_col = self.col
        chars: list[str] = []

        # Check for explicit positive prefix
        if self.pos < len(self.source) and self.source[self.pos] == "+":
            chars.append(self._take_char())

        # Check for negative prefix
        if self.pos < len(self.source) and self.source[self.pos] == "-":
            chars.append(self._take_char())

        # Check for hex, binary, octal prefixes
        if self.pos + 1 < len(self.source) and self.source[self.pos] == "0":
            next_ch = self.source[self.pos + 1]
            if next_ch in ("x", "X"):
                return self._read_hex(start_line, start_col, chars)
            elif next_ch in ("b", "B"):
                return self._read_binary(start_line, start_col, chars)
            elif next_ch in ("o", "O"):
                return self._read_octal(start_line, start_col, chars)

        # Decimal number
        return self._read_decimal(start_line, start_col, chars)

    def _read_hex(self, start_line: int, start_col: int, prefix: list[str]) -> Token:
        chars = prefix
        chars.append(self._take_char())  # '0'
        chars.append(self._take_char())  # 'x' or 'X'
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ("0" <= ch <= "9") or ("a" <= ch <= "f") or ("A" <= ch <= "F") or ch == "_":
                chars.append(self._take_char())
            else:
                break
        self._validate_underscores(chars, start_line, start_col)
        return Token(TokenType.NUMBER, "".join(chars), start_line, start_col)

    def _read_binary(self, start_line: int, start_col: int, prefix: list[str]) -> Token:
        chars = prefix
        chars.append(self._take_char())  # '0'
        chars.append(self._take_char())  # 'b' or 'B'
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in ("0", "1") or ch == "_":
                chars.append(self._take_char())
            else:
                break
        self._validate_underscores(chars, start_line, start_col)
        return Token(TokenType.NUMBER, "".join(chars), start_line, start_col)

    def _read_octal(self, start_line: int, start_col: int, prefix: list[str]) -> Token:
        chars = prefix
        chars.append(self._take_char())  # '0'
        chars.append(self._take_char())  # 'o' or 'O'
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ("0" <= ch <= "7") or ch == "_":
                chars.append(self._take_char())
            else:
                break
        self._validate_underscores(chars, start_line, start_col)
        return Token(TokenType.NUMBER, "".join(chars), start_line, start_col)

    def _read_decimal(self, start_line: int, start_col: int, prefix: list[str]) -> Token:
        chars = prefix
        # Integer part
        while self.pos < len(self.source) and ("0" <= self.source[self.pos] <= "9" or self.source[self.pos] == "_"):
            chars.append(self._take_char())
        # Fractional part
        is_float = False
        if self.pos < len(self.source) and self.source[self.pos] == ".":
            is_float = True
            chars.append(self._take_char())
            while self.pos < len(self.source) and ("0" <= self.source[self.pos] <= "9" or self.source[self.pos] == "_"):
                chars.append(self._take_char())
        # Scientific notation
        if self.pos < len(self.source) and self.source[self.pos] in ("e", "E"):
            is_float = True
            chars.append(self._take_char())
            if self.pos < len(self.source) and self.source[self.pos] in ("+", "-"):
                chars.append(self._take_char())
            while self.pos < len(self.source) and ("0" <= self.source[self.pos] <= "9" or self.source[self.pos] == "_"):
                chars.append(self._take_char())
        self._validate_underscores(chars, start_line, start_col)
        return Token(TokenType.NUMBER, "".join(chars), start_line, start_col)

    def _validate_underscores(self, chars: list[str], start_line: int, start_col: int) -> None:
        """Validate underscore placement: not leading, trailing, or consecutive."""
        s = "".join(chars)
        # Find where the numeric content starts (after optional sign and base prefix)
        content_start = 0
        if s and s[0] in ("+", "-"):
            content_start = 1
        if content_start < len(s) and s[content_start] == "0" and content_start + 1 < len(s) and s[content_start + 1] in ("x", "X", "b", "B", "o", "O"):
            content_start += 2
        content = s[content_start:]
        if not content:
            return
        if content.startswith("_"):
            raise GumError("Underscore cannot be leading", start_line, start_col)
        if content.endswith("_"):
            raise GumError("Underscore cannot be trailing", start_line, start_col)
        if "__" in content:
            raise GumError("Underscores cannot be consecutive", start_line, start_col)

    def _read_number_or_check_ident(self) -> Token:
        """Parse a number starting with digit or minus, then verify it's not followed by ident chars."""
        num = self._read_number()
        if self.pos < len(self.source):
            next_ch = self.source[self.pos]
            if ("A" <= next_ch <= "Z") or ("a" <= next_ch <= "z") or next_ch == "_":
                raise GumError(
                    "Invalid token: number cannot be followed by identifier characters",
                    num.line,
                    num.col,
                )
        return num

    def _read_number_or_dot(self) -> Token:
        """Parse a dot: either start of float (.5) or DOT token."""
        start_line = self.line
        start_col = self.col
        self._take_char()
        if self.pos < len(self.source) and "0" <= self.source[self.pos] <= "9":
            chars: list[str] = ["."]
            while self.pos < len(self.source) and ("0" <= self.source[self.pos] <= "9" or self.source[self.pos] == "_"):
                chars.append(self._take_char())
            self._validate_underscores(chars, start_line, start_col)
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
