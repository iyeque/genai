# ALGOL 26 Type System Specification

*Version: Draft v0.1*
*Date: 2026-03-19*
*Part of: ALGOL_26_SPEC_v0.1.md*

---

## 1. Overview

ALGOL 26's type system builds upon ALGOL 68's strong, static typing heritage while incorporating modern concepts for AI-first programming:

- **Strong, static typing**: Types are known at compile time; implicit conversions are limited
- **Type inference**: Local type inference for `var` declarations reduces verbosity
- **Composite types**: Fixed-size arrays, records (structs), and function types
- **Effects and ownership**: Basic ownership and borrowing for safe memory (MVP subset)
- **Special domain types**: Integration points for probabilistic programming (`prob`), causal modeling (`causal`), and formal verification (`verify`)
- **Future extensibility**: Foundation for dependent types and refinement types in later versions

The type system is **structural** for records (compatible if same fields) and **nominal** for named types. Arrays are indexed from 1 (ALGOL 68 tradition) unless otherwise configured.

---

## 2. Primitive Types

ALGOL 26 defines the following built-in primitive types:

| Type | Description | Size/Representation | Example Literals |
|------|-------------|---------------------|------------------|
| `int` | Signed integer | Platform-dependent (typically 64-bit) | `42`, `-10`, `0xFF`, `0b1010` |
| `real` | IEEE 754 floating-point | 64-bit double precision | `3.14`, `2.5e-10`, `1.0` |
| `bool` | Boolean | 1 byte | `true`, `false` |
| `char` | Unicode scalar value | 32-bit (UTF-32) | `'a'`, `'π'`, `'\n'` |
| `string` | Immutable UTF-8 string | Variable-length | `"hello"`, `"こんにちは"` |
| `bytes` | Immutable byte sequence | Variable-length | `b"\x00\xFF"` |

### 2.1 Integer Types

In MVP, `int` is a single signed integer type. Future versions may add:
- `int8`, `int16`, `int32`, `int64`, `int128`
- `uint` variants
- `nat` (non-negative integers)

### 2.2 Floating-Point Types

In MVP, `real` is double precision (`f64`). Future versions may add:
- `float32` (single precision)
- `complex64`, `complex128` (complex numbers)

### 2.3 Character Type

`char` represents a single Unicode scalar value (code point). It is **not** a grapheme cluster; multi-codepoint emojis require strings.

### 2.4 String and Bytes

- `string`: Immutable sequence of Unicode characters (UTF-8 encoding). Requires O(n) for indexing by codepoint.
- `bytes`: Immutable sequence of raw bytes (octets). Indexing is O(1).

MVPs provide basic concatenation (`+`) and length (`len()`) operations.

### 2.5 Boolean Type

`bool` has exactly two values: `true` and `false`. Used in conditionals and logical operations.

---

## 3. Composite Types

### 3.1 Arrays

Arrays are fixed-size, homogeneous sequences. Indexing is **1-based** (ALGOL 68 tradition).

```
arrayType ::= 'array' '[' expr ']' 'of' typeName
```

**Examples:**
```algol26
var nums: array [5] of int;                 // 5 integers, indices 1..5
var matrix: array [3] of array [3] of real; // 3x3 matrix
var chars: array [10] of char;               // 10 characters
```

**Semantics:**
- Size must be a compile-time constant in MVP (no dynamic arrays yet).
- Arrays are **value types**; assignment copies all elements (deep copy for primitive element types).
- Bounds checking is **enabled by default** in debug mode; may be omitted in release for performance.
- Access: `arr[i]` (1-based). Out-of-bounds access triggers runtime error (or panic in release).

**Future:**
- Dynamic arrays (heap-allocated, variable length)
- Slices (views into arrays)
- Multi-dimensional arrays with column-major order (ALGOL 68 tradition)

### 3.2 Records (Structs)

Records are product types with named fields. They are **structural** (compatible if same field names and types).

