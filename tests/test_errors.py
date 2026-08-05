from gum._errors import GumDecodeError
from gum.tokenizer import GumError


def test_gum_decode_error_attributes():
    err = GumDecodeError("unexpected token", 5, 12)
    assert err.msg == "unexpected token"
    assert err.lineno == 5
    assert err.colno == 12


def test_gum_decode_error_str():
    err = GumDecodeError("bad thing", 3, 7)
    assert "bad thing" in str(err)
    assert "3" in str(err)
    assert "7" in str(err)


def test_gum_decode_error_is_exception():
    assert issubclass(GumDecodeError, Exception)


def test_gum_error_is_gum_decode_error():
    assert GumError is GumDecodeError


def test_gum_decode_error_compatible_attributes():
    err = GumDecodeError("test", 10, 20)
    assert err.message == "test"
    assert err.line == 10
    assert err.col == 20
