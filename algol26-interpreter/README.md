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

The interpreter now implements:

- **Full static type checking** using Hindley-Milner inference with extensions:
  - Parametric polymorphism
  - Algebraic Data Types (ADT) (stubbed)
  - Row polymorphism for extensible records
  - Lightweight effect tracking (pure vs impure)
- **Module system**:
  - `module` declarations
  - `import` statements with selective, renamed, and wildcard imports
  - `export` statements to control visibility
  - Search path: `./local:./vendor:./stdlib`
- Core language: variables, control flow (if, while, for), functions (proc), arrays, records.
- Built-in functions: `println`, `print`, math functions (`exp`, `sqrt`, `sin`, `cos`, `tan`, `log`, `abs`, etc.)
- Advanced feature stubs: `prob`, `causal`, `verify`, `async`, `await`, `chan`.

See `docs/` for detailed specifications.

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