```
recordType ::= 'record' '{' fieldList '}'
fieldList ::= field { ',' field }*
field ::= identifier ':' typeName
```

**Examples:**
```algol26
type Point = record { x: real, y: real };
type Person = record { name: string, age: int };

var p: Point := Point { x: 1.0, y: 2.0 };
var alice: Person := Person { name: "Alice", age: 30 };

// Field access
println(p.x);
p.y := 3.14;

// Record assignment (deep copy)
var p2: Point := p;
```

**Semantics:**
- Records are **value types**; assignment copies all fields.
- Field access via `.` operator.
- Record types are **structural**: two records with identical field names and types are compatible, even if not explicitly named the same.
- Order of fields does not matter for type identity.

**Future:**
- Inheritance (`extends` clause)
- Methods (functions attached to records)
- Visibility modifiers (`public`, `private`)

### 3.3 Function Types

Function types describe the signature of procedures/functions: parameter types and return type.

```
procType ::= 'proc' '(' paramList ')' '=>' typeName
```

**Examples:**
```algol26
type BinaryOp = proc (real, real) => real;
type Predicate = proc (int) => bool;

var add: BinaryOp := proc (a: real, b: real) => real = a + b;
var isEven: Predicate := proc (n: int) => bool = n % 2 = 0;
```

**Semantics:**
- Function types are **nominal** if named (`type AddFn = proc(...)`), but **structural** when used anonymously.
- Functions are **first-class**: can be assigned to variables, passed as arguments, returned from other functions.
- Closures capture environment by reference (or by value if `own` is used, see ownership section).
- The special `proc` type with no return (i.e., `=> void`) indicates procedures with side effects.

**Variadic functions** (deferred to future):
```
procType ::= ... | 'proc' '(' paramList ', ...' ')' '=>' typeName
```

---

## 4. Type Annotations

Type annotations appear in:
- Variable declarations: `var x: int := 5;`
- Constant declarations: `const PI: real := 3.14159;`
- Parameters: `proc foo(a: int, b: real) => int;`
- Return types: `proc foo() => string;`
- Type definitions: `type MyInt = int;` or `type Point = record { ... };`

**Syntax (from BNF):**
```algol26
varDecl ::= 'var' identifier ':' typeName ['=' expr] ';'
param ::= identifier ':' typeName
procDecl ::= 'proc' identifier '(' [paramList] ')' ['=>' typeName] ...
```

**Examples:**
```algol26
var count: int;                  // uninitialized (default 0 for int)
var name: string := "Alice";    // initialized
var p: Point := Point { x: 0.0, y: 0.0 };

proc add(a: int, b: int) => int = a + b;
proc printHello() => void = begin println("Hello") end;
```

**Notes:**
- Type names are identifiers that refer to previously defined types (`int`, `real`, `MyType`, etc.).
- For arrays and records, the type must be fully specified: `array [N] of T`, `record { ... }`.
- MVP requires explicit type annotations on all function parameters and return types. Type inference is limited to `var` declarations with `:=` (see next section).

---

## 5. Type Inference

ALGOL 26 supports **local type inference** for `var` declarations using the `:=` operator:

```algol26
var x := 5;          // x: int inferred
var y := 3.14;       // y: real inferred
var flag := true;    // flag: bool inferred
var s := "hello";    // s: string inferred
var arr := [1,2,3];  // arr: array [3] of int inferred (if literal array supported)
```

**Rules:**
- Inference works only on the **initializer expression**.
- The type of `x` is exactly the type of the expression on the right-hand side.
- Inference is **not** allowed for function parameters, return types, or `const` declarations (explicit types required).
- Once inferred, `x`'s type is fixed; subsequent assignments must match that type.

**Examples:**
```algol26
var x := 5;      // x: int
x := "hello";    // TYPE ERROR: cannot assign string to int

var total := 0;  // total: int (0 is int)
total := 3.14;   // TYPE ERROR: cannot assign real to int (no implicit coercion)
```

