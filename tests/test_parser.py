from gum.parser import Parser
from gum.tokenizer import Tokenizer


def parse(src):
    return Parser(Tokenizer(src)).parse()


def test_empty():
    assert parse("") == {}


def test_simple_key_value():
    assert parse('key = "value"') == {"key": "value"}


def test_integer():
    assert parse("n = 42") == {"n": 42}


def test_float():
    assert parse("n = 3.14") == {"n": 3.14}


def test_negative():
    assert parse("n = -17") == {"n": -17}


def test_bool_true():
    assert parse("flag = true") == {"flag": True}


def test_bool_false():
    assert parse("flag = false") == {"flag": False}


def test_null():
    assert parse("v = null") == {"v": None}


def test_dotted_path():
    result = parse("""a.b.c = 1
a.b.d = 2""")
    assert result == {"a": {"b": {"c": 1, "d": 2}}}


def test_inline_table():
    result = parse('tbl = { x = 1, y = "two" }')
    assert result == {"tbl": {"x": 1, "y": "two"}}


def test_multiline_table():
    src = """tbl = {
  x = 1
  y = "two"
}"""
    result = parse(src)
    assert result == {"tbl": {"x": 1, "y": "two"}}


def test_nested_table():
    src = """tbl = {
  host = "localhost"
  port = 5432
  credentials = {
    user = "admin"
    password = null
  }
}"""
    result = parse(src)
    assert result == {"tbl": {"host": "localhost", "port": 5432, "credentials": {"user": "admin", "password": None}}}


def test_array():
    assert parse("arr = [1, 2, 3]") == {"arr": [1, 2, 3]}


def test_multiline_array():
    src = """colors = [
  "red"
  "yellow"
  "green"
]"""
    result = parse(src)
    assert result == {"colors": ["red", "yellow", "green"]}


def test_nested_array():
    src = "nested = [[1, 2], [3, 4, 5]]"
    result = parse(src)
    assert result == {"nested": [[1, 2], [3, 4, 5]]}


def test_mixed_array():
    src = 'mixed = [1, "two", true, null, { x = 1 }]'
    result = parse(src)
    assert result == {"mixed": [1, "two", True, None, {"x": 1}]}


def test_comment_in_table():
    src = """tbl = {
  # comment
  x = 1
}"""
    result = parse(src)
    assert result == {"tbl": {"x": 1}}


def test_comment_in_array():
    src = """arr = [
  1
  # comment
  2
]"""
    result = parse(src)
    assert result == {"arr": [1, 2]}


def test_trailing_comma():
    assert parse("tbl = { x = 1, }") == {"tbl": {"x": 1}}
    assert parse("arr = [1,]") == {"arr": [1]}


def test_dotted_into_existing_table():
    src = """fruit.apple.smooth = true
fruit.orange = 2"""
    result = parse(src)
    assert result == {"fruit": {"apple": {"smooth": True}, "orange": 2}}


def test_quoted_key():
    assert parse('"foo.bar" = null') == {"foo.bar": None}


def test_string_with_escape():
    assert parse(r's = "hello\nworld"') == {"s": "hello\nworld"}


def test_unicode_escape():
    assert parse(r's = "\u0041"') == {"s": "A"}


def test_multiline_string():
    src = 's = """hello\nworld"""'
    result = parse(src)
    assert result == {"s": "hello\nworld"}


def test_empty_table():
    assert parse("t = {}") == {"t": {}}


def test_empty_array():
    assert parse("a = []") == {"a": []}


def test_duplicate_key_overwrites():
    assert parse("a = 1\na = 2") == {"a": 2}


def test_type_conflict_dotted_path():
    import pytest
    from gum.tokenizer import GumError
    src = "a = 1\na.b = 2"
    with pytest.raises(GumError):
        parse(src)


def test_leading_dot_number():
    assert parse("n = .5") == {"n": 0.5}


def test_trailing_dot_number():
    assert parse("n = 2.") == {"n": 2.0}


def test_full_example():
    src = """name = "banana"
physical.color = "yellow"
physical.shape = "banana-shaped"
"""
    result = parse(src)
    assert result == {
        "name": "banana",
        "physical": {
            "color": "yellow",
            "shape": "banana-shaped",
        }
    }


def test_spec_example():
    src = """# camel config example
name = "camel-parser"
version = 1

author.name = "Alice"
author.email = "alice@example.com"

features = {
  strict = true
  logging = false
  max_retries = 3
  tags = ["dev", "prod"]
}

database = {
  host = "localhost"
  port = 5432
  credentials = {
    user = "admin"
    password = null
  }
}

description = \"\"\"This is camel.
It is markup everyone likes.\"\"\""""
    result = parse(src)
    assert result == {
        "name": "camel-parser",
        "version": 1,
        "author": {"name": "Alice", "email": "alice@example.com"},
        "features": {"strict": True, "logging": False, "max_retries": 3, "tags": ["dev", "prod"]},
        "database": {"host": "localhost", "port": 5432, "credentials": {"user": "admin", "password": None}},
        "description": "This is camel.\nIt is markup everyone likes.",
    }


def test_multiline_string_dedent():
    src = 's = """\n  hello\n  world\n  """'
    result = parse(src)
    assert result == {"s": "hello\nworld"}


def test_multiline_string_no_dedent():
    src = 's = """hello\nworld"""'
    result = parse(src)
    assert result == {"s": "hello\nworld"}


def test_comma_separated_top_level():
    result = parse('a = 1, b = 2')
    assert result == {"a": 1, "b": 2}


def test_comma_separated_no_whitespace():
    result = parse('x=1,a=2')
    assert result == {"x": 1, "a": 2}


def test_comma_separated_extra_whitespace():
    result = parse('x  =  1  ,  a  =  2')
    assert result == {"x": 1, "a": 2}


def test_mixed_separators():
    result = parse('a = 1, b = 2\nc = 3')
    assert result == {"a": 1, "b": 2, "c": 3}


def test_trailing_comma_document():
    assert parse('a = 1, b = 2,') == {"a": 1, "b": 2}


def test_comma_with_dotted_paths():
    result = parse('a.b.c = 1, a.b.d = 2')
    assert result == {"a": {"b": {"c": 1, "d": 2}}}
