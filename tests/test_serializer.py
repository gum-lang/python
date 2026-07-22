from gum import dumps, loads


def test_empty():
    assert dumps({}) == ""


def test_simple_key_value():
    assert dumps({"key": "value"}) == 'key = "value"\n'


def test_integer():
    assert dumps({"n": 42}) == "n = 42\n"


def test_float():
    assert dumps({"n": 3.14}) == "n = 3.14\n"


def test_bool():
    assert dumps({"flag": True}) == "flag = true\n"
    assert dumps({"flag": False}) == "flag = false\n"


def test_null():
    assert dumps({"v": None}) == "v = null\n"


def test_inline_table():
    result = dumps({"tbl": {"x": 1, "y": "two"}})
    assert "tbl" in result


def test_array():
    result = dumps({"arr": [1, 2, 3]})
    assert "[" in result


def test_roundtrip():
    data = {
        "name": "test",
        "version": 1,
        "features": {"a": True, "b": False},
        "tags": ["x", "y"],
    }
    gum_str = dumps(data)
    parsed = loads(gum_str)
    assert parsed == data


def test_multiline_with_triple_quotes_roundtrip():
    data = {"s": "hello\n\"\"\"world"}
    gum_str = dumps(data)
    reparsed = loads(gum_str)
    assert reparsed == data
