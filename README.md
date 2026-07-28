![acronym](https://github.com/gum-lang/.github/raw/main/assets/acronym.png)

This is a parser for the [GUM](https://github.com/gum-lang/spec) markup language for Python.

## API

This is a library for parsing `gum` markup. It mirrors the [json](https://docs.python.org/3/library/json.html) library in its API.

```python
def loads(s: str) -> dict[str, Any]
def load(fp: IO[str] | Path) -> dict[str, Any]
def dumps(data: dict[str, Any], indent: int = 2) -> str
def dump(data: dict[str, Any], fp: TextIO, indent: int = 2) -> None
```

## Example

```python
import gum

config = gum.loads("""
name = "my-app"
version = 1

server.host = "localhost"
server.port = 8080

features = {
  debug = true
  logging = false
}
""")

print(config["name"])  # "my-app"
print(config["server"]["port"])  # 8080
```

## Types

| \_ in `gum` | maps to \_ in `python3` |
| ----------- | ----------------------- |
| null        | None                    |
| true        | True                    |
| false       | False                   |
| integer     | int                     |
| float       | float                   |
| string      | str                     |
| list        | list                    |
| record      | dict                    |

![elaine](https://github.com/gum-lang/.github/raw/main/assets/elaine.png)

## Conformance

This library is tested against the [gum-test-suite](https://github.com/gum-lang/gum-test-suite) conformance test suite. Tests are included as a git submodule under `tests/conformance/`.

Run conformance tests:

```bash
pytest tests/test_conformance.py -v
```

Run all tests (unit + conformance):

```bash
pytest tests/ -v
```

Update the test suite:

```bash
git submodule update --remote tests/conformance
```

