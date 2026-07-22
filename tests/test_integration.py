from gum import dumps, loads


def test_spec_full_example():
    src = """# camel config example
name = "camel-parser"
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

description = \"\"\"This is camel.
It is markup everyone likes.\"\"\""""
    parsed = loads(src)
    gum_str = dumps(parsed)
    reparsed = loads(gum_str)
    assert parsed == reparsed
