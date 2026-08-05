from __future__ import annotations

import re
from pathlib import Path
from typing import IO, Any, Callable, TextIO

from gum._errors import GumDecodeError
from gum.parser import Parser
from gum.serializer import _serialize_string, serialize
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
) -> Any:
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
) -> Any:
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


def dumps(data: Any, indent: int = 2, bare_keys: bool = True) -> str:
    encoder = GumEncoder(indent=indent, bare_keys=bare_keys)
    return encoder.encode(data)


def dump(
    data: Any, fp: TextIO, indent: int = 2, bare_keys: bool = True
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

    def decode(self, s: str) -> Any:
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

    def encode(self, obj: Any) -> str:
        return serialize(obj, indent=self.indent, key_formatter=self._format_key)

    def _format_key(self, key: str) -> str:
        if self.bare_keys and _BARE_KEY_RE.match(key) and key not in _RESERVED_KEYS:
            return key
        return self._escape_string(key)

    def _escape_string(self, value: str) -> str:
        return _serialize_string(value)
