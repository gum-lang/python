import json
import glob
import os

import pytest
import gum

CONFORMANCE_DIR = os.path.join(os.path.dirname(__file__), "conformance")


def _to_tagged_value(obj):
    """Convert a single gum value to its tagged JSON representation."""
    if obj is None:
        return {"type": "null", "value": None}
    if isinstance(obj, bool):
        return {"type": "bool", "value": str(obj).lower()}
    if isinstance(obj, int):
        return {"type": "integer", "value": str(obj)}
    if isinstance(obj, float):
        return {"type": "float", "value": str(obj)}
    if isinstance(obj, str):
        return {"type": "string", "value": obj}
    if isinstance(obj, list):
        return [_to_tagged_value(item) for item in obj]
    if isinstance(obj, dict):
        return {"type": "table", "value": {k: _to_tagged_value(v) for k, v in obj.items()}}
    raise TypeError(f"unknown type: {type(obj)}")


def to_tagged(obj):
    """Convert a Python object to the tagged JSON format used by gum-test-suite."""
    if isinstance(obj, dict):
        return {k: _to_tagged_value(v) for k, v in obj.items()}
    return _to_tagged_value(obj)


def _valid_fixtures():
    """Yield (gum_path, json_path) pairs for all valid test fixtures."""
    pattern = os.path.join(CONFORMANCE_DIR, "valid", "**", "*.gum")
    for gum_path in glob.glob(pattern, recursive=True):
        json_path = gum_path.replace(".gum", ".json")
        if os.path.exists(json_path):
            yield gum_path, json_path


def _invalid_fixtures():
    """Yield gum paths for all invalid test fixtures."""
    pattern = os.path.join(CONFORMANCE_DIR, "invalid", "**", "*.gum")
    yield from glob.glob(pattern, recursive=True)


@pytest.mark.parametrize("gum_path,json_path", list(_valid_fixtures()))
def test_valid_fixture(gum_path, json_path):
    """Parse a valid .gum file and compare against expected tagged JSON."""
    with open(gum_path) as f:
        source = f.read()
    with open(json_path) as f:
        expected = json.load(f)

    result = gum.loads(source)
    assert to_tagged(result) == expected, f"Mismatch in {os.path.relpath(gum_path)}"


@pytest.mark.parametrize("gum_path", list(_invalid_fixtures()))
def test_invalid_fixture(gum_path):
    """Parse an invalid .gum file and assert that GumDecodeError is raised."""
    with open(gum_path) as f:
        source = f.read()

    with pytest.raises(gum.GumDecodeError):
        gum.loads(source)
