import pytest
from gum.tokenizer import Tokenizer, TokenType, GumError


def test_empty():
    t = Tokenizer("")
    assert t.peek().type == TokenType.EOF


def test_equals():
    t = Tokenizer("=")
    assert t.peek().type == TokenType.EQUALS


def test_braces():
    t = Tokenizer("{}[]")
    assert t.peek().type == TokenType.LBRACE
    t.advance()
    assert t.peek().type == TokenType.RBRACE
    t.advance()
    assert t.peek().type == TokenType.LBRACKET
    t.advance()
    assert t.peek().type == TokenType.RBRACKET


def test_comma_dot():
    t = Tokenizer(".,")
    assert t.peek().type == TokenType.DOT
    t.advance()
    assert t.peek().type == TokenType.COMMA


def test_bare_key():
    t = Tokenizer("foo_bar")
    tok = t.peek()
    assert tok.type == TokenType.IDENT
    assert tok.value == "foo_bar"


def test_number_int():
    t = Tokenizer("42")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "42"


def test_number_float():
    t = Tokenizer("3.14")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "3.14"


def test_number_leading_dot():
    t = Tokenizer(".5")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == ".5"


def test_number_trailing_dot():
    t = Tokenizer("2.")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "2."


def test_number_negative():
    t = Tokenizer("-42")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "-42"


def test_string():
    t = Tokenizer('"hello"')
    tok = t.peek()
    assert tok.type == TokenType.STRING
    assert tok.value == "hello"


def test_string_with_escape():
    t = Tokenizer(r'"hello\nworld"')
    tok = t.peek()
    assert tok.type == TokenType.STRING
    assert tok.value == "hello\nworld"


def test_bool_true():
    t = Tokenizer("true")
    tok = t.peek()
    assert tok.type == TokenType.TRUE


def test_bool_false():
    t = Tokenizer("false")
    tok = t.peek()
    assert tok.type == TokenType.FALSE


def test_null():
    t = Tokenizer("null")
    tok = t.peek()
    assert tok.type == TokenType.NULL


def test_newline():
    t = Tokenizer("\n")
    tok = t.peek()
    assert tok.type == TokenType.NEWLINE


def test_comment_skipped():
    t = Tokenizer("# comment\nkey")
    assert t.peek().type == TokenType.NEWLINE
    t.advance()
    assert t.peek().type == TokenType.IDENT


def test_multiline_string():
    t = Tokenizer('"""hello\nworld"""')
    tok = t.peek()
    assert tok.type == TokenType.STRING
    assert "hello" in tok.value


def test_reserved_keys():
    for keyword in ["true", "false", "null"]:
        t = Tokenizer(keyword)
        assert t.peek().type != TokenType.IDENT


def test_standalone_carriage_return():
    t = Tokenizer("key\r= 1")
    with pytest.raises(GumError):
        t.advance()


def test_position_tracking():
    t = Tokenizer("\n\nfoo")
    t.advance()
    t.advance()
    tok = t.advance()
    assert tok.line == 3


def test_invalid_unicode_escape():
    with pytest.raises(GumError):
        Tokenizer(r'"\uGGGG"')


def test_reject_bare_control_chars():
    # Bell character (U+0007)
    with pytest.raises(GumError):
        Tokenizer('"hello\x07world"')


def test_reject_bare_newline_in_string():
    # Literal newline (U+000A)
    with pytest.raises(GumError):
        Tokenizer('"hello\nworld"')


def test_reject_bare_delete_char():
    # DEL character (U+007F)
    with pytest.raises(GumError):
        Tokenizer('"hello\x7fworld"')


def test_reject_bare_nul_char():
    with pytest.raises(GumError):
        Tokenizer('"hello\x00world"')


def test_tab_allowed_in_string():
    # Tab (U+0009) is explicitly allowed
    t = Tokenizer('"hello\tworld"')
    tok = t.advance()
    assert tok.type == TokenType.STRING
    assert tok.value == "hello\tworld"


