from gum.parser import Parser
from gum.tokenizer import Tokenizer, GumError
import pytest


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


def test_duplicate_key_error():
    with pytest.raises(GumError, match="(?i)duplicate"):
        parse("a = 1\na = 2")


def test_type_conflict_dotted_path():
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


def test_whitespace_between_assignments():
    result = parse("a = 1  b = 2")
    assert result == {"a": 1, "b": 2}


def test_reserved_keyword_true_as_key():
    with pytest.raises(GumError, match="(?i)reserved"):
        parse("true = 1")


def test_reserved_keyword_false_as_key():
    with pytest.raises(GumError, match="(?i)reserved"):
        parse("false = 1")


def test_reserved_keyword_null_as_key():
    with pytest.raises(GumError, match="(?i)reserved"):
        parse("null = 1")


def test_multiple_whitespace_between_assignments():
    result = parse("a = 1     b = 2     c = 3")
    assert result == {"a": 1, "b": 2, "c": 3}


def test_mixed_whitespace_and_newline_between_assignments():
    result = parse("a = 1  \n  b = 2\n  c = 3")
    assert result == {"a": 1, "b": 2, "c": 3}


def test_path_conflict_string_to_table():
    src = "name = \"Alice\"\nname.first = \"Bob\""
    with pytest.raises(GumError, match="(?i)conflict"):
        parse(src)


def test_path_conflict_table_to_string():
    src = "a.b = 1\na = \"hello\""
    with pytest.raises(GumError, match="(?i)conflict"):
        parse(src)


def test_path_conflict_table_to_table():
    src = "a.b = 1\na = {}"
    with pytest.raises(GumError, match="(?i)duplicate"):
        parse(src)


def test_inline_table_subkey_reassignment():
    src = "tbl = { x = 1 }\ntbl.x = 2"
    with pytest.raises(GumError, match="(?i)redefin"):
        parse(src)


def test_inline_table_replacement():
    src = "tbl = { x = 1 }\ntbl = 2"
    with pytest.raises(GumError, match="(?i)redefin"):
        parse(src)


def test_adding_subkey_to_inline_table():
    """Adding new sub-keys to existing table is allowed."""
    result = parse("tbl = { x = 1 }\ntbl.y = 2")
    assert result == {"tbl": {"x": 1, "y": 2}}


def test_nested_inline_table_subkey_reassignment():
    """Nested inline tables should also be protected from redefinition."""
    src = "tbl = { nested = { x = 1 } }\ntbl.nested.x = 2"
    with pytest.raises(GumError, match="(?i)redefin"):
        parse(src)


def test_large_int_parsed():
    """Python handles arbitrary precision ints, so this just verifies parsing."""
    result = parse("n = 99999999999999999999999")
    assert result == {"n": 99999999999999999999999}


def test_hex_parsed():
    result = parse("n = 0xFF")
    assert result == {"n": 255}


def test_binary_parsed():
    result = parse("n = 0b1010")
    assert result == {"n": 10}


def test_octal_parsed():
    result = parse("n = 0o755")
    assert result == {"n": 493}


def test_scientific_parsed():
    result = parse("n = 1e10")
    assert result == {"n": 1e10}


def test_explicit_positive_parsed():
    result = parse("n = +42")
    assert result == {"n": 42}


def test_underscore_number_parsed():
    result = parse("n = 1_000_000")
    assert result == {"n": 1000000}
