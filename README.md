![acronym](https://github.com/gum-lang/spec/raw/main/assets/acronym.png)

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

TODO

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

![elaine](https://github.com/gum-lang/spec/raw/main/assets/elaine.png)
