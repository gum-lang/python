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
    import pytest
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
    import pytest
    with pytest.raises(GumError):
        Tokenizer(r'"\uGGGG"')