def test_multiline_string_crlf_normalized():
    t = Tokenizer('s = """\r\nhello\r\nworld\r\n"""')
    t.advance()  # s
    t.advance()  # whitespace
    t.advance()  # =
    t.advance()  # whitespace
    tok = t.advance()  # string
    assert tok.value == "hello\nworld"
    assert "\r" not in tok.value


def test_multiline_string_crlf_with_dedent():
    src = 's = """\r\n  hello\r\n  world\r\n  """'
    t = Tokenizer(src)
    t.advance()  # s
    t.advance()  # whitespace
    t.advance()  # =
    t.advance()  # whitespace
    tok = t.advance()  # string
    assert tok.value == "hello\nworld"
    assert "\r" not in tok.value


def test_multiline_string_cr_escape_preserved():
    src = r's = """hello\rworld"""'
    t = Tokenizer(src)
    t.advance()  # s
    t.advance()  # whitespace
    t.advance()  # =
    t.advance()  # whitespace
    tok = t.advance()  # string
    assert tok.value == "hello\rworld"
    assert "\r" in tok.value


def test_ident_cannot_start_with_digit():
    with pytest.raises(GumError):
        Tokenizer("1key")


def test_multiline_string_bare_cr_normalized():
    src = 's = """hello\rworld"""'
    t = Tokenizer(src)
    t.advance()  # s
    t.advance()  # whitespace
    t.advance()  # =
    t.advance()  # whitespace
    tok = t.advance()  # string
    assert tok.value == "hello\nworld"
    assert "\r" not in tok.value


def test_number_followed_by_underscore():
    with pytest.raises(GumError):
        Tokenizer("1_abc")


def test_negative_number_followed_by_ident():
    with pytest.raises(GumError):
        Tokenizer("-1key")


def test_number_followed_by_keyword():
    with pytest.raises(GumError):
        Tokenizer("123true")


def test_tab_column_tracking():
    t = Tokenizer("a\t= 1")
    tok = t.advance()  # 'a' IDENT
    assert tok.col == 1
    t.advance()  # tab WHITESPACE
    tok = t.advance()  # '=' EQUALS
    assert tok.col == 5


def test_tab_in_comment_column_tracking():
    t = Tokenizer("# comment\t\nkey")
    t.advance()  # newline after comment
    tok = t.advance()  # 'key' IDENT
    assert tok.col == 1  # key starts at col 1 on new line


def test_whitespace_token():
    t = Tokenizer("  \t  key")
    tok = t.peek()
    assert tok.type == TokenType.WHITESPACE
    assert tok.value == "  \t  "


def test_bom_stripped():
    t = Tokenizer("\ufeffkey = 1")
    tok = t.peek()
    assert tok.type == TokenType.IDENT
    assert tok.value == "key"


def test_hex_number():
    t = Tokenizer("0xFF")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "0xFF"


def test_binary_number():
    t = Tokenizer("0b1010")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "0b1010"


def test_octal_number():
    t = Tokenizer("0o755")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "0o755"


def test_hex_uppercase():
    t = Tokenizer("0XFF")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "0XFF"


def test_binary_uppercase():
    t = Tokenizer("0B0101")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "0B0101"


def test_octal_uppercase():
    t = Tokenizer("0O644")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "0O644"


def test_scientific_notation():
    t = Tokenizer("1e10")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "1e10"


def test_scientific_negative():
    t = Tokenizer("2.5E-3")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "2.5E-3"


def test_scientific_explicit_positive():
    t = Tokenizer("+1.5e+2")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "+1.5e+2"


def test_explicit_positive_int():
    t = Tokenizer("+42")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "+42"


def test_underscore_starting_bare_key():
    """ABNF bare-key allows UNDERSCORE as first char, followed by anything."""
    t = Tokenizer("_1")
    tok = t.peek()
    assert tok.type == TokenType.IDENT
    assert tok.value == "_1"


def test_underscore_starting_bare_key_multiple_digits():
    t = Tokenizer("_42")
    tok = t.peek()
    assert tok.type == TokenType.IDENT
    assert tok.value == "_42"