**No inference for function types:**
```algol26
var f := proc (x: int) => int = x + 1;  // OK, f: proc(int) => int
var g := x => x + 1;                    // ERROR: lambda syntax requires full type
```

**Deferred:**
- Full Hindley-Milner inference (let-polymorphism) for complex expressions
- Return type inference for functions (must be explicit in MVP)

---

## 6. Type Compatibility and Coercions

### 6.1 Assignment Compatibility

An assignment `x := expr` is type-correct if:
- `expr`'s type is **identical** to `x`'s declared type, OR
- `expr`'s type is **implicitly convertible** to `x`'s type via allowed coercions.

**Identical types:** Same primitive type, or same record structure (same fields with same types), or same array dimensions and element type.

### 6.2 Implicit Coercions (Limited)

ALGOL 26 allows **numeric promotion** in expressions:

- `int` → `real`: Widening (no information loss in typical range). Implicit in arithmetic operations:
  ```algol26
  var r: real := 5 + 3.2;  // 5 promoted to real, result real
  var r2: real := 5;       // ERROR: no implicit assignment conversion
  ```
  Note: The last line is an error because assignment requires explicit conversion. Use `real(5)` or `5.0`.

- `char` ↔ `int`: No implicit conversion. Must use explicit conversion functions: `int('A')` → 65, `char(65)` → 'A'.

- `string` ↔ `bytes`: No implicit conversion. Use `string(b)` or `bytes(s)`.

**No other implicit coercions** in MVP. No `bool` → `int`, no `int` → `bool`, etc.

### 6.3 Explicit Conversions

Conversion functions (built-in) allow explicit type casts:

```algol26
real(5)        // int to real: 5.0
int(3.14)      // real to int: truncates to 3
char(65)       // int to char: 'A'
int('A')       // char to int: 65
string(123)    // int to string: "123"
bytes("abc")   // string to bytes: b"abc"
```

**Rules:**
- Conversions may **panic on invalid values** (e.g., `int(1e100)` overflow, `char(-1)` out of range).
- Convert between numeric types with possible loss: `real` → `int` truncates; `int` → `byte` may overflow (wraps or panics? MVP: panic).
- Record and array conversions are **not allowed** except identity.

### 6.4 Subtype Polymorphism (Future)

Deferred to later versions. MVP has no subtyping (except structural record compatibility).

### 6.5 Type Equality

Two types are equal if:
- Both are the same primitive type, OR
- Both are arrays with same size (compile-time constant equal) and equal element types, OR
- Both are records with same set of field names (order irrelevant) and equal field types, OR
- Both are function types with same parameter types (names irrelevant) and same return type.

Type names are **aliases**, not new types:
```algol26
type MyInt = int;
var a: MyInt := 5;  // OK, MyInt is just another name for int
var b: int := a;    // OK, compatible
```

To define a **distinct** type (new nominal type), use `newtype` (deferred to future):
```algol26
newtype UserId = int;  // distinct from int, requires explicit conversion
```

---

## 7. Effects and Ownership (MVP Basics)

ALGOL 26 introduces **ownership** and **borrowing** inspired by Rust, but simplified for MVP. This ensures memory safety without a full garbage collector (though a simple GC fallback is available).

### 7.1 Ownership

Every value has a single **owner** — the variable that holds it directly. When the owner goes out of scope, its value is freed (for heap-allocated types like future dynamic arrays).

```algol26
var s: string := "hello";  // s owns the string
// When s goes out of scope, the string is freed
```

**Ownership applies to:**
- Strings (heap-allocated)
- Future dynamic arrays
- Structs containing heap-allocated fields

**Arrays and records** in MVP are stack-allocated and copied on assignment, so ownership is less critical but still tracked for clarity.

### 7.2 Borrowing with `ref`

To pass a value without transferring ownership, use `ref` (borrowed reference):

