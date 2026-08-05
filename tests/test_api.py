import io

import pytest

from gum import (
    GumDecodeError,
    GumDecoder,
    GumEncoder,
    GumError,
    dump,
    dumps,
    load,
    loads,
)


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


def test_load_file_error_includes_filename(tmp_path):
    p = tmp_path / "bad.gum"
    p.write_text("key = ")
    with pytest.raises(GumError) as exc_info:
        load(p)
    assert "bad.gum" in str(exc_info.value)


def test_load_file_object_error_includes_filename(tmp_path):
    p = tmp_path / "bad2.gum"
    p.write_text("key = ")
    with open(p) as f:
        with pytest.raises(GumError) as exc_info:
            load(f)
    assert "bad2.gum" in str(exc_info.value)


def test_load_invalid_input_type():
    with pytest.raises(TypeError):
        load(42)  # type: ignore


def test_load_file_with_bom(tmp_path):
    p = tmp_path / "config.gum"
    p.write_text("\ufeffkey = \"value\"\n", encoding="utf-8")
    result = load(p)
    assert result == {"key": "value"}


def test_gum_decode_error_importable():
    from gum import GumDecodeError as ImportedError

    err = ImportedError("test", 1, 2)
    assert err.msg == "test"
    assert err.lineno == 1
    assert err.colno == 2


def test_gum_decode_error_raised_on_parse_error():
    with pytest.raises(GumError):
        loads('"unclosed')


def test_gum_decoder_decode():
    decoder = GumDecoder()
    result = decoder.decode('name = "Alice"')
    assert result == {"name": "Alice"}


def test_gum_decoder_object_hook():
    def hook(d):
        return {k: v.upper() if isinstance(v, str) else v for k, v in d.items()}

    decoder = GumDecoder(object_hook=hook)
    result = decoder.decode('name = "alice"')
    assert result == {"name": "ALICE"}


def test_gum_decoder_object_hook_nested():
    def hook(d):
        return {k: f"[{v}]" if isinstance(v, str) else v for k, v in d.items()}

    decoder = GumDecoder(object_hook=hook)
    result = decoder.decode('outer = { inner = "hello" }')
    assert result == {"outer": {"inner": "[hello]"}}


def test_gum_decoder_object_pairs_hook():
    from collections import OrderedDict

    decoder = GumDecoder(object_pairs_hook=OrderedDict)
    result = decoder.decode('a = "1"\nb = "2"')
    assert isinstance(result, OrderedDict)
    assert list(result.keys()) == ["a", "b"]


def test_gum_decoder_object_pairs_hook_nested():
    from collections import OrderedDict

    decoder = GumDecoder(object_pairs_hook=OrderedDict)
    result = decoder.decode('outer = { inner = "val" }')
    assert isinstance(result, OrderedDict)
    assert isinstance(result["outer"], OrderedDict)


def test_gum_decoder_pairs_hook_takes_precedence():
    called_pairs = []
    called_obj = []

    def pairs_hook(pairs):
        called_pairs.append(pairs)
        return dict(pairs)

    def obj_hook(d):
        called_obj.append(d)
        return d

    decoder = GumDecoder(object_pairs_hook=pairs_hook, object_hook=obj_hook)
    decoder.decode('a = "1"')
    assert len(called_pairs) == 1
    assert len(called_obj) == 0


def test_gum_encoder_default():
    encoder = GumEncoder()
    result = encoder.encode({"key": "value"})
    assert 'key = "value"' in result


def test_gum_encoder_indent():
    encoder = GumEncoder(indent=4)
    result = encoder.encode({"tbl": {"a": 1, "b": 2, "c": 3, "d": 4}})
    assert "    a = 1" in result


def test_gum_encoder_bare_keys_true():
    encoder = GumEncoder(bare_keys=True)
    result = encoder.encode({"name": "test"})
    assert "name = " in result
    assert '"name"' not in result


def test_gum_encoder_bare_keys_false():
    encoder = GumEncoder(bare_keys=False)
    result = encoder.encode({"name": "test"})
    assert '"name" = "test"' in result


def test_gum_encoder_bare_keys_forces_quoting_reserved():
    encoder = GumEncoder(bare_keys=True)
    result = encoder.encode({"true": "yes"})
    assert '"true" = "yes"' in result


def test_gum_encoder_bare_keys_forces_quoting_special():
    encoder = GumEncoder(bare_keys=True)
    result = encoder.encode({"my-key": "val"})
    assert '"my-key" = "val"' in result


def test_gum_encoder_empty():
    encoder = GumEncoder()
    assert encoder.encode({}) == ""


def test_dumps_with_bare_keys_false():
    result = dumps({"name": "test"}, bare_keys=False)
    assert '"name" = "test"' in result


def test_dump_with_indent():
    fp = io.StringIO()
    dump({"tbl": {"a": 1, "b": 2, "c": 3, "d": 4}}, fp, indent=4)
    assert "    a = 1" in fp.getvalue()


def test_loads_with_object_hook():
    def hook(d):
        return {k.upper(): v for k, v in d.items()}

    result = loads('name = "alice"', object_hook=hook)
    assert result == {"NAME": "alice"}


def test_loads_with_object_pairs_hook():
    from collections import OrderedDict

    result = loads('a = 1\nb = 2', object_pairs_hook=OrderedDict)
    assert isinstance(result, OrderedDict)
    assert list(result.keys()) == ["a", "b"]


def test_load_with_object_hook(tmp_path):
    def hook(d):
        return {k: v * 2 if isinstance(v, int) else v for k, v in d.items()}

    p = tmp_path / "config.gum"
    p.write_text("count = 5\n")
    result = load(p, object_hook=hook)
    assert result == {"count": 10}
