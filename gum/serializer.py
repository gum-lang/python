"""Serializer for the gum configuration file format.

Converts Python dicts back to gum-formatted strings.
- Uses spec-defined escapes only (no \\/)
- Multi-line strings use triple-quote syntax
- Heuristic for inline vs multi-line tables/lists
"""
from __future__ import annotations

from typing import Any, Callable


def serialize(
    data: dict[str, Any],
    indent: int = 2,
    key_formatter: Callable[[str], str] | None = None,
) -> str:
    """Serialize a Python dict to a gum-formatted string.

    Args:
        data: The dictionary to serialize.
        indent: Number of spaces per indentation level.
        key_formatter: Optional callable to format keys (e.g., for bare_keys support).

    Returns:
        A gum-formatted string, or empty string for empty input.
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
    """Serialize a single Python value into one or more output lines."""
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

    Uses triple-quoted multiline syntax if the string contains newlines
    and does not contain triple quotes. Otherwise uses quoted form with
    escape sequences for control characters and special characters.
    """
    if "\n" in value and '"""' not in value:
        return '"""\n' + value + '"""'
    escaped: list[str] = []
    for ch in value:
        code = ord(ch)
        if code == 0x5c:
            escaped.append("\\\\")
        elif code == 0x22:
            escaped.append('\\"')
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
        elif code < 0x20 or code == 0x7f:
            escaped.append(f"\\u{code:04x}")
        else:
            escaped.append(ch)
    return f'"{"".join(escaped)}"'


def _serialize_list(
    lst: list[Any], depth: int, indent: int, key_formatter: Callable[[str], str] | None = None
) -> list[str]:
    """Serialize a list, choosing inline or multiline format based on heuristics."""
    if not lst:
        return ["[]"]
    simple = all(isinstance(v, (str, int, float, bool, type(None))) for v in lst)
    if simple and len(lst) <= 4 and sum(len(str(v)) for v in lst) < 40:
        inner = ", ".join(_serialize_value(v, depth, indent, key_formatter)[0] for v in lst)
        return ["[" + inner + "]"]
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
    """Serialize a dict, choosing inline or multiline format based on heuristics."""
    if not d:
        return ["{}"]
    all_simple = all(
        isinstance(v, (str, int, float, bool, type(None))) for v in d.values()
    )
    if all_simple and len(d) <= 3:
        items: list[str] = []
        for k, v in d.items():
            key_str = key_formatter(k) if key_formatter else k
            items.append(f"{key_str} = {_serialize_value(v, depth, indent, key_formatter)[0]}")
        return ["{ " + ", ".join(items) + " }"]
    lines: list[str] = ["{"]
    for k, v in d.items():
        val_lines = _serialize_value(v, depth + 1, indent, key_formatter)
        key_str = key_formatter(k) if key_formatter else k
        first = True
        for line in val_lines:
            if first:
                lines.append(" " * indent * (depth + 1) + f"{key_str} = {line}")
                first = False
            else:
                lines.append(" " * indent * (depth + 1) + line)
    lines.append(" " * indent * depth + "}")
    return lines
