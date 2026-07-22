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
    if isinstance(fp, Path):
        source = fp.read_text()
    elif hasattr(fp, "read"):
        source = fp.read()
    else:
        raise TypeError(f"Expected file-like object or Path, got {type(fp)}")
    return Parser(Tokenizer(source)).parse()


def dumps(data: dict[str, Any], indent: int = 2) -> str:
    return serialize(data, indent=indent)


def dump(data: dict[str, Any], fp: TextIO, indent: int = 2) -> None:
    fp.write(serialize(data, indent=indent))
