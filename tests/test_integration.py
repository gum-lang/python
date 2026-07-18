from gum import unmarshal, marshal


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
    parsed = unmarshal(src)
    # TODO: We need to assert values are correctly read
    # TODO: Waiting on import corrections
    gum_str = marshal(parsed)
    reparsed = unmarshal(gum_str)
    assert parsed == reparsed
