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
    t.advance()  # =
    tok = t.advance()  # string
    assert tok.value == "hello\nworld"
    assert "\r" not in tok.value


def test_multiline_string_crlf_with_dedent():
    src = 's = """\r\n  hello\r\n  world\r\n  """'
    t = Tokenizer(src)
    t.advance()  # s
    t.advance()  # =
    tok = t.advance()  # string
    assert tok.value == "hello\nworld"
    assert "\r" not in tok.value


def test_multiline_string_cr_escape_preserved():
    src = r's = """hello\rworld"""'
    t = Tokenizer(src)
    t.advance()  # s
    t.advance()  # =
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
    t.advance()  # =
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
