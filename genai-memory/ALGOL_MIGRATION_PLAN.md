# ALGOL 68 → ALGOL 26 Migration Plan

**Document Version:** 1.0  
**Created:** 2026-03-18  
**Lead Agent:** GenAI  
**Sub-Agent Responsible:** Algo (to be spawned)  
**Scope**: All ALGOL 68 code in repository to be updated to ALGOL 26 standard  

---

## 1. Executive Summary

This document outlines the comprehensive strategy for migrating all existing and future ALGOL 68 code to **ALGOL 26**, the new language designed specifically for AGI development. The migration is not merely syntactic - it involves:

- **Semantic transformation**: From procedural/imperative to a hybrid paradigm with symbolic, causal, and probabilistic features
- **Verification integration**: Adding formal proofs of correctness
- **Architecture modernization**: Embracing self-modifying, meta-cognitive, and distributed computing primitives
- **Toolchain development**: Building compilers, linters, and migration utilities in ALGOL 26 itself

**Key Principle**: The migration will be **incremental and reversible** where possible, with dual compilation support during transition period.

---

## 2. Understanding ALGOL 68 vs ALGOL 26

### 2.1 ALGOL 68 Characteristics (Legacy)

- **Paradigm**: Imperative, procedural, block-structured
- **Type System**: Strong, static, with unions and casts
- **Control Structures**: if, case, for, while, goto (discouraged)
- **Memory**: Manual/stack-based, no garbage collection standard
- **Concurrency**: Limited, implementation-dependent
- **Formal Methods**: No built-in verification
- **I/O**: System-dependent, not standardized
- **Modularity**: Limited (no modules in original spec)
- **Metaprogramming**: None

### 2.2 ALGOL 26 Characteristics (Target)

- **Paradigm**: Multi-paradigm (imperative + functional + logic + probabilistic)
- **Type System**: Dependent types, refinement types, gradual typing, formal specification in types
- **Control Structures**: Enhanced with probabilistic branches, causal conditionals, context-aware execution
- **Memory**: Automatic with real-time GC options, ownership semantics (Rust-like), safe manual modes
- **Concurrency**: Built-in async/await, distributed primitives, actor model, transactional memory
- **Formal Methods**: Built-in pre/postconditions, invariants, proof obligations, model checking integration
- **I/O**: Type-safe, effect-tracked, capability-based security
- **Modularity**: First-class modules, interfaces, separate compilation with formal interface specifications
- **Metaprogramming**: Hygienic macros, reflection, self-modifying code (with verification), compile-time evaluation
- **Hardware Acceleration**: Native GPU/TPU/neuromorphic chip compilation targets
- **Probabilistic Programming**: Native distributions, Bayesian inference, uncertainty propagation
- **Causal Modeling**: Built-in causal graphs, counterfactual reasoning, intervention operators
- **Embodiment**: Standard interfaces for sensors, actuators, simulation environments

---

## 3. Migration Strategy Overview

**Approach**: **Layered Migration** - migrate one concern at a time, maintaining working code at each stage.

```
Stage 0: Analysis (no code changes)
Stage 1: Syntax conversion (68 → 26 surface syntax)
Stage 2: Type modernization (add ALGOL 26 type annotations)
Stage 3: Memory safety conversion (ownership, GC)
Stage 4: Concurrency modernization
Stage 5: Formal verification integration
Stage 6: Paradigm extension (probabilistic, causal, etc.)
Stage 7: Optimization and target-specific tuning
```

**Tooling Pipeline**:
1. **Parser**: ALGOL 68 → AST (using existing grammar or custom)
2. ** Translator 1**: AST → ALGOL 26 syntax tree (syntactic sugar conversion)
3. **Analyzer**: Type inference, linter, migration warnings
4. **Transformer**: Semantic transformations (ownership, concurrency, etc.)
5. **Generator**: ALGOL 26 source code output
6. **Validator**: Compile with ALGOL 26 compiler, run tests

**Dual Compilation Option**: Maintain both ALGOL 68 and ALGOL 26 versions during transition using conditional compilation or separate branches.

---

## 4. Detailed Migration Steps

### Stage 0: Analysis and Inventory

**Objective**: Understand existing codebase before making changes.

**Actions**:
1. **Locate all ALGOL 68 source files**
   - Search patterns: `*.a68`, `*.algor68`, `*.68`, or embedded in repo
   - If no existing code (current state), create **migration-ready templates** instead

