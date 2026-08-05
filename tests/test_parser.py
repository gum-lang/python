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


def test_negative_hex():
    result = parse("n = -0xFF")
    assert result == {"n": -255}


def test_negative_binary():
    result = parse("n = -0b1010")
    assert result == {"n": -10}


def test_negative_octal():
    result = parse("n = -0o755")
    assert result == {"n": -493}


def test_crlf_newlines():
    src = "a = 1\r\nb = 2"
    result = parse(src)
    assert result == {"a": 1, "b": 2}


def test_inline_comment():
    src = 'key = "value" # this is a comment'
    result = parse(src)
    assert result == {"key": "value"}


def test_inline_comment_after_number():
    src = "count = 42 # items"
    result = parse(src)
    assert result == {"count": 42}


def test_whitespace_around_dots_not_supported():
    """Whitespace around dots is tokenized as separate DOT tokens; parser expects key after dot."""
    with pytest.raises(GumError):
        parse("a . b . c = 1")


def test_empty_string_value():
    result = parse('s = ""')
    assert result == {"s": ""}


def test_multiple_consecutive_newlines():
    src = "a = 1\n\n\nb = 2"
    result = parse(src)
    assert result == {"a": 1, "b": 2}


def test_escape_backslash():
    result = parse(r'p = "C:\\path\\to\\file"')
    assert result == {"p": "C:\\path\\to\\file"}


def test_escape_backspace():
    result = parse(r's = "hello\bworld"')
    assert result == {"s": "hello\bworld"}


def test_escape_formfeed():
    result = parse(r's = "hello\fworld"')
    assert result == {"s": "hello\fworld"}


def test_escape_carriage_return():
    result = parse(r's = "hello\rworld"')
    assert result == {"s": "hello\rworld"}


def test_escape_tab():
    result = parse(r's = "hello\tworld"')
    assert result == {"s": "hello\tworld"}


def test_escape_quote():
    result = parse(r's = "say \"hello\""')
    assert result == {"s": 'say "hello"'}


def test_escape_unicode_8digit():
    """The main tokenizer supports \\U (8-digit) unicode escapes."""
    result = parse(r's = "\U0001F600"')
    assert result == {"s": "\U0001F600"}


def test_quoted_key_with_period():
    result = parse('"foo.bar" = 1')
    assert result == {"foo.bar": 1}


def test_quoted_key_in_dotted_path():
    result = parse('a."b.c".d = 1')
    assert result == {"a": {"b.c": {"d": 1}}}


def test_dotted_key_whitespace_around_dots_quoted_not_supported():
    """Whitespace around dots is not supported by the parser."""
    with pytest.raises(GumError):
        parse('a . "b.c" . d = 1')


def test_trailing_dot_number_parsed_as_float():
    result = parse("n = 2.")
    assert result == {"n": 2.0}
    assert isinstance(result["n"], float)


def test_leading_dot_number_parsed_as_float():
    result = parse("n = .5")
    assert result == {"n": 0.5}
    assert isinstance(result["n"], float)


def test_scientific_notation_parsed_as_float():
    result = parse("n = 1e10")
    assert result == {"n": 1e10}
    assert isinstance(result["n"], float)


def test_signed_float():
    result = parse("n = -3.14")
    assert result == {"n": -3.14}
    assert isinstance(result["n"], float)


def test_positive_float():
    result = parse("n = +3.14")
    assert result == {"n": 3.14}
    assert isinstance(result["n"], float)


def test_nested_empty_list():
    result = parse("a = [[]]")
    assert result == {"a": [[]]}


def test_nested_empty_table():
    result = parse("t = { inner = {} }")
    assert result == {"t": {"inner": {}}}


def test_list_trailing_comma():
    result = parse("a = [1, 2, 3,]")
    assert result == {"a": [1, 2, 3]}


def test_table_trailing_comma():
    result = parse("t = { a = 1, b = 2, }")
    assert result == {"t": {"a": 1, "b": 2}}


def test_duplicate_key_in_table():
    with pytest.raises(GumError, match="(?i)duplicate"):
        parse("t = { a = 1, a = 2 }")


def test_duplicate_key_in_list_values():
    # Lists can have duplicate values, that's fine
    result = parse("a = [1, 1, 1]")
    assert result == {"a": [1, 1, 1]}


def test_multiline_string_first_line_strip():
    src = 's = """\nhello\nworld\n"""'
    result = parse(src)
    assert result == {"s": "hello\nworld"}


def test_multiline_string_with_escapes():
    src = r's = """hello\nworld"""'
    result = parse(src)
    assert result == {"s": "hello\nworld"}


def test_multiline_string_line_continuation():
    """Line continuation (backslash + newline) is supported in multiline strings."""
    result = parse('s = """hello \\\nworld"""')
    assert result == {"s": "hello world"}


def test_reserved_word_in_quoted_key():
    result = parse('"true" = 1')
    assert result == {"true": 1}


def test_bare_key_underscore_start():
    result = parse("_key = 1")
    assert result == {"_key": 1}


def test_bare_key_underscore_only():
    result = parse("_ = 1")
    assert result == {"_": 1}


def test_crlf_in_multiline_string():
    src = 's = """\r\nhello\r\nworld\r\n"""'
    result = parse(src)
    assert result == {"s": "hello\nworld"}
    assert "\r" not in result["s"]


def test_only_whitespace_and_comments():
    src = "# just a comment\n  \n# another comment\n"
    result = parse(src)
    assert result == {}


def test_deeply_nested_dotted_keys():
    src = "a.b.c.d.e = 1"
    result = parse(src)
    assert result == {"a": {"b": {"c": {"d": {"e": 1}}}}}


def test_mixed_bare_and_quoted_keys_in_path():
    src = 'a."b-c".d = 1'
    result = parse(src)
    assert result == {"a": {"b-c": {"d": 1}}}


def test_number_with_underscores():
    result = parse("n = 1_000_000")
    assert result == {"n": 1000000}


def test_float_with_underscores():
    result = parse("n = 1_000.2_5")
    assert result == {"n": 1000.25}


def test_scientific_with_underscores():
    result = parse("n = 1_0e1_0")
    assert result == {"n": 10e10}


def test_hex_with_underscores():
    result = parse("n = 0xFF_FF")
    assert result == {"n": 65535}


def test_binary_with_underscores():
    result = parse("n = 0b10_10")
    assert result == {"n": 10}


def test_octal_with_underscores():
    result = parse("n = 0o7_5_5")
    assert result == {"n": 493}