```algol26
proc modify(x: ref int) =
  x := x + 1;

var a: int := 5;
modify(a);   // passes a borrowed reference, a remains valid after
println(a);  // 6
```

**Rules:**
- `ref T` means "borrowed pointer to T".
- Borrowed references are valid only for the duration of the call.
- At most **one** mutable borrow (`ref`) of a value can exist at a time.
- Multiple immutable borrows (`ref const`? deferred) may coexist.

**MVP Limitation:**
- Borrow checking is **not fully enforced** in Week 2 interpreter (no borrow checker yet). The `ref` keyword is recognized but semantics are shallow (like pass-by-reference).
- Full borrow checking (aliasing rules) is deferred to a later version.

### 7.3 Explicit Ownership Transfer: `own`

To explicitly transfer ownership (e.g., moving a value into a struct), use `own`:

```algol26
type Bag = record { items: array [10] of int; count: own int };

var b: Bag := Bag { items: [0,0,0,0,0,0,0,0,0,0], count: 0 };
// count is owned by b; original variable (if any) is no longer valid
```

**MVP Limitation:**
- `own` is recognized but not fully enforced. The interpreter may permit it as documentation only.

### 7.4 Interaction with GC

A simple **tracing garbage collector** (mark-and-sweep) is available as a fallback for heap-allocated types (strings, dynamic arrays). When a value is no longer reachable, the GC frees it. Ownership annotations help avoid relying on GC for performance-critical code.

### 7.5 Summary for MVP

- **No borrow checker yet**: `ref` is pass-by-reference (like C++ reference), not a full linear type.
- **No compile-time ownership errors**: The interpreter allows `ref` and `own` but does not enforce exclusivity.
- **GC enabled by default**: Simplified memory management; ownership is advisory and for future optimization.

---

## 8. Special Feature Integration: `prob`, `causal`, `verify`

ALGOL 26's type system interacts with probabilistic programming, causal inference, and formal verification features.

### 8.1 Probabilistic Programming (`prob`)

`prob` blocks introduce random variables and distributions. Their **type system** extends standard types with **distribution types**.

```
probType ::= 'Distribution' '<' typeName '>'
```

**Examples:**
```algol26
prob x: Distribution<int> ~ Bernoulli(0.5);
prob y: Distribution<real> ~ Normal(0.0, 1.0);
```

**Type rules:**
- A `prob` declaration binds a name to a **distribution** over a base type `T`. The base type must be a primitive or composite type that can be sampled.
- The `~` operator assigns a distribution: left side must be `Distribution<T>`, right side a distribution expression (e.g., `Bernoulli(p)`, `Normal(μ, σ)`).
- Inside a `prob` block, **conditioning** via `factor(expr: bool)` constrains the sample space. The argument must be boolean-typed.
- `sample(expr: Distribution<T>) => T` extracts a random sample from a distribution (concrete `T`).

**Compatibility:**
- `Distribution<T>` is **not** assignable to `T` directly; must use `sample()`.
- Distribution types are **nominal** (named by `Distribution<T>`). Two `Distribution<int>` values are compatible.

**MVP Implementation:**
- In Week 2 interpreter, `prob` is a **no-op stub** that logs or returns deterministic values. The type `Distribution<T>` is recognized but treated as `T` internally.
- Full probabilistic inference (e.g., MCMC) is deferred.

**Deferred:**
- Probabilistic effect tracking (what distributions a function samples from)
- Conditioning on continuous variables
- Weighted samples and evidence

### 8.2 Causal Modeling (`causal`)

`causal` blocks enable causal inference with interventions. Types describe **causal graphs** and **potential outcomes**.

**Conceptual type:**
```
causalType ::= 'CausalModel'  // opaque handle to a causal DAG
```

**Example:**
```algol26
causal model := CausalModel.fromGraph( /* edges */ );
intervene(model, X := 5);
var Y_post: real := outcome(model, Y);
```

