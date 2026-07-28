from gum import dumps, loads


def test_spec_full_example():
    src = """# gum config example
version = 1

author.name = "Alice"
author.email = "alice@example.com"

features = {
  strict = true
  logging = false
  max_retries = 3
  tags = ["dev", "prod"]
}

database = {
  host = "localhost"
  port = 5432
  credentials = {
    user = "admin"
    password = null
  }
}

acronym = \"\"\"
      gum is
      useful
      markup
\"\"\""""
    parsed = loads(src)
    expected = {
        "version": 1,
        "author": {
            "name": "Alice",
            "email": "alice@example.com"
        },
        "features": {
            "strict": True,
            "logging": False,
            "max_retries": 3,
            "tags": ["dev", "prod"]
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "credentials": {
                "user": "admin",
                "password": None
            }
        },
        "acronym": "gum is\nuseful\nmarkup"
    }
    assert parsed == expected
    gum_str = dumps(parsed)
    reparsed = loads(gum_str)
    assert reparsed == expected


def test_hex_binary_octal_roundtrip():
    src = """hex = 0xFF
bin = 0b1010
oct = 0o755"""
    parsed = loads(src)
    assert parsed == {"hex": 255, "bin": 10, "oct": 493}


def test_scientific_notation():
    src = """sci1 = 1e10
sci2 = 2.5E-3
sci3 = +1.5e+2"""
    parsed = loads(src)
    assert parsed == {"sci1": 1e10, "sci2": 2.5e-3, "sci3": 1.5e2}


def test_underscore_numbers():
    src = "big = 1_000_000"
    parsed = loads(src)
    assert parsed == {"big": 1000000}
