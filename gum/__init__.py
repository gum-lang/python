from __future__ import annotations

import re
from pathlib import Path
from typing import IO, Any, Callable, TextIO

from gum._errors import GumDecodeError
from gum.parser import Parser
from gum.serializer import serialize
from gum.tokenizer import GumError, Tokenizer

_BARE_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RESERVED_KEYS = {"true", "false", "null"}

__all__ = [
    "GumDecodeError",
    "GumDecoder",
    "GumEncoder",
    "GumError",
    "dump",
    "dumps",
    "load",
    "loads",
]


def loads(
    s: str,
    *,
    object_pairs_hook: Callable[[list[tuple[str, Any]]], Any] | None = None,
    object_hook: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    decoder = GumDecoder(
        object_pairs_hook=object_pairs_hook,
        object_hook=object_hook,
    )
    return decoder.decode(s)


def load(
    fp: IO[str] | Path,
    *,
    object_pairs_hook: Callable[[list[tuple[str, Any]]], Any] | None = None,
    object_hook: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    filename: str | None = None
    if isinstance(fp, Path):
        source = fp.read_text()
        filename = str(fp)
    elif hasattr(fp, "read"):
        source = fp.read()
        if hasattr(fp, "name"):
            filename = fp.name
    else:
        raise TypeError(f"Expected file-like object or Path, got {type(fp)}")
    try:
        return loads(
            source,
            object_pairs_hook=object_pairs_hook,
            object_hook=object_hook,
        )
    except GumError as e:
        if filename:
            raise GumError(f"{filename}: {e.message}", e.line, e.col) from e
        raise


def dumps(data: dict[str, Any], *, indent: int = 2, bare_keys: bool = True) -> str:
    encoder = GumEncoder(indent=indent, bare_keys=bare_keys)
    return encoder.encode(data)


def dump(
    data: dict[str, Any], fp: TextIO, *, indent: int = 2, bare_keys: bool = True
) -> None:
    encoder = GumEncoder(indent=indent, bare_keys=bare_keys)
    fp.write(encoder.encode(data))


class GumDecoder:
    def __init__(
        self,
        *,
        object_pairs_hook: Callable[[list[tuple[str, Any]]], Any] | None = None,
        object_hook: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self.object_pairs_hook = object_pairs_hook
        self.object_hook = object_hook

    def decode(self, s: str) -> dict[str, Any]:
        result = Parser(Tokenizer(s)).parse()
        return self._apply_hooks(result)

    def _apply_hooks(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            processed = {k: self._apply_hooks(v) for k, v in obj.items()}
            if self.object_pairs_hook is not None:
                return self.object_pairs_hook(list(processed.items()))
            if self.object_hook is not None:
                return self.object_hook(processed)
            return processed
        if isinstance(obj, list):
            return [self._apply_hooks(item) for item in obj]
        return obj


class GumEncoder:
    def __init__(self, *, indent: int = 2, bare_keys: bool = True) -> None:
        self.indent = indent
        self.bare_keys = bare_keys

    def encode(self, obj: dict[str, Any]) -> str:
        if not obj:
            return ""
        lines: list[str] = []
        for k, v in obj.items():
            val_lines = self._serialize_value(v, 0)
            key_str = self._format_key(k)
            for i, line in enumerate(val_lines):
                if i == 0:
                    lines.append(f"{key_str} = {line}")
                else:
                    lines.append(line)
        return "\n".join(lines) + "\n"

    def _format_key(self, key: str) -> str:
        if self.bare_keys and _BARE_KEY_RE.match(key) and key not in _RESERVED_KEYS:
            return key
        return self._escape_string(key)

    def _serialize_value(self, value: Any, depth: int) -> list[str]:
        if value is None:
            return ["null"]
        if isinstance(value, bool):
            return ["true" if value else "false"]
        if isinstance(value, (int, float)):
            return [str(value)]
        if isinstance(value, str):
            return [self._serialize_string(value)]
        if isinstance(value, list):
            return self._serialize_list(value, depth)
        if isinstance(value, dict):
            return self._serialize_dict(value, depth)
        raise TypeError(f"Unsupported type: {type(value)}")

    def _serialize_string(self, value: str) -> str:
        if "\n" in value and '"""' not in value:
            return '"""\n' + value + '"""'
        return self._escape_string(value)

    def _escape_string(self, value: str) -> str:
        escaped: list[str] = []
        for ch in value:
            code = ord(ch)
            if code == 0x5C:
                escaped.append("\\\\")
            elif code == 0x22:
                escaped.append('\\"')
            elif code == 0x08:
                escaped.append("\\b")
            elif code == 0x0C:
                escaped.append("\\f")
            elif code == 0x0A:
                escaped.append("\\n")
            elif code == 0x0D:
                escaped.append("\\r")
            elif code == 0x09:
                escaped.append("\\t")
            elif code < 0x20 or code == 0x7F:
                escaped.append(f"\\u{code:04x}")
            else:
                escaped.append(ch)
        return f'"{"".join(escaped)}"'

    def _serialize_list(self, lst: list[Any], depth: int) -> list[str]:
        if not lst:
            return ["[]"]
        simple = all(isinstance(v, (str, int, float, bool, type(None))) for v in lst)
        if simple and len(lst) <= 4 and sum(len(str(v)) for v in lst) < 40:
            inner = ", ".join(self._serialize_value(v, depth)[0] for v in lst)
            return ["[" + inner + "]"]
        lines: list[str] = ["["]
        for v in lst:
            val_lines = self._serialize_value(v, depth + 1)
            for line in val_lines:
                lines.append(" " * self.indent * (depth + 1) + line)
        lines.append(" " * self.indent * depth + "]")
        return lines

    def _serialize_dict(self, d: dict[str, Any], depth: int) -> list[str]:
        if not d:
            return ["{}"]
        all_simple = all(
            isinstance(v, (str, int, float, bool, type(None))) for v in d.values()
        )
        if all_simple and len(d) <= 3:
            items: list[str] = []
            for k, v in d.items():
                key_str = self._format_key(k)
                items.append(f"{key_str} = {self._serialize_value(v, depth)[0]}")
            return ["{ " + ", ".join(items) + " }"]
        lines: list[str] = ["{"]
        for k, v in d.items():
            val_lines = self._serialize_value(v, depth + 1)
            key_str = self._format_key(k)
            first = True
            for line in val_lines:
                if first:
                    lines.append(" " * self.indent * (depth + 1) + f"{key_str} = {line}")
                    first = False
                else:
                    lines.append(" " * self.indent * (depth + 1) + line)
        lines.append(" " * self.indent * depth + "}")
        return lines
