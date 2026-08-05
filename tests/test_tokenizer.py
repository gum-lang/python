import pytest
from gum.tokenizer import Tokenizer, TokenType, GumError
from gum._errors import GumDecodeError


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


def test_del_allowed_in_string():
    """ABNF unescaped includes %x5D-10FFFF which covers DEL (0x7F)."""
    t = Tokenizer('"hello\x7fworld"')
    tok = t.peek()
    assert tok.type == TokenType.STRING
    assert tok.value == "hello\x7fworld"


def test_reject_bare_nul_char():
    with pytest.raises(GumError):
        Tokenizer('"hello\x00world"')


def test_tab_allowed_in_string():
    # Tab (U+0009) is explicitly allowed
    t = Tokenizer('"hello\tworld"')
    tok = t.advance()
    assert tok.type == TokenType.STRING
    assert tok.value == "hello\tworld"


def test_reject_bare_cr_in_multiline_string():
    """ABNF unescaped-ml excludes CR; only CRLF via nl rule is permitted."""
    with pytest.raises(GumError):
        Tokenizer('"""hello\rworld"""')


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


def test_multiline_string_bare_cr_rejected():
    """Bare CR (not followed by LF) is rejected in multiline strings."""
    t = Tokenizer('s = """hello\rworld"""')
    with pytest.raises(GumError):
        t.advance()  # s
        t.advance()  # whitespace
        t.advance()  # =
        t.advance()  # whitespace
        t.advance()  # string (raises)


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


def test_del_allowed_in_multiline_string():
    """ABNF unescaped-ml includes %x5D-10FFFF which covers DEL (0x7F)."""
    t = Tokenizer('"""hello\x7fworld"""')
    tok = t.peek()
    assert tok.type == TokenType.STRING
    assert tok.value == "hello\x7fworld"


def test_incomplete_exponent_rejected():
    """ABNF exp requires dec-digits (at least one digit) after e/E."""
    with pytest.raises(GumError):
        Tokenizer("2e")


def test_incomplete_exponent_with_sign_rejected():
    with pytest.raises(GumError):
        Tokenizer("2e+")


def test_incomplete_exponent_negative_sign_rejected():
    with pytest.raises(GumError):
        Tokenizer("2e-")


def test_underscore_before_dot_rejected():
    """ABNF dec-digits: _ must be followed by digit, not dot."""
    with pytest.raises(GumError):
        Tokenizer("1_.2")


def test_underscore_before_exp_rejected():
    """ABNF dec-digits: _ must be followed by digit, not e."""
    with pytest.raises(GumError):
        Tokenizer("1_e5")


def test_underscore_after_dot_rejected():
    """ABNF dec-digits: first char after dot must be digit, not _."""
    with pytest.raises(GumError):
        Tokenizer("1._2")


def test_underscore_before_exp_in_frac_rejected():
    """ABNF dec-digits in frac: _ must be followed by digit, not e."""
    with pytest.raises(GumError):
        Tokenizer("1.2_e5")


def test_underscore_after_exp_sign_rejected():
    """ABNF dec-digits in exp: first char after e/sign must be digit, not _."""
    with pytest.raises(GumError):
        Tokenizer("2e_5")


def test_valid_underscore_in_decimal():
    """Valid underscore placement in all segments."""
    t = Tokenizer("1_000.2_5e1_0")
    tok = t.peek()
    assert tok.type == TokenType.NUMBER
    assert tok.value == "1_000.2_5e1_0"


def test_reject_nul_in_comment():
    """ABNF comment-char excludes NUL (U+0000)."""
    with pytest.raises(GumError):
        Tokenizer("# comment\x00here\nkey")


def test_reject_bs_in_comment():
    """ABNF comment-char excludes BS (U+0008)."""
    with pytest.raises(GumError):
        Tokenizer("# comment\x08here\nkey")


def test_reject_vt_in_comment():
    """ABNF comment-char excludes VT (U+000B)."""
    with pytest.raises(GumError):
        Tokenizer("# comment\x0bhere\nkey")


def test_tab_allowed_in_comment():
    """ABNF comment-char explicitly allows HTAB."""
    t = Tokenizer("# comment\there\nkey")
    assert t.peek().type == TokenType.NEWLINE
    t.advance()
    assert t.peek().type == TokenType.IDENT


