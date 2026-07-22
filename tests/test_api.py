import io

from gum import dump, dumps, load, loads, GumError


def test_loads_simple():
    assert loads('key = "value"') == {"key": "value"}


def test_dumps_simple():
    result = dumps({"key": "value"})
    assert 'key = "value"' in result


def test_roundtrip():
    data = {"name": "test", "version": 1, "active": True, "meta": None}
    gum_str = dumps(data)
    parsed = loads(gum_str)
    assert parsed == data


def test_invalid_syntax():
    import pytest
    with pytest.raises(GumError):
        loads("key = ")


def test_loads_file(tmp_path):
    p = tmp_path / "config.gum"
    p.write_text('key = "value"\n')
    result = load(p)
    assert result == {"key": "value"}


def test_load_file_object(tmp_path):
    p = tmp_path / "config.gum"
    p.write_text('key = "value"\n')
    with open(p) as f:
        result = load(f)
    assert result == {"key": "value"}


def test_dump_file_object(tmp_path):
    p = tmp_path / "config.gum"
    data = {"name": "test", "version": 42}
    with open(p, "w") as f:
        dump(data, f)
    result = load(p)
    assert result == data

