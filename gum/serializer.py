"""Serializer for the gum configuration file format.

Converts Python dicts back to gum-formatted strings, implementing the
serialization half of the gum round-trip (dumps/loads).

Key behaviors:
    - Uses spec-defined escapes only (no \\/ for forward slashes)
    - Multi-line strings use triple-quote syntax when possible
    - Heuristic selection of inline vs multi-line format for tables and lists
    - Supports custom key formatting via optional key_formatter callable

Public API:
    serialize(data, indent, key_formatter) -> str

The module also exposes ``dumps`` as an alias for ``serialize`` via the
top-level ``gum`` package.
"""
from __future__ import annotations

from typing import Any, Callable


def serialize(
    data: dict[str, Any],
    indent: int = 2,
    key_formatter: Callable[[str], str] | None = None,
) -> str:
    """Serialize a Python dict to a gum-formatted string.

    Top-level entries are rendered as ``key = value`` pairs, one per logical
    entry. Nested structures (dicts, lists) may span multiple lines depending
    on the heuristics in _serialize_dict and _serialize_list.

    Args:
        data: The dictionary to serialize. Must have string keys.
        indent: Number of spaces per indentation level (default 2).
        key_formatter: Optional callable to format keys (e.g., for bare_keys
            support where valid identifiers omit quotes).

    Returns:
        A gum-formatted string terminated by a newline, or empty string for
        empty/falsy input.

    Raises:
        TypeError: If any value has an unsupported type (see _serialize_value).
    """
    if not data:
        return ""
    lines: list[str] = []
    for k, v in data.items():
        val_lines = _serialize_value(v, 0, indent, key_formatter)
        for i, line in enumerate(val_lines):
            if i == 0:
                key_str = key_formatter(k) if key_formatter else k
                lines.append(f"{key_str} = {line}")
            else:
                lines.append(line)
    return "\n".join(lines) + "\n"


def _serialize_value(
    value: Any, depth: int, indent: int, key_formatter: Callable[[str], str] | None = None
) -> list[str]:
    """Serialize a single Python value into one or more output lines.

    Dispatches to the appropriate serializer based on the value's type.
    Each type maps to a specific gum literal or structural form.

    Args:
        value: The Python value to serialize. Supported types: None, bool,
            int, float, str, list, dict.
        depth: Current nesting depth (0 for top-level). Used to calculate
            indentation for multi-line structures.
        indent: Number of spaces per indentation level.
        key_formatter: Optional callable to format dict keys. Passed through
            to _serialize_dict when value is a dict.

    Returns:
        A list of strings, one per output line. Simple values return a
        single-element list; nested structures may return multiple lines.

    Raises:
        TypeError: If the value's type is not one of the supported types.
    """
    if value is None:
        return ["null"]
    elif isinstance(value, bool):
        return ["true" if value else "false"]
    elif isinstance(value, (int, float)):
        return [str(value)]
    elif isinstance(value, str):
        return [_serialize_string(value)]
    elif isinstance(value, list):
        return _serialize_list(value, depth, indent, key_formatter)
    elif isinstance(value, dict):
        return _serialize_dict(value, depth, indent, key_formatter)
    else:
        raise TypeError(f"Unsupported type: {type(value)}")


def _serialize_string(value: str) -> str:
    """Serialize a string value with spec-defined escapes only.

    Chooses between triple-quoted multiline form and single-line quoted form
    based on the string's content. Only spec-defined escape sequences are
    used; forward slashes are never escaped.

    Args:
        value: The Python string to serialize.

    Returns:
        A gum-formatted string literal, either triple-quoted or double-quoted
        with escape sequences.

    Escape strategy:
        - Triple-quoted form is used when the string contains newlines AND
          does not itself contain triple quotes (which would break the syntax).
        - Single-line quoted form uses escape sequences for control characters
          and special characters per the gum specification.
    """
    # Triple-quoted multiline: preferred for strings with embedded newlines,
    # but only safe when the string doesn't contain triple quotes itself.
    if "\n" in value and '"""' not in value:
        return '"""\n' + value + '"""'
    # Single-line quoted form: build escape sequence character by character.
    escaped: list[str] = []
    for ch in value:
        code = ord(ch)
        # Backslash must be escaped first to avoid double-escaping
        if code == 0x5c:
            escaped.append("\\\\")
        # Double quote needs escaping inside quoted strings
        elif code == 0x22:
            escaped.append('\\"')
        # Named escape sequences for common control characters
        elif code == 0x08:
            escaped.append("\\b")
        elif code == 0x0c:
            escaped.append("\\f")
        elif code == 0x0a:
            escaped.append("\\n")
        elif code == 0x0d:
            escaped.append("\\r")
        elif code == 0x09:
            escaped.append("\\t")
        # Other control characters (0x00-0x1f, 0x7f) use \\uXXXX form
        elif code < 0x20 or code == 0x7f:
            escaped.append(f"\\u{code:04x}")
        # All other characters pass through unchanged (including /)
        else:
            escaped.append(ch)
    return f'"{"".join(escaped)}"'