**Type rules:**
- `CausalModel` values are created via `CausalModel.fromGraph(...)`, which takes a description of variables and causal edges.
- `intervene(model: CausalModel, assignment: (var := value))` returns a new `CausalModel` with intervention applied.
- `outcome(model: CausalModel, var: identifier) => Distribution<T>` returns the distribution of `var` given the model.
- Variables in the graph have types (`int`, `real`, etc.). The causal engine tracks these.

**MVP Implementation:**
- `causal` is a **stub**; `CausalModel` is a placeholder type with no operations.
- Type checking ensures correct usage but runtime does nothing.

**Deferred:**
- Structural causal models (SCMs) with equations
- Counterfactual queries
- Identification algorithms

### 8.3 Formal Verification (`verify`)

`verify` annotations attach **specifications** to functions and statements. Types interact with specifications through **refinement types** (deferred to future). For MVP, `verify` is a **comment-like directive** that does not affect runtime types.

**Syntax:**
```algol26
proc sorted(arr: array [N] of int) => void
  verify (forall i: int in 1..N-1 => arr[i] <= arr[i+1]);

begin
  // implementation
end
```

**Type rules:**
- `verify` clauses attach to function declarations, loops, or blocks.
- The expression inside `verify` must be **boolean-typed** (predicate over parameters and variables).
- Specifications are **erased** at runtime (zero-cost in release). In debug mode, `assert` checks them.

**MVP Implementation:**
- `verify` is recognized but ignored by interpreter. No checking performed.
- Future: Integrate with SMT solver for static verification; runtime checks in debug.

### 8.4 Interaction Summary

| Feature | Type Extension | MVP Status |
|---------|----------------|------------|
| `prob` | `Distribution<T>` nominal wrapper | Recognized, treated as `T` |
| `causal` | `CausalModel` opaque type | Recognized, stub |
| `verify` | No new types (uses predicates) | Recognized, ignored |

---

## 9. Dependent Types and Refinement Types (Future)

ALGOL 26 aims to support **dependent types** and **refinement types** in later versions, enabling compile-time proofs about program properties.

### 9.1 Refinement Types

A refinement type restricts a base type with a predicate:

```
{ x: int | 0 <= x < 100 }   // integers between 0 and 99
{ s: string | len(s) > 0 }  // non-empty strings
```

**Syntax** (not in MVP):
```algol26
var age: {int | 0 <= age && age < 150} := 25;
```

**Verification:**
- The predicate must be provable at compile time (via SMT) or checked at runtime (panic on violation).
- Subtyping: `{T | P}` is a subtype of `T`.

### 9.2 Dependent Function Types

Function return types or parameter types can depend on values of other parameters:

```
proc repeat(char: char, count: int) => array [count] of char
```

The return type mentions `count` from the parameter list. This is **dependent typing**.

**MVP:** Not supported. Functions have fixed return types independent of parameter values.

### 9.3 Path to Future

- **Phase 1 (MVP)**: No dependent types. Only simple types.
- **Phase 2**: Basic refinement types with runtime checks (similar to `assert` in types).
- **Phase 3**: SMT integration for compile-time proof of refinements.
- **Phase 4**: Full dependent types with value-dependent return types.

---

## 10. Type Errors and Diagnostics

### 10.1 Common Type Errors

1. **Type mismatch**
   ```algol26
   var x: int := 3.14;  // ERROR: real cannot be assigned to int without conversion
   ```
   Fix: Use explicit conversion: `var x: int := int(3.14);`

2. **Undefined type**
   ```algol26
   var x: MyType;  // ERROR: MyType not declared
   ```
   Fix: Declare `type MyType = ...;` first.

3. **Wrong number of array dimensions**
   ```algol26
   var mat: array [3] of int;
   var elem := mat[1, 2];  // ERROR: int[1,2] is not defined; use mat[1][2]
   ```

