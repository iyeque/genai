# ALGOL 26 Type System Specification

## Overview

ALGOL 26 employs a Hindley-Milner style static type system with several extensions to support advanced language features. Type inference is performed before execution, ensuring type safety while allowing concise code with optional type annotations.

## Core Types

### Primitive Types
- `int` — arbitrary-precision integers
- `real` — double-precision floating point
- `bool` — booleans `true` / `false`
- `char` — single characters
- `string` — immutable strings
- `void` — no value (for procedures)
- `null` — null reference

### Composite Types

#### Function Types
`(param1: T1, param2: T2, ...) -> ReturnType`  
Optionally annotated with an effect: `~ EffectType`. Effects track side effects; currently a placeholder.

#### Array Types
`array[N] of T` — fixed-size array with compile-time constant `N`.  
Size is part of the type but does not affect unification (arrays of different sizes are compatible if element type matches).

#### Record Types
`{ field1: T1, field2: T2, ... }` — unordered collection of named fields.  
Records support **row polymorphism**: a record type may end with a row variable `..r` to enable extension.

#### Algebraic Data Types (ADTs)
Sum types defined as a union of constructors:
```
type Result[T] = Ok(T) | Error(string)
```
Each constructor may carry arguments. Pattern matching (not yet implemented) selects on constructors.

## Type Inference

### Algorithm
1. **Constraint Generation** — Traverse AST, assigning fresh type variables to unknowns, and generate equality constraints between types.
2. **Unification** — Solve constraints via Robinson's algorithm with occurs check.
3. **Generalization** — At `let`-bindings (top-level declarations), quantify over type variables not free in the environment (let-polymorphism).
4. **Instantiation** — When a polymorphic value is used, replace quantified variables with fresh ones.

### Polymorphism
Top-level `var`, `const`, `proc` declarations are generalized, allowing them to be used at multiple instantiations.

### Row Polymorphism
Record types may include a row variable (e.g., `{ name: string, ..r }`) to represent an open record. Row variables unify with additional fields, enabling functions like:
```
fun extend[T, R](r: { x: T, ..R }) = { y: int, ..R }
```

### Effects (Stub)
Each function may carry an effect variable. For now, all functions are considered impure (`eff`). Future versions will distinguish `pure` functions.

## Type Checking Modes

The interpreter runs the type checker **before evaluation**. If type checking fails, the program is rejected with detailed error messages including source locations.

### Type Annotation Forms
- In variable declarations: `var x: T := expr;` (optional if initializer present)
- Constants: `const x: T = expr;` (type required)
- Functions: `proc f(p: T) => R = body;`
- Parameters: `param: T`
- Record fields: `field: T` inside record constructor

If a type annotation is omitted and an initializer exists, the type is inferred.

## Numeric Coercion

Arithmetic operators (`+`, `-`, `*`, `/`, `%`, `^`) accept `int` or `real` operands. The `/` operator always yields a `real`, promoting its operands as needed. Mixed `int`/`real` arithmetic automatically promotes `int` to `real`.

## Built-in Types and Functions

A set of primitive types and standard library functions are provided in the initial environment:
- Math: `sqrt(real) -> real`, `exp(real) -> real`, `sin(real) -> real`, etc.
- Conversion: `int(x) -> int`, `real(x) -> real`, `char(x) -> char`, `string(x) -> string`
- I/O: `println(...)`, `print(...)` (dynamic, accept any arguments)

## Limitations (MVP)

- No dependent types or refinement types (future)
- No effect polymorphism (future)
- ADTs are recognized but pattern matching not yet implemented
- Module system is functional but limited to file-based modules; no generic modules yet.

## Error Reporting

Type errors include:
- Mismatched types (e.g., `expected int, got real`)
- Undefined identifiers
- Arity mismatches in function calls
- Record field errors

Errors report the source location (line and column) from the original tokens.