def _serialize_list(
    lst: list[Any], depth: int, indent: int, key_formatter: Callable[[str], str] | None = None
) -> list[str]:
    """Serialize a list, choosing inline or multiline format based on heuristics.

    The heuristic favors compact inline format ``[a, b, c]`` for short lists
    of simple scalar values, and falls back to multi-line bracket format for
    anything more complex.

    Args:
        lst: The Python list to serialize.
        depth: Current nesting depth, used for indentation calculation.
        indent: Number of spaces per indentation level.
        key_formatter: Optional callable to format dict keys within list items.

    Returns:
        A list of output lines. Inline lists return a single-element list;
        multi-line lists return opening bracket, indented items, and closing
        bracket as separate elements.

    Inline heuristic:
        A list is rendered inline when ALL of the following are true:
        - Every element is a scalar (str, int, float, bool, or None)
        - The list has at most 4 elements
        - The combined string length of all elements is under 40 characters
        Otherwise, multi-line format is used.
    """
    if not lst:
        return ["[]"]
    # Check if all elements are simple scalar types (no nested lists/dicts)
    simple = all(isinstance(v, (str, int, float, bool, type(None))) for v in lst)
    # Inline format: short list of scalars with compact total width
    if simple and len(lst) <= 4 and sum(len(str(v)) for v in lst) < 40:
        inner = ", ".join(_serialize_value(v, depth, indent, key_formatter)[0] for v in lst)
        return ["[" + inner + "]"]
    # Multi-line format: each element on its own indented line
    lines: list[str] = ["["]
    for v in lst:
        val_lines = _serialize_value(v, depth + 1, indent, key_formatter)
        for line in val_lines:
            lines.append(" " * indent * (depth + 1) + line)
    lines.append(" " * indent * depth + "]")
    return lines


def _serialize_dict(
    d: dict[str, Any],
    depth: int,
    indent: int,
    key_formatter: Callable[[str], str] | None = None,
) -> list[str]:
    """Serialize a dict, choosing inline or multiline format based on heuristics.

    The heuristic favors compact inline format ``{ k1 = v1, k2 = v2 }`` for
    small tables with only scalar values, and falls back to multi-line brace
    format for anything more complex.

    Args:
        d: The Python dict to serialize.
        depth: Current nesting depth, used for indentation calculation.
        indent: Number of spaces per indentation level.
        key_formatter: Optional callable to format keys (e.g., for bare_keys
            support where valid identifiers omit quotes).

    Returns:
        A list of output lines. Inline dicts return a single-element list;
        multi-line dicts return opening brace, indented key-value pairs, and
        closing brace as separate elements.

    Inline heuristic:
        A dict is rendered inline when ALL of the following are true:
        - Every value is a scalar (str, int, float, bool, or None)
        - The dict has at most 3 entries
        Otherwise, multi-line format is used.
    """
    if not d:
        return ["{}"]
    # Check if all values are simple scalar types (no nested lists/dicts)
    all_simple = all(
        isinstance(v, (str, int, float, bool, type(None))) for v in d.values()
    )
    # Inline format: small table with only scalar values
    if all_simple and len(d) <= 3:
        items: list[str] = []
        for k, v in d.items():
            key_str = key_formatter(k) if key_formatter else k
            items.append(f"{key_str} = {_serialize_value(v, depth, indent, key_formatter)[0]}")
        return ["{ " + ", ".join(items) + " }"]
    # Multi-line format: each key-value pair on its own indented line
    lines: list[str] = ["{"]
    for k, v in d.items():
        val_lines = _serialize_value(v, depth + 1, indent, key_formatter)
        key_str = key_formatter(k) if key_formatter else k
        first = True
        for line in val_lines:
            if first:
                # First line of value includes the key assignment
                lines.append(" " * indent * (depth + 1) + f"{key_str} = {line}")
                first = False
            else:
                # Continuation lines (from nested multi-line values) are indented
                # but have no key prefix
                lines.append(" " * indent * (depth + 1) + line)
    lines.append(" " * indent * depth + "}")
    return lines
