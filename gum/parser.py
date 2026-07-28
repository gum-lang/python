from __future__ import annotations

from typing import Any, NoReturn, Optional

from gum.tokenizer import Token, Tokenizer, TokenType, GumError


class Parser:
    def __init__(self, tokenizer: Tokenizer) -> None:
        self.tok = tokenizer
        self._inline_tables: set[tuple[str, ...]] = set()

    def _error(self, msg: str) -> NoReturn:
        t = self.tok.peek()
        if t is not None:
            raise GumError(msg, t.line, t.col)
        else:
            raise GumError(msg, 0, 0)

    def _peek(self) -> TokenType:
        next_token = self.tok.peek()
        if next_token is None:
            self._error("Unexpected end of input")
        return next_token.type

    def _advance(self) -> Optional[Token]:
        return self.tok.advance()

    def _expect(self, *types: TokenType) -> Any:
        return self.tok.expect(*types)

    def _skip_separators(self) -> None:
        while self._peek() in (TokenType.NEWLINE, TokenType.WHITESPACE):
            self._advance()

    def parse(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        seen_keys: set[str] = set()
        self._skip_separators()
        while self._peek() != TokenType.EOF:
            self._parse_expression(result, seen_keys, path_prefix=())
            self._skip_sep({TokenType.EOF})
        return result

    def _register_inline_tables_recursive(self, path: tuple[str, ...], value: Any) -> None:
        if isinstance(value, dict):
            self._inline_tables.add(path)
            for key, val in value.items():
                self._register_inline_tables_recursive(path + (key,), val)

    def _parse_expression(self, target: dict[str, Any], seen_keys: set[str], path_prefix: tuple[str, ...] = ()) -> None:
        keys = self._parse_path()
        self._skip_separators()
        self._expect(TokenType.EQUALS)
        value = self._parse_value()
        full_path = path_prefix + tuple(keys)
        if len(keys) == 1 and keys[0] in seen_keys:
            # Check if existing is an inline table being replaced
            if full_path in self._inline_tables:
                self._error(f"Cannot redefine inline table at {keys[0]!r}")
            self._error(f"Duplicate key: {keys[0]!r}")
        if len(keys) == 1:
            seen_keys.add(keys[0])
        self._assign_path(target, keys, value)
        if isinstance(value, dict):
            self._register_inline_tables_recursive(full_path, value)

    def _parse_path(self) -> list[str]:
        keys = [self._parse_key()]
        while self._peek() == TokenType.DOT:
            self._advance()
            keys.append(self._parse_key())
        return keys

    def _parse_key(self) -> str:
        tok = self._advance()
        if tok is None:
            self._error("Unexpected end of input")
        if tok.value is None:
            self._error(f"Failed to parse key at line {tok.line}, col {tok.col}")

        if tok.type == TokenType.IDENT:
            return tok.value
        elif tok.type == TokenType.STRING:
            return tok.value
        elif tok.type in (TokenType.TRUE, TokenType.FALSE, TokenType.NULL):
            self._error(f"Reserved keyword '{tok.value}' cannot be used as a key")
        else:
            self._error(f"Expected key, got {tok.type.name}({tok.value!r})")

    def _parse_value(self) -> Any:
        self._skip_separators()
        t = self._peek()

        if t == TokenType.STRING:
            tok = self._advance()
            if tok is None:
                self._error("Unexpected end of input")
            elif tok.value is None:
                self._error(f"Failed to parse value at line {tok.line}, col {tok.col}")
            return tok.value
        elif t == TokenType.NUMBER:
            tok = self._advance()
            if tok is None:
                self._error("Unexpected end of input")
            elif tok.value is None:
                self._error(f"Failed to parse value at line {tok.line}, col {tok.col}")
            return self._parse_number_value(tok.value)
        elif t == TokenType.TRUE:
            self._advance()
            return True
        elif t == TokenType.FALSE:
            self._advance()
            return False
        elif t == TokenType.NULL:
            self._advance()
            return None
        elif t == TokenType.LBRACE:
            return self._parse_table()
        elif t == TokenType.LBRACKET:
            return self._parse_array()
        else:
            self._error(f"Unexpected token: {t.name}")

    def _parse_number_value(self, s: str) -> int | float:
        """Convert number token string to int or float per spec rules."""
        if s.startswith(("0x", "0X", "0b", "0B", "0o", "0O")):
            base_map = {"0x": 16, "0X": 16, "0b": 2, "0B": 2, "0o": 8, "0O": 8}
            base = base_map[s[:2]]
            digits = s[2:].replace("_", "")
            return int(digits, base)
        clean = s.lstrip("+-")
        if "e" in clean or "E" in clean:
            return float(s.replace("_", ""))
        if "." in clean:
            return float(s.replace("_", ""))
        return int(s.replace("_", ""))

    def _parse_table(self) -> dict[str, Any]:
        self._expect(TokenType.LBRACE)
        result: dict[str, Any] = {}
        seen_keys: set[str] = set()
        self._skip_separators()
        while self._peek() not in (TokenType.RBRACE, TokenType.EOF):
            self._parse_expression(result, seen_keys, path_prefix=())
            self._skip_sep({TokenType.RBRACE})
        self._expect(TokenType.RBRACE)
        return result

    def _skip_sep(self, closing_types: set[TokenType]) -> None:
        if self._peek() in closing_types:
            return
        if self._peek() == TokenType.COMMA:
            self._advance()
            self._skip_separators()
        elif self._peek() in (TokenType.NEWLINE, TokenType.WHITESPACE):
            self._skip_separators()
            if self._peek() == TokenType.COMMA:
                self._advance()
                self._skip_separators()
        else:
            self._error("Expected comma or newline")

    def _parse_array(self) -> list[Any]:
        self._expect(TokenType.LBRACKET)
        result: list[Any] = []
        self._skip_separators()
        while self._peek() not in (TokenType.RBRACKET, TokenType.EOF):
            result.append(self._parse_value())
            self._skip_sep({TokenType.RBRACKET})
        self._expect(TokenType.RBRACKET)
        return result

    def _assign_path(
        self, target: dict[str, Any], keys: list[str], value: Any
    ) -> None:
        current = target
        for i, key in enumerate(keys):
            full_path_so_far = tuple(keys[:i+1])
            parent_path = tuple(keys[:i])
            if i == len(keys) - 1:
                if key in current:
                    # Check if existing is an inline table being replaced
                    if full_path_so_far in self._inline_tables:
                        self._error(f"Cannot redefine inline table at {key!r}")
                    # Check if we're trying to redefine a sub-key of an inline table
                    if parent_path in self._inline_tables:
                        self._error(f"Cannot redefine sub-key of inline table at {key!r}")
                    # Check type conflict: existing dict being replaced by non-dict
                    if isinstance(current[key], dict) and not isinstance(value, dict):
                        self._error(
                            f"Key path conflict: {key!r} is already a table, cannot be a {type(value).__name__}"
                        )
                    self._error(f"Duplicate key: {key!r}")
                current[key] = value
            else:
                if key not in current:
                    current[key] = {}
                elif not isinstance(current[key], dict):
                    self._error(
                        f"Key path conflict: {key!r} is already a {type(current[key]).__name__}, cannot be a table"
                    )
                current = current[key]
