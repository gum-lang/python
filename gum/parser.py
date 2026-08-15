"""Recursive descent parser for the gum configuration file format.

Consumes tokens produced by the Tokenizer and builds a nested dict/list
structure representing the parsed configuration.

Grammar handled:
- Assignments: ``key = value`` separated by commas or newlines
- Dotted path keys: ``a.b.c = 1`` creates nested dicts
- Inline tables: ``{ key = val, ... }``
- Arrays: ``[ val, val, ... ]``
- Literal values: strings, numbers (int/float/hex/binary/octal), booleans, null

Semantic validation performed during parsing:
- Duplicate key detection (same scope)
- Inline table immutability (cannot redefine or extend inline tables)
- Path conflict detection (table vs scalar type mismatches)

The parser stops on the first error encountered (no error recovery).
All errors are raised as GumError with line/column position.
"""
from __future__ import annotations

from typing import Any, NoReturn, Optional

from gum.tokenizer import Token, Tokenizer, TokenType, GumError


class Parser:
    """Recursive descent parser that converts a token stream into a nested dict.

    The parser consumes tokens from a Tokenizer and produces a Python dict
    representing the gum configuration. It handles assignments, dotted path
    keys, inline tables, arrays, and all literal value types.

    Semantic validation is performed during parsing:
    - Duplicate keys within the same scope are rejected.
    - Inline tables (created via ``{}`` syntax) are immutable once defined;
      they cannot be redefined or extended via dotted paths.
    - Path conflicts (e.g., assigning a scalar where a table exists) are
      detected and reported.

    The parser is single-pass with no error recovery; the first error
    encountered halts parsing and raises GumError.

    Attributes:
        tok: The Tokenizer instance providing the token stream.
        _inline_tables: Set of fully-qualified paths (as tuples of key names)
            that correspond to inline table values. Used to enforce immutability
            of inline tables during subsequent assignments.
    """

    def __init__(self, tokenizer: Tokenizer) -> None:
        """Initialize the parser with a Tokenizer instance.

        Args:
            tokenizer: A Tokenizer that has been primed (i.e., peek() returns
                the first token). The parser will consume tokens from this
                tokenizer until EOF is reached.
        """
        self.tok = tokenizer
        self._inline_tables: set[tuple[str, ...]] = set()

    def _error(self, msg: str) -> NoReturn:
        """Raise a GumError at the current token position.

        Uses the line/column of the next unconsumed token to provide
        precise error location. If the tokenizer is exhausted (EOF),
        falls back to position (0, 0).

        Args:
            msg: Human-readable error message.

        Raises:
            GumError: Always raised with the message and position.
        """
        t = self.tok.peek()
        if t is not None:
            raise GumError(msg, t.line, t.col)
        else:
            raise GumError(msg, 0, 0)

    def _peek(self) -> TokenType:
        """Return the type of the next token without consuming it.

        Unlike Tokenizer.peek(), this method errors on EOF rather than
        returning None, ensuring callers always receive a valid TokenType.

        Returns:
            The TokenType of the next unconsumed token.

        Raises:
            GumError: If the tokenizer is exhausted (EOF).
        """
        next_token = self.tok.peek()
        if next_token is None:
            self._error("Unexpected end of input")
        return next_token.type

    def _advance(self) -> Optional[Token]:
        """Consume and return the current token, advancing to the next.

        Returns:
            The Token that was current before advancing, or None if the
            tokenizer has not been primed.
        """
        return self.tok.advance()

    def _expect(self, *types: TokenType) -> Any:
        """Assert the current token matches one of the given types, then advance.

        Args:
            *types: One or more acceptable TokenType values.

        Returns:
            The matched Token if the assertion succeeds.

        Raises:
            GumError: If the current token's type is not in *types.
        """
        return self.tok.expect(*types)

    def _skip_separators(self) -> None:
        """Consume consecutive NEWLINE and WHITESPACE tokens.

        Used to skip over formatting between meaningful tokens. Stops at
        the first non-separator token (which remains unconsumed).
        """
        while self._peek() in (TokenType.NEWLINE, TokenType.WHITESPACE):
            self._advance()

    def parse(self) -> dict[str, Any]:
        """Parse the entire token stream into a nested dict.

        Entry point for parsing. Consumes tokens until EOF, parsing each
        top-level assignment expression and building the result dict.

        Returns:
            A dict representing the parsed gum configuration. Keys are
            strings, values are Python objects (str, int, float, bool,
            None, dict, or list).

        Raises:
            GumError: On any syntax error, duplicate key, or path conflict.
        """
        result: dict[str, Any] = {}
        seen_keys: set[str] = set()
        self._skip_separators()
        while self._peek() != TokenType.EOF:
            self._parse_expression(result, seen_keys, path_prefix=())
            self._skip_sep({TokenType.EOF})
        return result

    def _register_inline_tables_recursive(self, path: tuple[str, ...], value: Any) -> None:
        """Register a value and all nested dicts as inline tables.

        When an inline table ``{ ... }`` is parsed, its path and the paths
        of all nested dicts within it are recorded so that subsequent
        assignments cannot redefine or extend them.

        Args:
            path: The fully-qualified key path (tuple of key names) to the value.
            value: The parsed value. If it is a dict, it and all nested dicts
                are registered in _inline_tables.
        """
        if isinstance(value, dict):
            self._inline_tables.add(path)
            for key, val in value.items():
                self._register_inline_tables_recursive(path + (key,), val)

    def _parse_expression(self, target: dict[str, Any], seen_keys: set[str], path_prefix: tuple[str, ...] = ()) -> None:
        """Parse a single assignment expression: ``key.path = value``.

        Reads a dotted key path, an equals sign, and a value. Performs
        duplicate key detection at the current scope level, then delegates
        to _assign_path() to insert the value into the target dict.

        Args:
            target: The dict to assign into (top-level result or inline table).
            seen_keys: Set of simple (non-dotted) key names already assigned
                in this scope. Used for duplicate detection.
            path_prefix: Prefix prepended to the parsed key path when
                registering inline tables. Empty for top-level expressions.

        Raises:
            GumError: On duplicate keys, inline table redefinition, or
                any syntax error in the key path or value.
        """
        keys = self._parse_path()
        self._skip_separators()
        self._expect(TokenType.EQUALS)
        value = self._parse_value()
        full_path = path_prefix + tuple(keys)
        # Duplicate detection: only for simple (non-dotted) keys at this scope.
        # Dotted keys like a.b are handled by _assign_path conflict detection.
        if len(keys) == 1 and keys[0] in seen_keys:
            # Check if existing is an inline table being replaced
            if full_path in self._inline_tables:
                self._error(f"Cannot redefine inline table at {keys[0]!r}")
            self._error(f"Duplicate key: {keys[0]!r}")
        if len(keys) == 1:
            seen_keys.add(keys[0])
        self._assign_path(target, keys, value)
        # Register inline tables after assignment so they are tracked
        if isinstance(value, dict):
            self._register_inline_tables_recursive(full_path, value)

    def _parse_path(self) -> list[str]:
        """Parse a dotted key path (e.g., ``a.b.c`` -> ``['a', 'b', 'c']``).

        Consumes one or more key segments separated by DOT tokens.

        Returns:
            A list of key name strings. Always contains at least one element.

        Raises:
            GumError: If a key segment is missing, malformed, or uses a
                reserved keyword.
        """
        keys = [self._parse_key()]
        while self._peek() == TokenType.DOT:
            self._advance()
            keys.append(self._parse_key())
        return keys

    def _parse_key(self) -> str:
        """Parse a single key segment from an IDENT or STRING token.

        Bare identifiers (e.g., ``foo``) and quoted strings (e.g., ``"foo"``)
        are both valid keys. Reserved keywords (``true``, ``false``, ``null``)
        are rejected.

        Returns:
            The key name as a string.

        Raises:
            GumError: If the next token is not a valid key type, is EOF,
                or is a reserved keyword.
        """
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
        """Parse the next value token into a Python object.

        Dispatches based on the next token type:
        - STRING -> str
        - NUMBER -> int or float (via _parse_number_value)
        - TRUE -> True
        - FALSE -> False
        - NULL -> None
        - LBRACE -> dict (via _parse_table)
        - LBRACKET -> list (via _parse_array)

        Returns:
            The parsed Python value.

        Raises:
            GumError: If the next token is not a valid value type, or on
                any syntax error within a table or array.
        """
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
        """Convert a number token string to int or float per the gum spec.

        Supports the following formats:
        - Decimal integers: ``42``, ``-7``, ``+3``
        - Decimal floats: ``3.14``, ``-0.5``, ``1e10``, ``2.5E-3``
        - Hexadecimal: ``0xFF``, ``0x1A``
        - Binary: ``0b1010``
        - Octal: ``0o77``
        - Underscore separators: ``1_000_000`` (stripped before conversion)

        Args:
            s: The raw number string from the token (may include sign,
                underscores, and base prefix).

        Returns:
            An int for integer formats, or a float for decimal/hex formats
            with a fractional or exponent part.
        """
        clean = s.lstrip("+-")
        # Hex, binary, octal: detect by 0x/0b/0o prefix
        if clean.startswith(("0x", "0X", "0b", "0B", "0o", "0O")):
            base_map = {"0x": 16, "0X": 16, "0b": 2, "0B": 2, "0o": 8, "0O": 8}
            base = base_map[clean[:2]]
            digits = clean[2:].replace("_", "")
            result = int(digits, base)
            if s.startswith("-"):
                return -result
            return result
        # Scientific notation: contains 'e' or 'E'
        if "e" in clean or "E" in clean:
            return float(s.replace("_", ""))
        # Decimal float: contains '.'
        if "." in clean:
            return float(s.replace("_", ""))
        # Plain integer
        return int(s.replace("_", ""))

    def _parse_table(self) -> dict[str, Any]:
        """Parse an inline table enclosed in ``{ }``.

        Reads the opening brace, then parses comma/newline-separated
        assignment expressions until the closing brace. Each inline table
        gets its own ``seen_keys`` set for duplicate detection within its
        scope.

        Returns:
            A dict representing the inline table's contents.

        Raises:
            GumError: On missing braces, duplicate keys within the table,
                or any syntax error in contained expressions.
        """
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
        """Consume a separator (comma or newline) between elements.

        Handles three valid separator patterns:
        1. A comma (optionally followed by whitespace/newlines)
        2. A newline (optionally followed by a comma and more whitespace)
        3. No separator if the next token is a closing delimiter

        Args:
            closing_types: Set of token types that indicate the end of the
                current collection (e.g., RBRACE, RBRACKET, EOF). If the
                next token is one of these, no separator is consumed.

        Raises:
            GumError: If the next token is neither a valid separator nor
                a closing delimiter.
        """
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
        """Parse an array literal enclosed in ``[ ]``.

        Reads the opening bracket, then parses comma/newline-separated
        values until the closing bracket. Arrays may contain mixed types.

        Returns:
            A list of parsed Python values.

        Raises:
            GumError: On missing brackets or any syntax error in contained
                values.
        """
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
        """Assign a value at a nested key path, with conflict detection.

        Walks the key path from left to right, creating intermediate dicts
        as needed for dotted keys. At each level, checks for:

        1. **Inline table redefinition** — if the full path matches a
           registered inline table, the assignment would overwrite an
           immutable inline table.
        2. **Inline table extension** — if the parent path is a registered
           inline table, the assignment would add a new key to an existing
           inline table (which is forbidden).
        3. **Type conflict** — if an existing value is a dict but the new
           value is not (or vice versa for intermediate keys), the path
           structure is contradictory.
        4. **Duplicate key** — if the key already exists and none of the
           above special cases apply.

        Args:
            target: The root dict to assign into.
            keys: The list of key names forming the path (e.g., ``['a', 'b', 'c']``).
            value: The value to assign at the final key.

        Raises:
            GumError: On any of the four conflict conditions above.
        """
        current = target
        for i, key in enumerate(keys):
            full_path_so_far = tuple(keys[:i+1])
            parent_path = tuple(keys[:i])
            if i == len(keys) - 1:
                # Final key in path: assign the value here
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
                # Intermediate key: must be or become a dict
                if key not in current:
                    current[key] = {}
                elif not isinstance(current[key], dict):
                    self._error(
                        f"Key path conflict: {key!r} is already a {type(current[key]).__name__}, cannot be a table"
                    )
                current = current[key]
