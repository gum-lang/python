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
    """Parse a gum-formatted string and return a Python object.

    Mirrors the json.loads() API.

    Args:
        s: The gum-formatted string to parse.
        object_pairs_hook: Optional callable to process key-value pairs.
            Called with list of (key, value) pairs, should return processed dict.
        object_hook: Optional callable to process dicts.
            Called with dict, should return processed object.

    Returns:
        Parsed Python object (typically dict).

    Raises:
        GumDecodeError: If parsing fails due to syntax or semantic errors.

    Example:
        >>> config = gum.loads('name = "my-app"\nversion = 1')
        >>> print(config["name"])
        my-app
    """
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
    """Parse a gum-formatted file and return a Python object.

    Mirrors the json.load() API.

    Args:
        fp: A file-like object with a read() method, or a Path object.
        object_pairs_hook: Optional callable to process key-value pairs.
            Called with list of (key, value) pairs, should return processed dict.
        object_hook: Optional callable to process dicts.
            Called with dict, should return processed object.

    Returns:
        Parsed Python object (typically dict).

    Raises:
        GumDecodeError: If parsing fails due to syntax or semantic errors.
            Error message includes filename if available.
        TypeError: If fp is not a file-like object or Path.

    Example:
        >>> from pathlib import Path
        >>> config = gum.load(Path("config.gum"))
    """
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
    """Serialize a Python object to a gum-formatted string.

    Mirrors the json.dumps() API.

    Args:
        data: The Python object to serialize (typically dict).
        indent: Number of spaces for indentation (default 2).
        bare_keys: If True, use bare keys when possible (default True).
            If False, always quote keys.

    Returns:
        Gum-formatted string representation.

    Example:
        >>> config = {"name": "my-app", "version": 1}
        >>> print(gum.dumps(config))
        name = "my-app"
        version = 1
    """
    encoder = GumEncoder(indent=indent, bare_keys=bare_keys)
    return encoder.encode(data)


def dump(
    data: Any, fp: TextIO, indent: int = 2, bare_keys: bool = True
) -> None:
    """Serialize a Python object to a gum-formatted file.

    Mirrors the json.dump() API.

    Args:
        data: The Python object to serialize (typically dict).
        fp: A file-like object with a write() method.
        indent: Number of spaces for indentation (default 2).
        bare_keys: If True, use bare keys when possible (default True).
            If False, always quote keys.

    Example:
        >>> config = {"name": "my-app", "version": 1}
        >>> with open("config.gum", "w") as f:
        ...     gum.dump(config, f)
    """
    encoder = GumEncoder(indent=indent, bare_keys=bare_keys)
    fp.write(encoder.encode(data))


class GumDecoder:
    """Decoder for gum-formatted strings with optional object hooks.

    Provides a configurable interface for parsing gum markup, allowing
    custom processing of dicts and key-value pairs via hooks.

    Args:
        object_pairs_hook: Optional callable invoked with list of (key, value)
            pairs. Should return the processed dict. Takes precedence over
            object_hook if both are provided.
        object_hook: Optional callable invoked with dict. Should return the
            processed object (e.g., custom class instance).

    Example:
        >>> from collections import OrderedDict
        >>> decoder = GumDecoder(object_pairs_hook=OrderedDict)
        >>> result = decoder.decode("a = 1\nb = 2")
        >>> isinstance(result, OrderedDict)
        True
    """

    def __init__(
        self,
        *,
        object_pairs_hook: Callable[[list[tuple[str, Any]]], Any] | None = None,
        object_hook: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self.object_pairs_hook = object_pairs_hook
        self.object_hook = object_hook

    def decode(self, s: str) -> Any:
        """Parse a gum-formatted string and return a Python object.

        Args:
            s: The gum-formatted string to parse.

        Returns:
            Parsed Python object (typically dict).

        Raises:
            GumDecodeError: If parsing fails due to syntax or semantic errors.
        """
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
    """Encoder for serializing Python objects to gum-formatted strings.

    Provides a configurable interface for generating gum markup with
    control over formatting and key representation.

    Args:
        indent: Number of spaces for indentation (default 2).
        bare_keys: If True, use bare keys when valid per spec (default True).
            Bare keys must match [A-Za-z_][A-Za-z0-9_]* and not be reserved
            keywords (true, false, null). If False, always quote keys.

    Example:
        >>> encoder = GumEncoder(indent=4, bare_keys=True)
        >>> result = encoder.encode({"name": "my-app", "version": 1})
        >>> print(result)
        name = "my-app"
        version = 1
    """

    def __init__(self, *, indent: int = 2, bare_keys: bool = True) -> None:
        self.indent = indent
        self.bare_keys = bare_keys

    def encode(self, obj: Any) -> str:
        """Serialize a Python object to a gum-formatted string.

        Args:
            obj: The Python object to serialize (typically dict).

        Returns:
            Gum-formatted string representation.
        """
        return serialize(obj, indent=self.indent, key_formatter=self._format_key)

    def _format_key(self, key: str) -> str:
        if self.bare_keys and _BARE_KEY_RE.match(key) and key not in _RESERVED_KEYS:
            return key
        return self._escape_string(key)

    def _escape_string(self, value: str) -> str:
        return _serialize_string(value)
