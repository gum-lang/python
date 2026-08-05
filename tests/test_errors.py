from gum._errors import GumDecodeError


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
