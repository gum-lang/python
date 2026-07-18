from gum.serializer import serialize


def test_empty():
    assert serialize({}) == ""


def test_simple_key_value():
    assert serialize({"key": "value"}) == 'key = "value"\n'

def test_integer():
    assert serialize({"n": 42}) == "n = 42\n"

def test_float():
    assert serialize({"n": 3.14}) == "n = 3.14\n"

def test_bool():
    assert serialize({"flag": True}) == "flag = true\n"
    assert serialize({"flag": False}) == "flag = false\n"

def test_null():
    assert serialize({"v": None}) == "v = null\n"

def test_inline_table():
    result = serialize({"tbl": {"x": 1, "y": "two"}})
    assert "tbl" in result

def test_array():
    result = serialize({"arr": [1, 2, 3]})
    assert "[" in result

def test_roundtrip():
    from gum.parser import Parser
    from gum.tokenizer import Tokenizer
    data = {
        "name": "test",
        "version": 1,
        "features": {"a": True, "b": False},
        "tags": ["x", "y"],
    }
    gum_str = serialize(data)
    parsed = Parser(Tokenizer(gum_str)).parse()
    assert parsed == data
