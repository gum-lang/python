# Implementation Notes

## Architecture

The library follows a classic two-stage parsing pipeline:

```
source text -> Tokenizer -> token stream -> Parser -> nested dict/list
```

A separate `serializer` module handles the reverse direction (dict -> gum string).

### Modules

| Module | Purpose |
|--------|---------|
| `gum/tokenizer.py` | Lexical analysis: source text to token stream |
| `gum/parser.py` | Recursive descent parser: token stream to nested dict |
| `gum/serializer.py` | Serialization: nested dict to gum-formatted string |
| `gum/_errors.py` | `GumDecodeError` exception with line/column tracking |
| `gum/__init__.py` | Public API (`loads`, `load`, `dumps`, `dump`, `GumDecoder`, `GumEncoder`) |

## Design Decisions

### Recursive Descent Parser

The parser is a single-pass recursive descent parser that stops on the first error (no error recovery). This was chosen because:

- The gum grammar is simple enough that LL(1) parsing suffices
- Error messages are precise (first error, exact position)
- No need for parser generators or complex grammar transformations
- Easy to maintain and extend

### Tokenizer as Iterator

The tokenizer implements a peek/advance/expect interface rather than producing a full token list upfront. This keeps memory usage constant regardless of input size and allows the parser to drive tokenization lazily.

Comments are consumed silently during tokenization and never emitted as tokens.

### Semantic Validation During Parsing

Semantic checks (duplicate keys, inline table immutability, path conflicts) are performed inline during parsing rather than in a separate validation pass. The parser tracks inline table paths in a set (`_inline_tables`) to enforce immutability rules.

### Serializer Heuristics

The serializer uses simple heuristics to choose between inline and multi-line formats:

- **Lists**: Inline if all scalars, <= 4 elements, and < 40 chars total
- **Dicts**: Inline if all scalar values and <= 3 entries

These produce readable output for typical configuration files without requiring user configuration.

### API Design

The public API mirrors Python's `json` module (`loads`, `load`, `dumps`, `dump`) for familiarity. `GumDecoder` and `GumEncoder` classes support hooks for custom object processing (e.g., `OrderedDict`).

## Spec Compliance

### Implemented

- UTF-8 encoding with BOM stripping
- CRLF normalized to LF; bare CR rejected
- Quoted strings with all spec escape sequences (`\b`, `\t`, `\n`, `\f`, `\r`, `\"`, `\\`, `\uXXXX`)
- Multi-line strings with spec-compliant dedent algorithm
- Control character validation in strings and comments
- Decimal integers with underscore separators
- Hex (`0x`), binary (`0b`), octal (`0o`) literals
- Floats with scientific notation, leading/trailing decimal points
- Underscore placement validation (no leading, trailing, or consecutive)
- Bare keys, quoted keys, dotted paths
- Reserved keyword rejection (`true`, `false`, `null` as keys)
- Inline and multi-line tables and lists
- Trailing commas
- Duplicate key detection
- Key path conflict detection
- Inline table immutability

### Not Implemented

- **Literal strings** (single-quoted `'...'` and `'''...'''`) from spec v0.3.0
- **Numeric overflow detection** (Python integers have arbitrary precision)

## Testing Strategy

### Unit Tests

274 unit tests across 7 test files covering:

| File | Coverage |
|------|----------|
| `test_tokenizer.py` | Token recognition, escape sequences, number formats, error cases |
| `test_parser.py` | Assignments, dotted paths, tables, lists, semantic validation |
| `test_serializer.py` | String escaping, inline/multi-line heuristics, round-trip |
| `test_errors.py` | Error message formatting, position tracking |
| `test_api.py` | Public API (`loads`, `dumps`, hooks, file I/O) |
| `test_integration.py` | End-to-end scenarios, edge cases |
| `test_conformance.py` | Official gum test suite fixtures |

### Conformance Tests

28 fixtures from the [gum-test-suite](https://github.com/gum-lang/gum-test-suite) submodule:
- 18 valid fixtures (parse and compare to expected JSON)
- 10 invalid fixtures (verify rejection with `GumDecodeError`)

Result: 27 passed, 1 xfailed (`overflow.gum` — see Known Limitations).

### Tagged JSON Comparison

Conformance tests convert parsed Python values to a tagged JSON format (`{"type": "...", "value": "..."}`) before comparing against expected output. This ensures type-correct comparison (e.g., distinguishing integer `42` from float `42.0`).

## Known Limitations

### Numeric Overflow

Python integers have arbitrary precision, so `1e999999` does not overflow naturally. The conformance test `invalid/number/overflow.gum` is marked `xfail`. Detecting overflow would require explicit bounds checking against IEEE 754 limits, which is not implemented.

### Literal Strings

Single-quoted literal strings (`'...'` and `'''...'''`) from spec v0.3.0 are not implemented. The current implementation only supports double-quoted strings.

## Requirements

- Python >= 3.10
- pytest (dev dependency)
- No external runtime dependencies
