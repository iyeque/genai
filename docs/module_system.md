# ALGOL 26 Module System Guide

## Introduction

Modules provide encapsulation, namespace management, and separate compilation. Each source file constitutes a module. Modules may export selected bindings and import from other modules.

## Module Declaration

Optionally, a module may declare its name using:
```algol26
module MyModule;
```
If omitted, the module name is derived from the filename (without extension). The declaration is not required for single-file programs.

## Exporting

Top-level declarations (variables, constants, procedures, types) are **private by default**. To make a binding visible to importers, use an `export` statement:

```algol26
export foo, bar, baz;
```

Multiple `export` statements are allowed; the exported set is the union.

If a module contains **no** `export` statements, it exports **nothing** (fully encapsulated).

## Importing

Import statements bring external bindings into the current module's scope.

### Syntax
```
import module_name;                    // wildcard import of all exports
import module_name as alias;           // import the module itself as a namespace
import module_name.{a, b, c};          // selective import of specific names
```

- `module_name` is a dot-separated identifier path (e.g., `math`, `utils.collections`).
- The file is searched in the **search path**: `./local:./vendor:./stdlib` relative to the current module's directory, plus the current directory itself.
- Imported names must be present in the source module's export set, otherwise a type error occurs.
- If `as alias` is used, the module is bound as a **namespace** – a record type whose fields are the exported bindings.

### Examples

**Wildcard import:**
```algol26
import math;   // brings all exports of math.algol26 into scope
```

**Selective import:**
```algol26
import math.{abs, max};  // only abs and max are imported
```

**Renamed import:**
```algol26
import statistics as stats;
println(stats.mean(...));
```

## Compilation Model

1. **Parsing** – Each module is parsed into an AST.
2. **Type Checking** – The type checker runs on the module. When an import statement is encountered, the imported module is recursively parsed and type-checked (if not already cached).
3. **Environment Merging** – The exported bindings of the imported module are added to the current module's environment.
4. **Cycle Detection** – Circular imports are detected and rejected: if module A imports B and B imports A (directly or indirectly), an error is reported.

## Separate Compilation (MVP)

- **Interface files** (`.algol26i`) are not yet used. The source of imported modules is read and type-checked on demand.
- A **module cache** stores already-loaded modules to avoid repeated work.
- The **search path** is consulted to locate module files; it includes the module's own directory, then `local`, `vendor`, and `stdlib` subdirectories.

## Visibility and Encapsulation

- Exports are explicit; any name not listed in an `export` statement remains private to the module.
- There is no `private` keyword; the default is private.
- Types defined in a module may be exported, enabling other modules to use them in type annotations.

## Example

**File: `math.algol26`**
```algol26
export abs, max

proc abs(x: int) => int = if x < 0 then -x else x;
proc max(a: int, b: int) => int = if a > b then a else b;
```

**File: `main.algol26`**
```algol26
import math.{abs, max};

begin
  println(abs(-5));    // prints 5
  println(max(3, 7));  // prints 7
end
```

Both programs type-check and run correctly.

## Limitations

- No versioning of modules (future).
- No support for parameterized modules (functors).
- No explicit `private` modifier on individual declarations; visibility is controlled solely by export lists.
- Import statements are top-level only; nested imports not allowed.
