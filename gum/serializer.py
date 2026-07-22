from __future__ import annotations

from typing import Any


def serialize(data: dict[str, Any], indent: int = 2) -> str:
    if not data:
        return ""
    lines: list[str] = []
    for k, v in data.items():
        val_lines = _serialize_value(v, 0, indent)
        for i, line in enumerate(val_lines):
            if i == 0:
                lines.append(f"{k} = {line}")
            else:
                lines.append(line)
    return "\n".join(lines) + "\n"


def _serialize_value(value: Any, depth: int, indent: int) -> list[str]:
    if value is None:
        return ["null"]
    elif isinstance(value, bool):
        return ["true" if value else "false"]
    elif isinstance(value, (int, float)):
        return [str(value)]
    elif isinstance(value, str):
        return [_serialize_string(value)]
    elif isinstance(value, list):
        return _serialize_list(value, depth, indent)
    elif isinstance(value, dict):
        return _serialize_dict(value, depth, indent)
    else:
        raise TypeError(f"Unsupported type: {type(value)}")


def _serialize_string(value: str) -> str:
    if "\n" in value:
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


def _serialize_list(lst: list[Any], depth: int, indent: int) -> list[str]:
    if not lst:
        return ["[]"]
    simple = all(isinstance(v, (str, int, float, bool, type(None))) for v in lst)
    if simple and len(lst) <= 4 and sum(len(str(v)) for v in lst) < 40:
        inner = ", ".join(_serialize_value(v, depth, indent)[0] for v in lst)
        return ["[" + inner + "]"]
    lines: list[str] = ["["]
    for v in lst:
        val_lines = _serialize_value(v, depth + 1, indent)
        for line in val_lines:
            lines.append(" " * indent * (depth + 1) + line)
    lines.append(" " * indent * depth + "]")
    return lines


def _serialize_dict(d: dict[str, Any], depth: int, indent: int) -> list[str]:
    if not d:
        return ["{}"]
    all_simple = all(
        isinstance(v, (str, int, float, bool, type(None))) for v in d.values()
    )
    if all_simple and len(d) <= 3:
        items: list[str] = []
        for k, v in d.items():
            items.append(f"{k} = {_serialize_value(v, depth, indent)[0]}")
        return ["{ " + ", ".join(items) + " }"]
    lines: list[str] = ["{"]
    for k, v in d.items():
        val_lines = _serialize_value(v, depth + 1, indent)
        first = True
        for line in val_lines:
            if first:
                lines.append(" " * indent * (depth + 1) + f"{k} = {line}")
                first = False
            else:
                lines.append(" " * indent * (depth + 1) + line)
    lines.append(" " * indent * depth + "}")
    return lines