4. **Missing field in record constructor**
   ```algol26
   type Point = record { x: real, y: real };
   var p := Point { x: 1.0 };  // ERROR: missing field y
   ```

5. **Incompatible function signature**
   ```algol26
   var f: proc(int) => real := proc (x: int) => int = x;  // ERROR: return type mismatch
   ```

6. **Incorrect number of arguments**
   ```algol26
   proc add(a: int, b: int) => int = a + b;
   var sum := add(5);  // ERROR: expected 2 args, got 1
   ```

7. **Cannot assign to function parameter (if not `var` parameter)**
   ```algol26
   proc foo(x: int) = x := 5;  // ERROR: x is immutable parameter
   ```
   Fix: Use `var` parameter (deferred) or assign to local variable.

8. **Cannot use `var` with `prob`**
   ```algol26
   var p: Distribution<int> ~ Bernoulli(0.5);  // ERROR: use `prob`, not `var`
   ```
   Fix: `prob p: Distribution<int> ~ Bernoulli(0.5);`

### 10.2 Error Message Format

The interpreter should produce:
```
error: type mismatch at line 12, column 15
  got: real
  expected: int
  hint: use explicit conversion e.g., int(expr)
```

---

## 11. MVP Scope (Week 2 Interpreter)

### 11.1 Implemented Types

**Primitive types (all):**
- `int`, `real`, `bool`, `char`, `string`

**Composite types:**
- Fixed-size arrays: `array [N] of T` with compile-time constant `N`
- Records: `record { field1: T1, field2: T2, ... }`
- Function types: `proc (T1, T2, ...) => R` (used in variable declarations and parameters)

**Null/void:**
- `void` return type (procedures with no return value)
- `null` literal (but no nullable types yet; deferred)

### 11.2 Implemented Type Features

✅ **Type annotations** on all declarations (variables, constants, parameters, returns)
✅ **Type inference** for `var x := expr` (local inference only)
✅ **Assignment compatibility**: identical types and numeric promotion in expressions
✅ **Explicit conversions**: `int()`, `real()`, `char()`, `string()`, `bytes()` (basic)
✅ **Array and record operations**: indexing, field access, constructors
✅ **Function types** as first-class values (assignable, passable)
✅ **Basic error checking**: mismatched types, wrong arity, missing fields

### 11.3 Deferred (Post-MVP)

- **Full borrow checker** (ownership/borrowing enforcement) — `ref` and `own` are parsed but not checked
- **Dynamic arrays** (heap-allocated, variable size)
- **Slices**
- **Dependent/refinement types**
- **Subtyping** (except structural records)
- **Generics/parametric polymorphism** (all types must be concrete)
- **TypeClasses** (ad-hoc polymorphism)
- **Module-level type checking** (no imports yet)
- **Effect typing** (probabilistic effects, I/O effects) — `prob`/`causal`/`verify` are stubs
- **Union types** (sum types)
- **Nullable types** (`?T`)
- **Type inference for function bodies** (all return types explicit)

### 11.4 Interpreter Type Checking Strategy

The Week 2 interpreter performs **semantic analysis** in a single pass after parsing:

1. Build symbol table (scopes: global, function, block)
2. Check each declaration:
   - Type name exists (primitive or user-defined)
   - For arrays: size expression is integer constant
   - Initializer expression type matches declared type (or infer if `:=` without explicit type)
3. Check each statement:
   - Assignment LHS and RHS types compatible
   - Procedure call arguments match parameter types
   - Return expression matches function return type
4. Expressions: compute result type using operator typing rules
5. Report first error encountered (stop). Later: collect all errors.

**No separate inference phase:** Inference happens during declaration checking with initializer.

---

## 12. Type System Examples

### 12.1 Type-Correct Programs

**Example A: Basic types and inference**
```algol26
var x := 5;           // x: int
var y := 3.14;        // y: real
var s := "hello";     // s: string
var flag := true;     // flag: bool

x := 10;              // OK, same type
y := real(x);         // OK, explicit conversion
```

