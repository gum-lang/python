from gum.tokenizer import Tokenizer, GumError
from gum.parser import Parser
from gum.serializer import serialize

__all__ = ["unmarshal", "marshal", "GumError"]


def unmarshal(source) -> dict:
    if hasattr(source, "read"):
        source = source.read()
    elif hasattr(source, "read_text"):
        source = source.read_text()
    return Parser(Tokenizer(source)).parse()


def marshal(data: dict) -> str:
    return serialize(data)
