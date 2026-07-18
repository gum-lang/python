from gum import unmarshal, marshal, GumError


def test_unmarshal_simple():
    assert unmarshal('key = "value"') == {"key": "value"}

def test_marshal_simple():
    result = marshal({"key": "value"})
    assert 'key = "value"' in result

def test_roundtrip():
    data = {"name": "test", "version": 1, "active": True, "meta": None}
    gum_str = marshal(data)
    parsed = unmarshal(gum_str)
    assert parsed == data

def test_invalid_syntax():
    import pytest
    with pytest.raises(GumError):
        unmarshal("key = ")

def test_unmarshal_file(tmp_path):
    p = tmp_path / "config.gum"
    p.write_text('key = "value"\n')
    result = unmarshal(p)
    assert result == {"key": "value"}