def test_underscore_only_bare_key():
    t = Tokenizer("_")
    tok = t.peek()
    assert tok.type == TokenType.IDENT
    assert tok.value == "_"


def test_underscore_separator():
    t = Tokenizer("1_000_000")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "1_000_000"


def test_underscore_starting_ident():
    """ABNF bare-key allows UNDERSCORE followed by DIGIT."""
    t = Tokenizer("_1000")
    tok = t.peek()
    assert tok.type == TokenType.IDENT
    assert tok.value == "_1000"


def test_underscore_invalid_trailing():
    with pytest.raises(GumError):
        Tokenizer("1000_")


def test_underscore_invalid_consecutive():
    with pytest.raises(GumError):
        Tokenizer("1__000")


def test_double_sign_rejected():
    with pytest.raises(GumError):
        Tokenizer("+-42")


def test_empty_hex_rejected():
    with pytest.raises(GumError):
        Tokenizer("0x")


def test_empty_binary_rejected():
    with pytest.raises(GumError):
        Tokenizer("0b")


def test_empty_octal_rejected():
    with pytest.raises(GumError):
        Tokenizer("0o")


def test_negative_hex():
    t = Tokenizer("-0xFF")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "-0xFF"


def test_underscore_in_hex():
    t = Tokenizer("0xFF_FF")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "0xFF_FF"


def test_reject_forward_slash_escape():
    with pytest.raises(GumError):
        Tokenizer(r'"hello\/world"')


def test_multiline_dedent_spec():
    """Spec algorithm: min indentation of non-empty lines, spaces only."""
    src = 's = """\n      "Did you ever hear the Tragedy of Darth Plagueis the Wise?"\n      "No."\n      "I thought not."\n"""'
    t = Tokenizer(src)
    t.advance()  # s
    t.advance()  # whitespace
    t.advance()  # =
    t.advance()  # whitespace
    tok = t.advance()  # string
    assert tok.value == '"Did you ever hear the Tragedy of Darth Plagueis the Wise?"\n"No."\n"I thought not."'


def test_multiline_dedent_no_leading_newline():
    src = 's = """hello\n  world\n"""'
    t = Tokenizer(src)
    t.advance()  # s
    t.advance()  # whitespace
    t.advance()  # =
    t.advance()  # whitespace
    tok = t.advance()  # string
    assert tok.value == "hello\n  world"


def test_multiline_dedent_tabs_not_indentation():
    """Tabs are treated as content, not indentation."""
    src = 's = """\n\thello\n\tworld\n"""'
    t = Tokenizer(src)
    t.advance()  # s
    t.advance()  # whitespace
    t.advance()  # =
    t.advance()  # whitespace
    tok = t.advance()  # string
    assert tok.value == "\thello\n\tworld"


def test_positive_with_underscores():
    t = Tokenizer("+1_000")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "+1_000"


def test_reject_nul_in_multiline_string():
    """ABNF unescaped-ml excludes NUL (U+0000)."""
    with pytest.raises(GumError):
        Tokenizer('"""hello\x00world"""')


def test_reject_backspace_in_multiline_string():
    """ABNF unescaped-ml excludes BS (U+0008)."""
    with pytest.raises(GumError):
        Tokenizer('"""hello\x08world"""')


def test_reject_vt_in_multiline_string():
    """ABNF unescaped-ml excludes VT (U+000B)."""
    with pytest.raises(GumError):
        Tokenizer('"""hello\x0bworld"""')


def test_reject_ff_in_multiline_string():
    """ABNF unescaped-ml excludes FF (U+000C)."""
    with pytest.raises(GumError):
        Tokenizer('"""hello\x0cworld"""')


def test_reject_soh_in_multiline_string():
    """ABNF unescaped-ml excludes SOH (U+0001)."""
    with pytest.raises(GumError):
        Tokenizer('"""hello\x01world"""')


def test_tab_allowed_in_multiline_string():
    """ABNF unescaped-ml explicitly allows HTAB."""
    t = Tokenizer('"""hello\tworld"""')
    tok = t.peek()
    assert tok.type == TokenType.STRING
    assert tok.value == "hello\tworld"
