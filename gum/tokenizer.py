"""Tokenizer for the gum configuration file format.

Scans source text into a stream of tokens, handling:
- Comments (# to end of line, consumed silently)
- Whitespace (coalesced into WHITESPACE tokens)
- Strings (quoted and multi-line with spec-compliant dedent)
- Numbers (int, float, hex, binary, octal, scientific, with underscores)
- Keywords (true, false, null)
- Identifiers (bare keys)
- Punctuation ({, }, [, ], =, ,, .)

All tokens carry line/column position for error reporting.
"""
from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

from gum._errors import GumDecodeError

GumError = GumDecodeError


class TokenType(Enum):
    """Enumeration of all token types recognized by the tokenizer."""
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
    """Represents a single lexical token with type, value, and position."""
    type: TokenType
    value: str | None
    line: int
    col: int


class Tokenizer:
    """Converts gum source text into a stream of tokens."""
    KEYWORDS: dict[str, TokenType] = {
        "true": TokenType.TRUE,
        "false": TokenType.FALSE,
        "null": TokenType.NULL,
    }

    def __init__(self, source: str) -> None:
        """Initialize tokenizer with source text."""
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self._current: Optional[Token] = None
        self._advance()

    def peek(self) -> Optional[Token]:
        """Return the current token without advancing."""
        return self._current

    def advance(self) -> Optional[Token]:
        """Return the current token and advance to the next one."""
        tok = self._current
        self._advance()
        return tok

    def expect(self, *types: TokenType) -> Optional[Token]:
        """Assert the current token matches one of the given types, then advance."""
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
        """Read the next non-comment token and store it as _current."""
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
                # Consume comment to end of line, validating each character
                while self.pos < len(self.source):
                    c = self.source[self.pos]
                    if c == "\n":
                        break
                    if c == "\r":
                        break
                    code = ord(c)
                    # ABNF comment-char = HTAB / %x20-10FFFF
                    if code <= 0x08 or (0x0A <= code <= 0x1F):
                        raise GumError(
                            f"Invalid character U+{code:04X} in comment",
                            self.line,
                            self.col,
                        )
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
        """Read a single-line quoted string, enforcing control character escaping."""
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
                if code <= 0x08 or (0x0A <= code <= 0x1F):
                    raise GumError(
                        f"Control character U+{code:04X} must be escaped",
                        self.line,
                        self.col - 1,
                    )
                chars.append(ch)
        raise GumError("Unterminated string", start_line, start_col)

    def _read_multiline_string(self, start_line: int, start_col: int) -> Token:
        """Read a triple-quoted multiline string, normalizing CRLF and applying dedent."""
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
                # Check for line continuation: \ followed by optional whitespace then newline
                next_pos = self.pos
                while next_pos < len(self.source) and self.source[next_pos] in (" ", "\t"):
                    next_pos += 1
                if next_pos < len(self.source) and self.source[next_pos] in ("\n", "\r"):
                    # Line continuation: skip backslash, whitespace, and newline
                    while self.pos < len(self.source) and self.source[self.pos] in (" ", "\t"):
                        self._take_char()
                    if self.pos < len(self.source) and self.source[self.pos] == "\n":
                        self._take_char()
                    elif (
                        self.pos + 1 < len(self.source)
                        and self.source[self.pos] == "\r"
                        and self.source[self.pos + 1] == "\n"
                    ):
                        self._take_char()
                        self._take_char()
                    continue
                ch = self._read_escape()
                chars.append(ch)
            elif ch == "\r":
                # CRLF is permitted via nl rule; bare CR is not
                if self.pos < len(self.source) and self.source[self.pos] == "\n":
                    self._take_char()
                    chars.append("\n")
                else:
                    raise GumError(
                        "Unexpected character: \\r",
                        self.line,
                        self.col - 1,
                    )
            else:
                code = ord(ch)
                if code <= 0x08 or (0x0B <= code <= 0x1F):
                    raise GumError(
                        f"Control character U+{code:04X} must be escaped",
                        self.line,
                        self.col - 1,
                    )
                chars.append(ch)
        raise GumError("Unterminated multiline string", start_line, start_col)

    def _dedent_multiline(self, raw: str) -> str:
        """Apply spec-compliant multi-line string dedent.

        Algorithm:
        1. Split content into lines.
        2. Remove first line if empty (whitespace only).
        3. Remove last line if whitespace only.
        4. Find minimum indentation (spaces only) of remaining non-empty lines.
        5. Strip that many leading spaces from every non-empty line.
        6. Join with newlines.

        Args:
            raw: The raw multiline string content (without delimiters).

        Returns:
            The dedented string with consistent indentation.
        """
        raw = raw.replace("\r\n", "\n")
        lines = raw.split("\n")
        if not lines:
            return raw

        # Step 2: Remove first line if empty
        if lines and not lines[0].strip():
            lines = lines[1:]
        if not lines:
            return ""

        # Step 3: Remove last line if whitespace only
        if lines and not lines[-1].strip():
            lines = lines[:-1]
        if not lines:
            return ""

        # Step 4: Find minimum indentation (spaces only) of non-empty lines
        min_indent = None
        for line in lines:
            if line.strip():  # non-empty
                # Count leading spaces only
                space_count = 0
                for ch in line:
                    if ch == " ":
                        space_count += 1
                    else:
                        break
                if min_indent is None or space_count < min_indent:
                    min_indent = space_count

        if min_indent is None or min_indent == 0:
            min_indent = 0

        # Step 5: Strip min_indent spaces from non-empty lines
        result: list[str] = []
        for line in lines:
            if line.strip():  # non-empty
                result.append(line[min_indent:])
            else:
                result.append(line)

        # Step 6: Join with newlines
        return "\n".join(result)

    def _read_escape(self) -> str:
        """Read and resolve an escape sequence after the backslash."""
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
        """Parse a number: int, float, hex, binary, octal, scientific, with optional underscore separators.

        Dispatches to the appropriate specialized reader based on prefix.
        """
        start_line = self.line
        start_col = self.col
        chars: list[str] = []

        # Check for explicit positive prefix
        if self.pos < len(self.source) and self.source[self.pos] == "+":
            chars.append(self._take_char())

        # Check for negative prefix
        elif self.pos < len(self.source) and self.source[self.pos] == "-":
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
        """Read a hexadecimal number literal (0x prefix)."""
        chars = prefix
        chars.append(self._take_char())  # '0'
        chars.append(self._take_char())  # 'x' or 'X'
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ("0" <= ch <= "9") or ("a" <= ch <= "f") or ("A" <= ch <= "F") or ch == "_":
                chars.append(self._take_char())
            else:
                break
        if len(chars) <= 2:
            raise GumError("Hex literal requires at least one digit after 0x", start_line, start_col)
        self._validate_underscores(chars, start_line, start_col)
        return Token(TokenType.NUMBER, "".join(chars), start_line, start_col)

    def _read_binary(self, start_line: int, start_col: int, prefix: list[str]) -> Token:
        """Read a binary number literal (0b prefix)."""
        chars = prefix
        chars.append(self._take_char())  # '0'
        chars.append(self._take_char())  # 'b' or 'B'
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in ("0", "1") or ch == "_":
                chars.append(self._take_char())
            else:
                break
        if len(chars) <= 2:
            raise GumError("Binary literal requires at least one digit after 0b", start_line, start_col)
        self._validate_underscores(chars, start_line, start_col)
        return Token(TokenType.NUMBER, "".join(chars), start_line, start_col)

    def _read_octal(self, start_line: int, start_col: int, prefix: list[str]) -> Token:
        """Read an octal number literal (0o prefix)."""
        chars = prefix
        chars.append(self._take_char())  # '0'
        chars.append(self._take_char())  # 'o' or 'O'
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ("0" <= ch <= "7") or ch == "_":
                chars.append(self._take_char())
            else:
                break
        if len(chars) <= 2:
            raise GumError("Octal literal requires at least one digit after 0o", start_line, start_col)
        self._validate_underscores(chars, start_line, start_col)
        return Token(TokenType.NUMBER, "".join(chars), start_line, start_col)

    def _validate_decimal_segment_underscores(self, segment: str, start_line: int, start_col: int) -> None:
        """Validate underscore placement within a single decimal digit segment."""
        if not segment:
            return
        if segment.startswith("_"):
            raise GumError("Underscore cannot be leading", start_line, start_col)
        if segment.endswith("_"):
            raise GumError("Underscore cannot be trailing", start_line, start_col)
        if "__" in segment:
            raise GumError("Underscores cannot be consecutive", start_line, start_col)

    def _read_decimal(self, start_line: int, start_col: int, prefix: list[str]) -> Token:
        """Read a decimal number, optionally with fractional and/or scientific notation parts."""
        chars = prefix
        # Integer part
        int_start = len(chars)
        while self.pos < len(self.source) and ("0" <= self.source[self.pos] <= "9" or self.source[self.pos] == "_"):
            chars.append(self._take_char())
        if len(chars) == 1 and chars[0] in ("+", "-"):
            raise GumError("Expected digit after sign", start_line, start_col)
        # Validate integer segment
        self._validate_decimal_segment_underscores("".join(chars[int_start:]), start_line, start_col)
        # Fractional part
        if self.pos < len(self.source) and self.source[self.pos] == ".":
            chars.append(self._take_char())
            frac_start = len(chars)
            while self.pos < len(self.source) and ("0" <= self.source[self.pos] <= "9" or self.source[self.pos] == "_"):
                chars.append(self._take_char())
            # Validate fractional segment
            self._validate_decimal_segment_underscores("".join(chars[frac_start:]), start_line, start_col)
        # Scientific notation
        if self.pos < len(self.source) and self.source[self.pos] in ("e", "E"):
            chars.append(self._take_char())
            if self.pos < len(self.source) and self.source[self.pos] in ("+", "-"):
                chars.append(self._take_char())
            # ABNF requires at least one digit in dec-digits
            if self.pos >= len(self.source) or not ("0" <= self.source[self.pos] <= "9" or self.source[self.pos] == "_"):
                raise GumError("Expected digit in exponent", start_line, start_col)
            exp_start = len(chars)
            while self.pos < len(self.source) and ("0" <= self.source[self.pos] <= "9" or self.source[self.pos] == "_"):
                chars.append(self._take_char())
            # Validate exponent segment
            self._validate_decimal_segment_underscores("".join(chars[exp_start:]), start_line, start_col)
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
        """Read an identifier or keyword (alphanumeric + underscore, starting with letter or underscore)."""
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
