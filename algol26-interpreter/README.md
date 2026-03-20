# ALGOL 26 Interpreter

Minimal Viable Interpreter (MVI) for ALGOL 26, built in Python.

## Project Structure

```
.
├── src/
│   ├── lexer.py       # Tokenization
│   ├── parser.py      # Recursive descent parser with Pratt expressions
│   ├── ast.py         # Abstract Syntax Tree nodes
│   ├── interpreter.py # Evaluator with environment
│   └── builtins.py    # Built-in functions (println, math, etc.)
├── tests/
│   ├── hello.algol26
│   └── ai-demo.algol26
├── main.py            # Entry point
├── pyproject.toml     # Project configuration
└── README.md
```

## Features

The MVP interpreter implements:

- Lexical syntax: identifiers, literals (int, real, bool, char, string), comments, operators.
- Core grammar: variables, control flow (if, while, for), functions (proc), arrays, records, expressions.
- Built-in functions: `println`, `print`, and basic math (`exp`, `sqrt`, `sin`, `cos`, `tan`, `log`, `abs`, etc.)
- Advanced feature stub: `prob` (recognized but stubbed)
- Static typing with basic inference (`var x := ...`).

## Running Programs

Run an ALGOL 26 source file:

```bash
python main.py tests/hello.algol26
```

or

```bash
python main.py tests/ai-demo.algol26
```

## Demo Programs

- `hello.algol26`: Classic "Hello, World!" example.
- `ai-demo.algol26`: Calculates a simple neural network forward pass (sigmoid activation).

## Implementation Notes

- **Language**: Python 3.9+ for rapid prototyping.
- **Parser**: Hand-written recursive descent with Pratt parser for expressions.
- **Type System**: Dynamic semantics with static type annotations (enforced minimally in MVP). Types: `int`, `real`, `bool`, `char`, `string`, fixed-size arrays, records.
- **Memory**: Stack-allocated values; no GC yet. Arrays and records are Python lists/dicts.
- **Concurrency**: Keywords recognized but stubbed (`async`, `await`, `chan`, `spawn`).
- **Advanced Features**: `prob`/`causal`/`verify` recognized but not implemented.

## Future Work

- Full static type checking (type compatibility, coercion rules)
- Borrow checking (`ref`, `own`)
- Concurrency runtime
- Probabilistic programming (`prob` blocks, `sample`)
- Formal verification (`verify`)

## License

MIT