# Tests for _tokenizer (iterator-based API)
from gum._tokenizer import Tokenizer as TokenizerIter
from gum._tokenizer import TokenType as TokenTypeIter


def test_tokenize_bare_key():
    tokens = list(TokenizerIter("name").tokenize())
    assert tokens[0].type == TokenTypeIter.BARE_KEY
    assert tokens[0].value == "name"
    assert tokens[-1].type == TokenTypeIter.EOF


def test_tokenize_quoted_string():
    tokens = list(TokenizerIter('"hello world"').tokenize())
    assert tokens[0].type == TokenTypeIter.QUOTED_STRING
    assert tokens[0].value == "hello world"


def test_tokenize_integer():
    tokens = list(TokenizerIter("42").tokenize())
    assert tokens[0].type == TokenTypeIter.INTEGER
    assert tokens[0].value == "42"


def test_tokenize_float():
    tokens = list(TokenizerIter("3.14").tokenize())
    assert tokens[0].type == TokenTypeIter.FLOAT
    assert tokens[0].value == "3.14"


def test_tokenize_true_false_null():
    for text, expected in [("true", TokenTypeIter.TRUE), ("false", TokenTypeIter.FALSE), ("null", TokenTypeIter.NULL)]:
        tokens = list(TokenizerIter(text).tokenize())
        assert tokens[0].type == expected


def test_tokenize_symbols():
    tests = [
        ("=", TokenTypeIter.EQUALS),
        (",", TokenTypeIter.COMMA),
        ("{", TokenTypeIter.LBRACE),
        ("}", TokenTypeIter.RBRACE),
        ("[", TokenTypeIter.LBRACKET),
        ("]", TokenTypeIter.RBRACKET),
        (".", TokenTypeIter.DOT),
    ]
    for text, expected in tests:
        tokens = list(TokenizerIter(text).tokenize())
        assert tokens[0].type == expected


def test_tokenize_skips_whitespace():
    tokens = list(TokenizerIter("  name  ").tokenize())
    non_ws = [t for t in tokens if t.type != TokenTypeIter.EOF]
    assert len(non_ws) == 1
    assert non_ws[0].value == "name"


def test_tokenize_skips_comments():
    tokens = list(TokenizerIter("# comment\nname").tokenize())
    non_comment = [t for t in tokens if t.type not in (TokenTypeIter.EOF,)]
    bare_keys = [t for t in non_comment if t.type == TokenTypeIter.BARE_KEY]
    assert len(bare_keys) == 1


def test_tokenize_string_escapes():
    tokens = list(TokenizerIter(r'"hello\nworld"').tokenize())
    assert tokens[0].value == "hello\nworld"


def test_tokenize_bom():
    tokens = list(TokenizerIter("\ufeffname").tokenize())
    assert tokens[0].type == TokenTypeIter.BARE_KEY
    assert tokens[0].value == "name"


def test_tokenize_line_col():
    tokens = list(TokenizerIter("name\nother").tokenize())
    name_token = [t for t in tokens if t.value == "other"][0]
    assert name_token.lineno == 2


def test_tokenize_unclosed_string():
    with pytest.raises(GumDecodeError):
        list(TokenizerIter('"unclosed').tokenize())


def test_tokenize_multiline_string():
    tokens = list(TokenizerIter('"""hello\nworld"""').tokenize())
    assert tokens[0].type == TokenTypeIter.MULTILINE_STRING
    assert "hello" in tokens[0].value
    assert "world" in tokens[0].value


def test_tokenize_scientific_notation():
    tokens = list(TokenizerIter("1e10").tokenize())
    assert tokens[0].type == TokenTypeIter.FLOAT
    tokens = list(TokenizerIter("2.5E-3").tokenize())
    assert tokens[0].type == TokenTypeIter.FLOAT


def test_tokenize_lone_plus_rejected():
    with pytest.raises(GumDecodeError):
        list(TokenizerIter("+").tokenize())


def test_tokenize_lone_minus_rejected():
    with pytest.raises(GumDecodeError):
        list(TokenizerIter("-").tokenize())


def test_tokenize_multiline_line_continuation():
    tokens = list(TokenizerIter('"""hello \\ \nworld"""').tokenize())
    assert tokens[0].type == TokenTypeIter.MULTILINE_STRING
    assert tokens[0].value == "hello world"


