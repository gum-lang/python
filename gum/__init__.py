from __future__ import annotations

from pathlib import Path
from typing import IO, Any, TextIO

from gum.parser import Parser
from gum.serializer import serialize
from gum.tokenizer import GumError, Tokenizer

__all__ = [
    "GumError",
    "load",
    "loads",
    "dump",
    "dumps",
]


def loads(s: str) -> dict[str, Any]:
    return Parser(Tokenizer(s)).parse()


def load(fp: IO[str] | Path) -> dict[str, Any]:
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
        return Parser(Tokenizer(source)).parse()
    except GumError as e:
        if filename:
            raise GumError(f"{filename}: {e.message}", e.line, e.col) from e
        raise


def dumps(data: dict[str, Any], indent: int = 2) -> str:
    return serialize(data, indent=indent)


def dump(data: dict[str, Any], fp: TextIO, indent: int = 2) -> None:
    fp.write(serialize(data, indent=indent))
