from __future__ import annotations

from typing import Any

from gum.tokenizer import Tokenizer, TokenType, GumError


class Parser:
    def __init__(self, tokenizer: Tokenizer) -> None:
        self.tok = tokenizer

    def _error(self, msg: str) -> None:
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

    def _advance(self) -> Tokenizer:
        return self.tok.advance()

    def _expect(self, *types: TokenType) -> Any:
        return self.tok.expect(*types)

    def _skip_newlines(self) -> None:
        while self._peek() == TokenType.NEWLINE:
            self._advance()

    def parse(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        self._skip_newlines()
        while self._peek() != TokenType.EOF:
            self._parse_expression(result)
            self._skip_sep({TokenType.EOF})
        return result

    def _parse_expression(self, target: dict[str, Any]) -> None:
        keys = self._parse_path()
        self._expect(TokenType.EQUALS)
        value = self._parse_value()
        self._assign_path(target, keys, value)

    def _parse_path(self) -> list[str]:
        keys = [self._parse_key()]
        while self._peek() == TokenType.DOT:
            self._advance()
            keys.append(self._parse_key())
        return keys

    def _parse_key(self) -> str:
        tok = self._advance()
        if tok.type == TokenType.IDENT:
            return tok.value
        elif tok.type == TokenType.STRING:
            return tok.value
        elif tok.type in (TokenType.TRUE, TokenType.FALSE, TokenType.NULL):
            self._error(f"Reserved keyword '{tok.value}' cannot be used as a key")
        else:
            self._error(f"Expected key, got {tok.type.name}({tok.value!r})")

    def _parse_value(self) -> Any:
        t = self._peek()
        if t == TokenType.STRING:
            return self._advance().value
        elif t == TokenType.NUMBER:
            raw = self._advance().value
            if "." in raw:
                return float(raw)
            return int(raw)
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

    def _parse_table(self) -> dict[str, Any]:
        self._expect(TokenType.LBRACE)
        result: dict[str, Any] = {}
        self._skip_newlines()
        while self._peek() not in (TokenType.RBRACE, TokenType.EOF):
            self._parse_expression(result)
            self._skip_sep({TokenType.RBRACE})
        self._expect(TokenType.RBRACE)
        return result

    def _skip_sep(self, closing_types: set[TokenType]) -> None:
        if self._peek() in closing_types:
            return
        if self._peek() == TokenType.COMMA:
            self._advance()
        elif self._peek() != TokenType.NEWLINE:
            self._error("Expected comma or newline")
        self._skip_newlines()

    def _parse_array(self) -> list[Any]:
        self._expect(TokenType.LBRACKET)
        result: list[Any] = []
        self._skip_newlines()
        while self._peek() not in (TokenType.RBRACKET, TokenType.EOF):
            result.append(self._parse_value())
            self._skip_sep({TokenType.RBRACKET})
        self._expect(TokenType.RBRACKET)
        return result

    def _assign_path(
        self, target: dict[str, Any], keys: list[str], value: Any
    ) -> None:
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                target[key] = value
            else:
                if key not in target:
                    target[key] = {}
                elif not isinstance(target[key], dict):
                    self._error(f"Cannot set key {key!r}: existing value is not a table")
                target = target[key]