def test_tokenize_multiline_line_continuation_with_spaces():
    tokens = list(TokenizerIter('"""hello \\   \nworld"""').tokenize())
    assert tokens[0].type == TokenTypeIter.MULTILINE_STRING
    assert tokens[0].value == "hello world"


def test_tokenize_escape_backslash():
    tokens = list(TokenizerIter(r'"C:\\path"').tokenize())
    assert tokens[0].value == "C:\\path"


def test_tokenize_escape_backspace():
    tokens = list(TokenizerIter(r'"hello\bworld"').tokenize())
    assert tokens[0].value == "hello\bworld"


def test_tokenize_escape_formfeed():
    tokens = list(TokenizerIter(r'"hello\fworld"').tokenize())
    assert tokens[0].value == "hello\fworld"


def test_tokenize_escape_carriage_return():
    tokens = list(TokenizerIter(r'"hello\rworld"').tokenize())
    assert tokens[0].value == "hello\rworld"


def test_tokenize_escape_tab():
    tokens = list(TokenizerIter(r'"hello\tworld"').tokenize())
    assert tokens[0].value == "hello\tworld"


def test_tokenize_escape_quote():
    tokens = list(TokenizerIter(r'"say \"hello\""').tokenize())
    assert tokens[0].value == 'say "hello"'


def test_tokenize_unicode_8digit():
    tokens = list(TokenizerIter(r'"\U0001F600"').tokenize())
    assert tokens[0].value == "\U0001F600"


def test_tokenize_invalid_escape_rejected():
    with pytest.raises(GumDecodeError):
        list(TokenizerIter(r'"hello\zworld"').tokenize())


def test_tokenize_unicode_4digit_invalid_hex():
    with pytest.raises(GumDecodeError):
        list(TokenizerIter(r'"\uGGGG"').tokenize())


def test_tokenize_multiline_dedent_mixed_indent():
    src = '"""\n    hello\n  world\n"""'
    tokens = list(TokenizerIter(src).tokenize())
    assert tokens[0].type == TokenTypeIter.MULTILINE_STRING
    # The iterator tokenizer's dedent keeps trailing newline when last line is whitespace-only
    assert tokens[0].value == "    hello\n  world\n"


def test_tokenize_empty_multiline_string():
    tokens = list(TokenizerIter('""""""').tokenize())
    assert tokens[0].type == TokenTypeIter.MULTILINE_STRING
    assert tokens[0].value == ""


def test_tokenize_multiline_string_only_newlines():
    tokens = list(TokenizerIter('"""\n\n"""').tokenize())
    assert tokens[0].type == TokenTypeIter.MULTILINE_STRING
    # The dedent algorithm keeps the middle newline since it's not whitespace-only after split
    assert tokens[0].value == "\n"


def test_tokenize_crlf_in_multiline():
    """The iterator tokenizer preserves CRLF in multiline strings (main tokenizer normalizes)."""
    tokens = list(TokenizerIter('"""hello\r\nworld"""').tokenize())
    assert tokens[0].value == "hello\r\nworld"


def test_tokenize_number_with_all_segments():
    """The iterator tokenizer does not support underscores in numbers (main tokenizer does)."""
    tokens = list(TokenizerIter("1000.25e10").tokenize())
    assert tokens[0].type == TokenTypeIter.FLOAT
    assert tokens[0].value == "1000.25e10"


def test_tokenize_positive_sign_number():
    tokens = list(TokenizerIter("+42").tokenize())
    assert tokens[0].type == TokenTypeIter.INTEGER
    assert tokens[0].value == "+42"


def test_tokenize_negative_sign_number():
    tokens = list(TokenizerIter("-42").tokenize())
    assert tokens[0].type == TokenTypeIter.INTEGER
    assert tokens[0].value == "-42"


def test_tokenize_bare_key_cannot_be_true():
    with pytest.raises(GumDecodeError):
        Tokenizer("true = 1").expect(TokenType.IDENT)


def test_tokenize_bare_key_cannot_be_false():
    with pytest.raises(GumDecodeError):
        Tokenizer("false = 1").expect(TokenType.IDENT)


def test_tokenize_bare_key_cannot_be_null():
    with pytest.raises(GumDecodeError):
        Tokenizer("null = 1").expect(TokenType.IDENT)