**Example B: Arrays and records**
```algol26
type Vec3 = record { x: real, y: real, z: real };
var v: Vec3 := Vec3 { x: 1.0, y: 2.0, z: 3.0 };

var arr: array [3] of int := [10, 20, 30];
var sum := arr[1] + arr[2] + arr[3];  // 60
```

**Example C: Functions**
```algol26
proc square(x: int) => int = x * x;

var f: proc(int) => int := square;
var result: int := f(5);  // 25
```

**Example D: Nested structures**
```algol26
type Matrix = array [2] of array [2] of real;
var m: Matrix := [[1.0, 2.0], [3.0, 4.0]];
var a: real := m[1][2];  // 2.0
```

**Example E: Explicit conversions**
```algol26
var i: int := 5;
var r: real := real(i);   // 5.0
var c: char := char(65);  // 'A'
var s: string := string(123);  // "123"
```

### 12.2 Common Type Errors

**Error 1: Mismatched assignment**
```algol26
var x: int := 3.14;
// error: cannot assign real to int
```

**Error 2: Incompatible operator operands**
```algol26
var s: string := "hello";
var b: bool := s < "world";
// error: '<' not defined for string (only for numbers in MVP)
```

**Error 3: Wrong array size**
```algol26
var a: array [5] of int := [1,2,3];  // only 3 elements, need 5
// error: array literal has 3 elements, expected 5
```

**Error 4: Missing record field**
```algol26
type R = record { a: int, b: int };
var r: R := R { a: 1 };
// error: missing field b
```

**Error 5: Function signature mismatch**
```algol26
var f: proc(int) => real := proc (x: int) => int = x;
// error: return type int not compatible with real
```

**Error 6: Using undeclared identifier**
```algol26
var x := unknown;
// error: identifier 'unknown' not declared
```

**Error 7: Non-constant array size**
```algol26
var n: int := 5;
var a: array [n] of int;  // ERROR: array size must be constant
```

---

## 13. Conclusion

This type system specification defines a **pragmatic, static type system** for ALGOL 26 that balances ALGOL 68 heritage with modern needs. The MVP implementation in Week 2 will support the essentials: primitive types, arrays, records, functions, basic inference, and explicit conversions. Advanced features (dependent types, full ownership, effect tracking) are deferred but the foundation is laid for future expansion.

The integration with `prob`, `causal`, and `verify` is designed as **stubs** in MVP, allowing syntax and basic type checking without runtime semantics. This enables the language to be prototyped quickly while reserving complex implementation for later iterations when the interpreter core is stable.

---

## Appendix: Type Grammar Summary

```
typeName ::= 'int' | 'real' | 'bool' | 'char' | 'string' | 'bytes'
           | 'void'
           | identifier                // user-defined type alias
           | 'array' '[' expr ']' 'of' typeName
           | 'record' '{' fieldList '}'
           | 'proc' '(' paramList ')' '=>' typeName
           | 'Distribution' '<' typeName '>'  // prob feature
           | 'CausalModel'                    // causal feature

fieldList ::= field { ',' field }*
field ::= identifier ':' typeName

paramList ::= [param { ',' param }]
param ::= identifier ':' typeName

expr (with type rules):
  - Primary: literals, identifiers, parentheses
  - Unary: `-` (numeric), `not` (bool)
  - Multiplicative: `*`, `/`, `%` (numeric operands)
  - Additive: `+`, `-` (numeric or string concat? deferred)
  - Comparison: `=`, `<>`, `<`, `<=`, `>`, `>=` (any comparable types)
  - Logical: `and`, `or` (bool operands only)
  - Ternary: `cond ? thenExpr : elseExpr` (deferred)
  - Function call: `f(args)`
  - Array indexing: `arr[i]` (arr: array[T], i: int)
  - Record access: `rec.field` (rec: record with field)
```

---

**End of Type System Specification**