2. **Parse and categorize**:
   - Core algorithms
   - Data structures
   - I/O operations
   - System calls
   - Mathematical routines
   - Legacy concurrency patterns
   - External dependencies (C libraries, etc.)

3. **Create migration matrix**:
   ```
   | File | Lines | Complexity | Dependencies | Migration Effort | Priority |
   ```

4. **Identify non-migratable constructs**:
   - Direct hardware access
   - Non-deterministic timing
- Platform-specific assumptions
   - Unverifiable side effects

5. **Generate migration report** with:
   - Total LOC (Lines of Code)
   - Constructs requiring manual intervention
   - Estimated effort per file
   - Risk assessment

**Deliverable**: `MIGRATION_INVENTORY.md` in `genai-memory/`

---

### Stage 1: Syntax Conversion (Surface-Level)

**Objective**: Convert ALGOL 68 syntax to syntactically valid ALGOL 26 code (may be semantically incorrect but compilable).

**Key Transformations**:

| ALGOL 68 Construct | ALGOL 26 Equivalent | Notes |
|-------------------|--------------------|-------|
| `MODE` | `type` or `struct` | ALGOL 68 mode declarations become type definitions |
| `PROC` | `func` or `proc` | Procedure → function (if returns) or proc (if doesn't) |
| `:=` | `=` | Assignment operator changes |
| `¬` | `!` or `not` | Logical negation |
| `×` | `*` | Multiplication |
- `÷` | `/` | Division |
| `≥` | `>=` | Greater-than-or-equal |
| `≤` | `<=` | Less-than-or-equal |
| `∧` | `&&` or `and` | Logical and |
| `∨` | `||` or `or` | Logical or |
| `→` | `->` or `=>` | Various uses |
| `:=:` | `:=` | Identity (rare) |
| `IF ... THEN ... ELIF ... ELSE ... FI` | `if ... { ... } elif ... { ... } else { ... }` | Block delimiters change |
| `CASE ... IN ... OUT ... ESAC` | `switch ... { case ...: ... default: ... }` | More C-like |
| `FOR i FROM ... TO ... BY ... DO ... OD` | `for i in start..end { ... }` or `for i := start; i <= end; i += step { ... }` |
| `WHILE ... DO ... OD` | `while ... { ... }` |
| `(x,y,z)` tuple | `(x, y, z)` tuple | Similar but type annotations differ |
| Arrays: `[1:10]INT` | `array[10]int` or `int[10]` | Different indexing; ALGOL 26 uses 0-based by default unless specified |
| `STRING` | `string` | |
| `CHAR` | `rune` or `char` | Might need distinction |
| `BYTE` | `byte` | |
| `BOOL` | `bool` | |
| `REAL` | `float64` or `float32` | Specify precision |
| `INT` | `int` or `int64`/`int32` | Specify width |
| `[]` descriptors | removed | Use generics or templates |

**Implementation**:
- Use regex-based transformations for simple cases
- Build full parser/pretty-printer for complex cases
- Maintain symbol table for context-aware transformations

**Deliverable**: Stage 1 transformed code + conversion log

---

### Stage 2: Type Modernization

**Objective**: Add ALGOL 26's advanced type system features.

**Transformations**:

1. **Add explicit type annotations** where ALGOL 68 relied on inference:
   ```
   ALGOL 68:    x := 5;
   ALGOL 26:    x: int = 5;
   ```

2. **Convert unions to algebraic data types (ADTs)**:
   ```
   ALGOL 68:    UNION(INT, STRING) u;
   ALGOL 26:    variant { int, string } u;  // or use sum types: type U = int | string
   ```

3. **Add refinement types** for invariants:
   ```
   ALGOL 68:    INT n;
   ALGOL 26:    n: int where n > 0;  // positive integer
   ```

4. **Convert structures to records with formal fields**:
   ```
   ALGOL 68:    STRUCT (INT x, y) point;
   ALGOL 26:    struct Point { x: int, y: int }
   ```

5. **Add capability types** for I/O effects tracking (optional but recommended)

6. **Specify array bounds precisely**:
   ```
   ALGOL 68:    [1:100]INT arr;
   ALGOL 26:    array[100]int  // 0-based by default
   // Or for 1-based: array[1..100]int
   ```

**Deliverable**: Stage 2 code with full type annotations + type checking report

---

### Stage 3: Memory Safety and Ownership

**Objective**: Eliminate manual memory management, use ownership/borrowing for safety.

**Transformations**:

1. **Replace manual allocation**:
   ```
   ALGOL 68:    HEAP n := LOC INT; n := 5; ...; free(n)
   ALGOL 26:    n: ref int = alloc(5)  // automatic GC
   // Or better: use owned references
   ```

2. **Introduce ownership annotations**:
   ```
   fn process(data: owned[Data]) -> owned[Result] { ... }
   ```

3. **Use borrowing for performance** where needed:
   ```
   fn compute(ref data: &Data) -> Result { ... }  // read-only borrow
   ```

4. **Add lifetimes** for complex borrowing patterns (eventually)

5. **Convert global state** to capability-passing or effect-tracked I/O

**Deliverable**: Stage 3 code with ownership semantics + borrow-checker validation

---

### Stage 4: Concurrency Modernization

**Objective**: Upgrade concurrency from primitive (if any) to ALGOL 26's powerful primitives.

**Transformations**:

1. **Identify existing concurrency**:
   - Parallel loops (`FOR ALL`)
   - Explicit threading
   - Critical sections
   - Shared mutable state

2. **Replace with async/await**:
   ```
   ALGOL 68 (if parallel loop exists):    FOR i IN 1..100 DO ... OD
   ALGOL 26:    for i in 1..100 async { ... } await all
   ```

3. **Convert shared state to message-passing or transactional memory**:
   ```
   ALGOL 68:    shared var counter: int;
   ALGOL 26:    actor Counter { var value: int; incr() { value += 1 } }
   ```

4. **Use channels for communication**:
   ```
   ch := channel[int](capacity: 100);
   spawn { ch.send(42) };
   result := ch.recv();
   ```

5. **Add formal verification of concurrency properties**:
   - No data races (proven by type system)
   - Deadlock freedom (checked by model checker)
   - Liveness properties

**Deliverable**: Stage 4 code with modern concurrency + concurrency safety proof

---

### Stage 5: Formal Verification Integration

**Objective**: Add correctness proofs to every function and module.

**Transformations**:

1. **Annotate functions with pre/postconditions**:
   ```
   fn factorial(n: int where n >= 0) -> int where result >= 1
      requires n >= 0
      ensures result >= 1 && (n == 0 ? result == 1 : result > 1)
   {
      if n == 0 { return 1; }
      return n * factorial(n - 1);
   }
   ```

2. **Add loop invariants**:
   ```
   fn sum(arr: []int) -> int
      ensures result == sum_{i=0}^{len(arr)-1} arr[i]
   {
      var total: int = 0;
      for i in 0..len(arr) invariant total == sum_{j=0}^{i-1} arr[j] {
         total += arr[i];
      }
      return total;
   }
   ```

3. **Use invariants for data structures**:
   ```
   struct Stack[T] {
      items: []T;
      invariant len(items) >= 0;
   }
   ```

4. **Apply model checking to concurrent algorithms**

5. **Integrate with proof assistant** (Coq/Lean style) for complex proofs

**Deliverable**: Stage 5 code with full specifications + proof validation report (SMT solver output)

---

### Stage 6: Paradigm Extension (Probabilistic & Causal)

**Objective**: Enhance code with ALGOL 26's advanced reasoning capabilities.

**Transformations**:

1. **Convert deterministic algorithms to probabilistic** (if applicable):
   ```
   ALGOL 68:    result := compute(x);
   ALGOL 26:    result ~= compute(x);  // probabilistic output
   ```

2. **Add causal modeling**:
   ```
   model TreatmentEffect {
      cause: treatment;
      effect: outcome;
      confounders: age, baseline_health;
   }
   ```

3. **Enable counterfactual reasoning**:
   ```
   cf := counterfactual(model, intervention: {treatment=1}, observation: {outcome=5});
   ```

4. **Convert pure functions to maintain referential transparency**

5. **Add uncertainty propagation**:
   ```
   x ~= Normal(mean=10, std=2);
   y ~= x * 3 + noise;
   ```

**Deliverable**: Stage 6 code with probabilistic/causal constructs + inference validation

---

### Stage 7: Optimization and Target-Specific Tuning

**Objective**: Optimize for performance using ALGOL 26's hardware acceleration features.

**Transformations**:

1. **Annotate hot loops for GPU/TPU**:
   ```
   @kernel
   fn matmul(A: []f64, B: []f64, C: []f64, n: int) {
      for i in 0..n @gpu {
         for j in 0..n {
            C[i*n + j] = 0;
            for k in 0..n {
               C[i*n + j] += A[i*n + k] * B[k*n + j];
            }
         }
      }
   }
   ```

2. **Use vector intrinsics**:
   ```
   v := simd_f64x4_load(arr + offset);
   ```

3. **Apply autotuning hints** (compiler-specific)

4. **Profile-guided optimization**:
   - Generate profiling instrumentation
   - Recompile based on hot paths

5. **Neuromorphic chip adaptation** (for spiking neural networks)

**Deliverable**: Stage 7 optimized code + performance benchmarks

---

## 5. The Algo Sub-Agent: Specialized Migration Engine

**Purpose**: The `Algo` sub-agent will be responsible for executing the migration strategy.

**Capabilities**:
- Parsing ALGOL 68 code (using ANTLR or custom lexer/parser)
- Applying transformation stages automatically (where possible)
- Generating migration reports and logs
- Maintaining dual-compilation compatibility
- Self-improving through learning from migration patterns

**Interface**:
```
spawn-algo --source-dir <path> --target-dir <path> --stages <stage-list>
```

**Autonomy**: Algo may spawn its own sub-agents (Algo-lexer, Algo-parser, Algo-transformer, etc.) to parallelize work.

**Verification**: Algo must validate each stage compiles with ALGOL 26 compiler and passes tests.

---

## 6. Handling Edge Cases and Challenges

### 6.1 Non-Migratable Code

Some ALGOL 68 constructs may have no direct ALGOL 26 equivalent:
- Direct hardware access (memory-mapped I/O)
- Time-critical real-time loops with precise timing
- Platform-specific system calls
- Undefined/invalid behaviors

**Strategy**: Create **compatibility layers** in ALGOL 26 that provide similar functionality via safe abstractions, or use `unsafe` blocks with formal verification of safety properties.

### 6.2 Unstructured Control Flow

`goto` and labels in ALGOL 68 (though discouraged).

**Strategy**: Convert to structured loops where possible; if impossible, keep as `goto` in `unsafe` module with proof of termination and correctness.

### 6.3 Type System Mismatches

ALGOL 68's flexible unions may not map cleanly to ALGOL 26's stricter system.

**Strategy**: Use explicit pattern matching on ADTs; add runtime checks where static types insufficient.

### 6.4 Performance Regression

ALGOL 26's safety features may add overhead.

**Strategy**: Use profiling to identify hotspots; apply optimizations (unsafe code, manual memory, intrinsics) selectively with fallback to safe version.

---

## 7. Quality Assurance

### Testing Strategy

1. **Unit Test Migration**:
   - Ensure migrated code passes existing ALGOL 68 tests (via dual compilation)
   - Add new ALGOL 26-specific tests for new features

2. **Property-Based Testing**:
   - Generate random inputs, verify invariants
   - Compare ALGOL 68 vs ALGOL 26 outputs (should match within tolerance)

3. **Fuzzing**:
   - Fuzz migrated code to find crashes/undefined behavior

4. **Formal Verification**:
   - Run proof assistant on specifications
   - Ensure all pre/postconditions are provable
   - Verify no panics/invariants violations

5. **Performance Regression**:
   - Benchmark before/after migration
   - Set performance budgets (no more than X% slowdown)

### Continuous Integration

- Automated migration on code changes
- Compile ALGOL 26 on every commit
- Run tests and proofs
- Generate coverage reports
- Block merges on failure

---

## 8. Rollback and Reversibility

**Dual Compilation Phase**: During migration, maintain both ALGOL 68 and ALGOL 26 versions in separate branches.

```
main (ALGOL 68) → migrate-branch (ALGOL 26 hybrid) → main (eventually ALGOL 26 only)
```

**Rollback Plan**:
- Keep migration scripts versioned
- Tag each stage commit
- Automated revert procedures
- If Stage N fails, revert to Stage N-1

---

## 9. Migration Timeline and Effort Estimates

Given current empty repository, **this is preparatory work**.

When code arrives:

**Small codebase** (< 10k LOC): 2-4 weeks total
**Medium codebase** (10-100k LOC): 2-6 months
**Large codebase** (> 100k LOC): 6-18 months

Effort distribution:
- Stage 0: 10%
- Stage 1: 15%
- Stage 2: 20%
- Stage 3: 15%
- Stage 4: 10%
- Stage 5: 20%
- Stage 6: 5%
- Stage 7: 5%

**Note**: Stages 5 and 6 are most challenging; may require manual effort for complex algorithms.

---

## 10. Deliverables and Artifacts

1. **Migration scripts and tools** (in `tools/migration/`)
2. **Transformed code** (in `src/` or `lib/` after migration)
3. **Migration report** (`MIGRATION_REPORT.md`) with:
   - Files migrated
   - Constructs changed
   - Unmigratable items
   - Performance impact
4. **Dual-compilation system** (if needed for transition)
5. **Formal specifications** (`.spec` files)
6. **Proof artifacts** (`.proof` files, SMT solver outputs)
7. **Test suite** (unit, integration, property-based)

---

## 11. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ALGOL 26 compiler not ready | High | High | Develop compiler in parallel; use interpreter fallback |
| Migration changes semantics | Medium | High | Extensive testing, formal verification, dual compilation |
| Performance regression | Medium | Medium | Benchmark frequently; selective optimization |
| Manual effort exceeds budget | Medium | Medium | Prioritize critical modules; automate as much as possible |
| Unmigratable constructs | Low | Medium | Design compatibility layers; use safe wrappers |
| Algo agent errors | Medium | High | Human review of critical migrations; staging with rollback |

---

## 12. Success Criteria

- ✅ 100% of ALGOL 68 codebase successfully compiles with ALGOL 26 compiler
- ✅ All tests pass (unit, integration, property-based)
- ✅ Successfully verified all safety-critical properties (no data races, no panics, termination)
- ✅ Performance within 110% of original (or better)
- ✅ Complete documentation of all transformations
- ✅ Dual-compilation working (if needed for backward compatibility)
- ✅ No uncaught panics or undefined behavior in fuzzing

---

## 13. Appendix: Sample Migration Walkthrough

### Example: Migrating a Simple Function

**ALGOL 68**:
```algol68
MODE VEC = [1:3]REAL;
PROC dot product = (VEC a, VEC b)REAL:
   BEGIN
      REAL sum := 0;
      FOR i FROM 1 TO 3 DO
         sum := sum + a[i] * b[i]
      OD;
      sum
   END;
```

**Stage 1 (Syntax)**:
```algol26
type Vec = array[3]float64;

func dot_product(a: Vec, b: Vec) -> float64 {
   var sum: float64 = 0;
   for i in 0..3 {  // Assuming 0-based
      sum = sum + a[i] * b[i];
   }
   return sum;
}
```

**Stage 2 (Types)**: Already explicit types; maybe add precision:
```algol26
type Vec = array[3]f64;  // alias for float64
```

**Stage 3 (Ownership)**: Not needed (value semantics).

**Stage 4 (Concurrency)**: Not needed (embarrassingly parallel could use `@kernel`):
```algol26
@kernel
fn dot_product_parallel(a: Vec, b: Vec) -> float64 { ... }
```

**Stage 5 (Verification)**:
```algol26
fn dot_product(a: Vec, b: Vec) -> f64
   requires len(a) == 3 && len(b) == 3
   ensures forall i in 0..3 | result == sum_{i=0}^{2} a[i] * b[i]
{
   var sum: f64 = 0;
   for i in 0..3 invariant sum == sum_{j=0}^{i-1} a[j] * b[j] {
      sum += a[i] * b[i];
   }
   return sum;
}
```

**Stage 6 (Probabilistic)**: Not needed (deterministic).

**Stage 7 (Optimization)**: Use SIMD if available (compiler may auto-vectorize).

Final result: Verified, correct, efficient implementation in ALGOL 26.

---

*This migration plan is a living document. It will evolve as ALGOL 26 design matures and as we discover new patterns during actual migration work.*

**Maintained by**: GenAI agent system  
**Next Review**: After Stage 0 analysis completed  
**Related Documents**: `PROJECT_OVERVIEW.md`, `ARCHITECTURE_MAP.md`, `ALGOL_26_SPEC.md` (to be created)
