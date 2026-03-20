# ALGOL 26 Implementation Roadmap v1.0

**Purpose:** This document outlines the comprehensive implementation plan for ALGOL 26, a language designed from the ground up to be the default language for AGI development in the GenAI ecosystem. The roadmap translates the vision into actionable phases, with technical specifications, success criteria, and risk mitigation strategies.

**Current State (Phase 1 - Complete):**
- Minimum Viable Interpreter (MVI) implemented in Python
- Fully functional lexer, parser, AST, and interpreter
- Core features working: variables, control flow (if/while/for), functions, arrays, records, basic I/O, math builtins
- Demo programs run successfully
- Repository structure:
  ```
  genai/
    algol26-interpreter/   # MVI Python implementation
    core-modules/          # Specification drafts (existing)
    docs/                  # Documentation (to be created)
    tests/                 # Test suite (to be expanded)
  ```

**Guiding Principles:**
1. **AGI-First Design:** Every feature must serve AGI development needs (reasoning, learning, self-modification)
2. **Formal Foundations:** Strong static guarantees where possible, with escape hatches for meta-programming
3. **Performance Path:** Start with Python prototype for agility, plan migration to Rust for production
4. **Incremental Delivery:** Each phase produces usable, testable results
5. **Tooling Integration:** Build compiler, debugger, and verification tools alongside language

---

## Phase 2 (Weeks 2-4): Type System + Module System

**Objective:** Transform the current dynamically-typed prototype into a statically-typed language with robust module boundaries and code reuse mechanisms.

### 2.1 Full Static Type Checking

Beyond the current minimal type inference, implement Hindley-Milner style inference with extensions:

**Type System Features:**
- **Parametric Polymorphism:** Generic functions and types with type inference
  ```algol26
  func map[T](arr: array[T], f: func(T) -> T) -> array[T] = ...
  ```
- **Algebraic Data Types (ADTs):** Sum types with pattern matching
  ```algol26
  type Result[T] = Ok(T) | Error(string)
  match x {
    Ok(val) => println("Success: " + val),
    Error(msg) => println("Failed: " + msg)
  }
  ```
- **Row Polymorphism:** For extensible records (crucial for gradual schema evolution in AGI)
  ```algol26
  type Person = { name: string, age: int, .. }  // Row variable
  func greet(p: { name: string, .. }) = println("Hello " + p.name)
  ```
- **Effect Tracking (Lightweight):** Mark pure vs impure functions (future extension for verification)

**Type Checking Algorithm:**
1. **Constraint Generation:** Convert AST to type constraints
2. **Unification:** Solve constraints with occurs-check prevention
3. **Generalization:** Compute principal types with quantified type variables
4. **Instantiation:** Replace generic variables on use sites

**Implementation Plan:**
- Week 2: Design constraint language and unifier
- Week 3: Integrate type checker into interpreter pipeline (rejection mode)
- Week 4: Add error reporting with source spans and suggestions

**Success Criteria:**
- All existing MVI demo programs type-check without modifications
- New generic examples compile correctly
- Type errors report precise locations and human-readable messages

### 2.2 Module System Design

**Goals:** Encapsulation, namespace management, separate compilation, dependency management

**Module Syntax:**
```algol26
// file: math.algol26
module math
  export abs, max, min, factorial  // Explicit export list
  private helper(x: int) = x * x   // Not exported

  public abs(x: int) = if x < 0 then -x else x
  public max(a: int, b: int) = if a > b then a else b
end module

// file: main.algol26
import math.{abs, max}           // Selective import
import stats as s                // Renamed import
import utils::*                  // Wildcard (discouraged but allowed)
```

**Module Resolution:**
- Flat namespace by default, hierarchical with `::` separator
- Search path: `./local:./vendor:./stdlib`
- Versioned packages via manifest file (future)

**Visibility Modifiers:**
- `public`: Exported and visible to importers
- `private`: Visible only within the module (default for unannotated)
- `protected`: Visible to submodules (for hierarchical packages)

**Separate Compilation:**
- Interface files (`.algol26i`) for compiled signatures
- Implementation files (`.algol26`) for source
- Incremental compilation cache

**Integration with Type System:**
- Modules as type namespaces: `math::abs` is a distinct identifier
- Signature merging: Import multiple modules, add their exports to current namespace
- Cyclic dependency detection (compile-time error)

**Success Criteria:**
- Multiple modules can be developed independently
- Import/export enforces visibility boundaries
- Compilation of small project (5+ modules) succeeds

### 2.3 Integration Plan

**Type-Module Interaction:**
1. Type checking proceeds per module, using imported signatures
2. Export lists restrict what types are visible externally
3. Generic module parameters (future): `module Vector[T](size: int) ...`
4. Cross-module inlining (optimization phase)

**Testing Strategy:**
- Unit tests for type inference engine
- Negative tests for type errors (expected failures)
- Module system integration tests with multi-file projects

**Milestone: End of Week 4**
- Type checker fully integrated
- Module system functional
- All existing tests pass under strict type checking
- Documentation: type system spec, module system guide

---

## Phase 3 (Months 2-3): Probabilistic + Causal Primitives

**Objective:** Add first-class support for uncertainty and causal reasoning, making ALGOL 26 suitable for probabilistic programming and causal inference—critical for AGI reasoning under uncertainty.

### 3.1 Probabilistic Programming Primitives

**Design Philosophy:** Integrate probability tightly with the type system. Probabilistic values are first-class, not a library.

**Core Constructs:**

1. **`prob` Blocks:** Define probability distributions
   ```algol26
   prob weather {
     rain: Bernoulli(0.3)  // Discrete random variable
     temperature: Normal(20.0, 5.0)  // Continuous
   }
   ```

2. **Distribution Types:**
   ```algol26
   type Dist[T]  // Generic distribution wrapper
   val d: Dist[int] = Bernoulli(0.5)
   val sample: int = sample(d)  // Draw a sample
   ```

3. **Conditioning (`given`):**
   ```algol26
   posterior = prob {
     x: Normal(0, 1)
     y: Normal(x, 1)
   } given (y > 1.5)  // Condition on observation
   ```

4. **Expectation and Inference:**
   ```algol26
   let expected = expectation[float](prob {
     x: Normal(0, 1)
   }, x => x^2)
   ```

**Implementation Approaches:**
- **Symbolic:** Represent distributions as expressions (for exact inference on small models)
- **Particle Filter:** Sequential Monte Carlo for approximate inference
- **Hybrid:** Use symbolic first, fall back to sampling when needed

**Type System Extensions:**
- `Dist[T]` as a distinct type (not just a runtime wrapper)
- Effect typing: `sample` marks a function as stochastic
- Certainty intervals: `value: float +- 0.05` (syntactic sugar for distribution)

**Integration Points:**
- Interoperate with existing numeric types
- Allow distributions in arrays, records, ADTs
- Generic code can abstract over distributions

### 3.2 Causal Modeling Primitives

**Goal:** Explicit causal relationships and do-calculus for intervention queries.

**Syntax:**
```algol26
causal model Medical {
  Smoking -> LungCancer  // Directed edge
  LungCancer -> Death

  // Structural equations
  P(LungCancer | Smoking) = 0.2
  P(LungCancer | ~Smoking) = 0.01
  P(Death | LungCancer) = 0.8
  P(Death | ~LungCancer) = 0.1
}

// Intervention: what if we force non-smoking?
query cause = do(model, Smoking = false, Death)
// Returns P(Death | do(Smoking=false))
```

**Semantics:**
- Compile-time validation of causal graphs (no cycles unless explicitly allowed)
- Transform do-calculus queries to conditional probability computations
- Lattice of interventions for counterfactual reasoning

**Integration with Probabilistic:**
- Causal models extend `prob` blocks with directed edges
- `do()` operator transforms causal model into new distribution
- `see()` operator for observational queries (default)

**Inference Algorithms:**
- Backdoor adjustment (automatic when possible)
- Frontdoor criterion (when backdoor fails)
- Twin network method for counterfactuals
- Gradient-based variational inference (with hardware acceleration later)

**Success Criteria:**
- Can encode classic Bayesian networks (Asia, Alarm, etc.)
- Compute marginal and conditional probabilities correctly
- Perform do-calculus interventions on non-trivial models
- Generate causal explanations (natural language output from model)

### 3.3 Type System Integration

**Probability Types:**
```algol26
type Prob[T] = Dist[T]  // Alias
type Certain[T] = T      // Zero uncertainty
type Uncertain[T] = Prob[T] | T  // Union for gradual typing

// Certainty intervals at type level:
type Speed = float +- 0.01  // Guaranteed precision
type Estimate = float +- (0.0..1.0)  // Range
```

**Effect System:**
- Mark functions that may sample: `effect sample`
- Track which variables are random vs deterministic
- Enforce that conditioning (`given`) only uses random variables

**Implementation Timeline:**
- Month 2: Design probabilistic syntax, type extensions, basic inference (enumeration)
- Month 3: Causal modeling, do-calculus, more advanced inference (MCMC), integration testing

**Milestone: End of Month 3**
- Probabilistic primitives fully type-checked and operational
- Causal modeling with do-calculus working
- Performance: small models (<20 variables) inference in <1s
- Documentation: probabilistic programming guide, causal inference tutorial

---

## Phase 4 (Months 4-6): Concurrency + Meta-Cognition

**Objective:** Enable safe parallel execution and self-reflection capabilities—foundational for AGI systems that must reason about their own reasoning.

### 4.1 Concurrency Model

**Design Choice:** Actor-model primitives with CSP-style channels, inspired by Go but with stronger safety guarantees.

**Core Primitives:**

1. **`async` / `await`:** Asynchronous functions
   ```algol26
   async fetch(url: string) -> string = {
     let resp = http_get(url)  // blocking call in async context
     await(resp)  // yields control
   }
   ```

2. **`spawn`:** Create lightweight tasks (coroutines)
   ```algol26
   let t = spawn worker()  // Returns handle
   t.join()  // Wait for completion
   ```

3. **`chan`:** Typed communication channels
   ```algol26
   let c: chan[int] = new chan[int](capacity: 10)
   c.send(42)      // Non-blocking if space
   let v = c.recv() // Blocks until available
   ```

4. **`select`:** Multi-channel wait
   ```algol26
   select {
     case c1.recv(v) => println("From c1: " + v)
     case c2.send(123) => println("Sent to c2")
     case after(1000ms) => println("Timeout")
   }
   ```

**Memory Safety Strategy:**

**Option A: Borrow Checker (Rust-style)**
- Ownership types track who owns data
- Borrow checking prevents data races at compile time
- Steeper learning curve but zero runtime overhead
- **Implementation Cost:** High (complex type system extension)

**Option B: Garbage Collection (with region inference)**
- Stop-the-world or concurrent GC
- Region-based inference to reduce GC pressure
- **Implementation Cost:** Medium (GC implementation)

**Recommendation:** Start with **Option B** (GC) for rapid prototyping, but design type system to allow future migration to borrow checking. GC is acceptable for AGI research workloads, and region inference can achieve near-manual performance for many workloads.

**Implementation Plan:**
- Month 4: Design async/await, scheduler, stack management
- Month 5: Implement channels and select, deadlock detection
- Month 6: Memory management (GC or experimental borrow checker), stress testing

**Concurrency Safety Features:**
- Static analysis for data races (even with GC)
- Channel type checking: send/receive types must match
- Deadlock detection at runtime (cycle in wait graph)
- Async function isolation: cannot block on synchronous I/O

### 4.2 Meta-Cognitive Constructs

**Vision:** ALGOL 26 programs should be able to introspect and modify their own structure and behavior—self-reflection as a first-class feature.

**`meta` Blocks:** Code that operates on code

```algol26
meta analyze(func: FuncDef) -> {
  arity: int,
  sideEffects: bool,
  complexity: float
} = {
  // 'func' is an AST node, not a function value
  // Can inspect structure, transform, generate new code
  return {
    arity: length(func.params),
    sideEffects: containsIO(func.body),
    complexity: estimateComplexity(func.body)
  }
}

// Usage:
let stats = analyze(my_function)
```

**Reflection API:**
```algol26
// Get current execution context
let ctx = reflection.current()

// Inspect call stack
for frame in ctx.stack {
  println(frame.function + " at line " + frame.line)
}

// Dynamic code generation
let code = parse("func add(x: int, y: int) = x + y")
let add = eval(code)  // Evaluate in current or new namespace
```

**Self-Modification:**
```algol26
// Sandboxed code rewriting
let old = read_module("my_algol")
let new = transform(old, rule => rule match {
  IfStmt(cond, then, else) => IfStmt(not(cond), else, then)  // Swap branches
})
write_module("my_algol", new)  // Requires appropriate capability
```

**Capability-Based Security:**
- Meta operations require capabilities (permissions)
- Capabilities can be granted or revoked dynamically
- Sandboxing untrusted code with limited capabilities
- Capability propagation tracking

**Integration with Concurrency:**
- Meta operations can run in separate async tasks
- Shared mutable AST caches require synchronization
- Consider read/write locks for module databases

**Implementation Timeline:**
- Month 4: AST reification (convert runtime values to AST)
- Month 5: Reflection API (stack inspection, namespace queries)
- Month 6: Safe eval, sandboxing, capability system

**Success Criteria:**
- Concurrent programs with channels run without data races
- Meta programs can analyze and transform code structures
- Self-modification under capability constraints works
- Performance: async tasks overhead <10% vs synchronous

---

## Phase 5 (Months 7-12+): Formal Verification + Advanced Features

**Objective:** Provide machine-checkable correctness guarantees and hardware-aware performance for AGI systems that require provable safety and efficiency.

### 5.1 Verification Infrastructure

**Verification Syntax:**

1. **Pre/Post Conditions:**
   ```algol26
   func factorial(n: int) -> int
     requires n >= 0
     ensures result >= 1
   {
     if n == 0 then 1 else n * factorial(n-1)
   }
   ```

2. **Loop Invariants:**
   ```algol26
   func sum(arr: array[int]) -> int = {
     var total = 0
     var i = 0
     while i < length(arr)
       invariant 0 <= i <= length(arr)
       invariant total == sum(arr[0..i])
     {
       total = total + arr[i]
       i = i + 1
     }
     return total
   }
   ```

3. **`verify` Blocks:** Standalone proofs
   ```algol26
   verify {
     forall x: int, y: int.
       (x >= 0 && y >= 0) ==> (x + y >= 0)
   }
   ```

4. **Temporal Assertions (for concurrent code):**
   ```algol26
   always {
     mutex.locked ==> !(mutex.locked by other)
   }
   ```

**Proof Obligations:**
- Generate VC (Verification Conditions) from annotated code
- Discharge VCs using SMT solvers (Z3, CVC5) and model checkers
- Failing proofs produce counterexamples

**SMT Integration:**
- Translate ALGOL 26 expressions to SMT-LIB
- Register theories: arrays, bitvectors, probabilistic operators
- Incremental solving for complex proofs
- Extract proof certificates for auditability

**Model Checking (for concurrent/temporal properties):**
- State space exploration with bounded model checking
- Symbolic model checking with BDDs
- Abstraction-refinement loop for infinite-state systems

**Semi-Automated Proofs:**
- Interactive proof mode with tactic language
- Lemma libraries for standard algorithms
- Proof reuse across modules

### 5.2 Hardware Acceleration Primitives

**Rationale:** AGI workloads are compute-intensive; need access to GPU/TPU without leaving ALGOL 26.

**GPU Intrinsics:**
```algol26
// Matrix multiplication on GPU
@kernel(gpu) matmul[A: float, B: float] -> float = {
  let block = thread_block(16, 16)
  let i = block.row * 16 + thread_id.x
  let j = block.col * 16 + thread_id.y
  var sum = 0.0
  for k in 0..N {
    sum = sum + A[i][k] * B[k][j]
  }
  return sum
}

// Transfer data to device
let A_gpu = to_device(A)
let B_gpu = to_device(B)
let C_gpu = matmul(A_gpu, B_gpu)
let C = from_device(C_gpu)
```

**SIMD Vectorization:**
```algol26
@vectorize(width: 8)  // Auto-vectorize over 8 lanes
func add(a: array[float], b: array[float]) -> array[float] = {
  for i in 0..length(a) {
    a[i] + b[i]  // Compiles to SIMD instruction
  }
}
```

**Heterogeneous Compute Graph:**
- Task graph with device annotations
- Auto-scheduling: partition compute graph across CPU/GPU/TPU
- Data movement minimization (pinning, zero-copy where possible)

**Implementation:**
- Month 7-8: GPU kernel language, basic memory model
- Month 9-10: Advanced scheduling, multi-GPU
- Month 11-12: Integration with probabilistic inference (accelerate MCMC)

### 5.3 Self-Modifying Code Sandbox

**Use Cases:** AGI self-improvement, evolutionary algorithms, dynamic compilation.

**Sandbox Architecture:**
- Isolated namespace for code generation/evaluation
- Capability-limited: sandbox may not escape or access host resources without permission
- Observable semantics: all effects logged for audit

**Safe Recompilation:**
```algol26
sandbox modify {
  // Generate new version of function
  let new_code = optimize(old_code)
  let new_fn = compile(new_code)  // Compiles to bytecode
  replace(fn_pointer, new_fn)     // Atomically swap
}
```

**Versioning and Rollback:**
- Every modification creates new version (immutable old versions retained)
- Automatic checkpointing before modifications
- Rollback capability if verification fails

**Integration with Verification:**
- Re-verify modified code automatically
- Prove that modifications preserve critical invariants
- Generate proof obligations for self-modifications

**Timeline:** Month 10-12 (overlap with hardware acceleration)

### 5.4 Additional Advanced Features (Stretch)

- **Gradual Typing:** Allow dynamic types for rapid prototyping, then refine
- **Dependent Types (light):** Value-dependent types (e.g., `array[T, n: int]`)
- **Effect Handlers:** Algebraic effects for first-class control flow (backtracking, async)
- **Interoperability:** C FFI, Python embedding (for ML libraries)

**Milestone: End of Month 12**
- Formal verification core functional (pre/post, invariants)
- SMT integration with 70%+ proof automation for standard specs
- GPU kernels compile and run on test hardware
- Self-modification sandbox with audit logs
- Documentation: verification guide, GPU programming manual

---

## Compiler/Interpreter Architecture Decision

**Question:** Stay with Python prototype or rewrite in Rust?

### Analysis

**Python Prototype:**
- ✅ Current implementation complete (MVI)
- ✅ Rapid iteration, easy debugging
- ✅ Rich ecosystem (ML libraries for probabilistic inference)
- ❌ Performance: ~5-10x slower than native
- ❌ Deployment: Python runtime dependency
- ❌ Memory: Higher overhead

**Rust Rewrite:**
- ✅ Performance: near C/C++ speeds, predictable latency
- ✅ Memory safety without GC (but we plan GC anyway for concurrency)
- ✅ Growing ecosystem (SMT solver bindings, GPU crates)
- ❌ Development speed: slower than Python
- ❌ Doesn't leverage existing Python inference implementations
- ❌ Need to reimplement parser, type checker, interpreter from scratch

### Recommended Strategy: **Multi-Stage Compilation Hybrid**

**Architecture:**
```
Stage 1: ALGOL 26 Source → AST (Python prototype maintained)
         |
         v
Stage 2: AST → HIR (High-level IR) in Rust
         |
         v
Stage 3: HIR → MIR (Mid-level IR) in Rust
         |
         v
Stage 4: Optimization passes (Rust)
         |
         +--> Bytecode (for JIT)
         |
         +--> LLVM IR → Native code (AOT)
```

**Execution Modes:**
1. **Interpretation:** Compile to bytecode, run by bytecode VM (fast startup, medium speed)
2. **JIT:** Profile-guided recompilation of hot paths to native code
3. **AOT:** Ahead-of-time compilation for production deployment

**Implementation Plan:**
- Months 1-3: Continue Python prototype for language design (agile)
- Month 4: Begin Rust implementation of type checker and module system (in parallel)
- Month 6: Rust interpreter with bytecode VM (feature parity with Python prototype)
- Month 9: JIT compilation layer (using Cranelift or LLVM)
- Month 12: AOT compilation pipeline mature

**Benefits:**
- Early language development in fast-iteration Python
- Rust rewrite gives performance and safety without disrupting design
- Gradual migration: Python prototype serves as reference implementation
- Testing: Cross-validate Python and Rust outputs on test cases

**Risk:** Maintaining two implementations doubles work.

**Mitigation:**
- Use Python prototype as executable spec; Rust must pass all same tests
- Auto-generate Rust tests from Python test suite
- Stop Python development once Rust feature-complete (Month 9)

---

## Testing Strategy

**Layered Approach:**

### Unit Tests
- Location: `tests/unit/`
- Framework: Built-in test harness (like Rust's `cargo test`)
- Coverage: Every function/module tested
- Goal: >90% line coverage

**Example:**
```algol26
test "type inference simple" {
  let x = 42
  assert typeof(x) == int
}

test "channel send/recv" {
  let c = new chan[string]()
  spawn async {
    c.send("hello")
  }
  assert c.recv() == "hello"
}
```

### Property-Based Testing
- Framework: QuickCheck-style generator library
- Properties: Laws that should hold for all inputs

**Examples:**
- "Map composition: map(f, map(g, xs)) = map(x => f(g(x)), xs)"
- "Type inference principal: inferred type is most general"
- "Sort stability: equal elements preserve original order"

### Fuzzing
- Grammar-based fuzzer for parser
- Mutation fuzzer for type checker
- AFL or libFuzzer integration
- Coverage-guided corpus management

### Formal Verification Test Suite
- Specifications in ALGOL 26 itself
- Check that proofs complete successfully
- Regression tests for counterexamples

### Integration Tests
- End-to-end compilation of non-trivial programs
- Cross-module compilation
- Concurrency stress tests (1000+ threads)

**Test Infrastructure:**
- `algol26-test` command: run all tests with filters
- CI integration: run tests on every commit
- Coverage reporting: upload to Codecov
- Performance regression tests: benchmark suite

---

## Build System and CI/CD Pipeline

### Build System

**Choice: Custom with Cargo-like experience**

Simplify for small project; avoid heavyweight solutions.

**Structure:**
```
genai/
  algol26/              # Language definition (parser, type checker)
  runtime/              # Runtime library (GC, threads, math)
  stdlib/               # Standard library
  compiler/             # Compiler frontend/backend
  tools/                # Linter, formatter, debugger
  tests/                # Test suite
  examples/             # Demo programs
  docs/                 # Documentation
```

**Build Tool:** `algo` (custom)
- `algo build` - Build compiler andstdlib
- `algo run <file>` - Compile and run
- `algo test` - Run tests
- `algo fmt` - Format code
- `algo check` - Type check without running

**Dependencies:**
- Rust toolchain (rustc, cargo)
- LLVM (optional, for native codegen)
- Python (for prototyping phase only)
- CMake (for C dependencies like GC)

### CI/CD Pipeline

**Platform:** GitHub Actions (or GitLab CI)

**Jobs:**
1. **Lint** - `algo fmt --check`, clippy, markdown lint
2. **Build** - Compiler builds on Linux/macOS/Windows
3. **Unit Tests** - All unit tests, coverage upload
4. **Integration Tests** - Compile and run example programs
5. **Fuzzing** - Run fuzzer for 1 hour, detect crashes
6. **Formal Verification** - Run SMT-based proofs
7. **Docs** - Build and deploy documentation site

**Triggers:**
- On push to main: run all jobs
- On PR: run lint, build, unit tests
- Nightly: full suite including fuzzing and verification

**Artifacts:**
- Compiler binary (for each platform)
- Test coverage reports
- Fuzzing corpus (store as artifact)

**Release Process:**
- Semantic versioning: MAJOR.MINOR.PATCH
- Automated release via GitHub Actions on tag push
- Release notes auto-generated from commit messages
- Binary uploads to GitHub Releases

---

## Milestone Breakdown

### Month 1 (MVI Polish)
- Week 1-2: Improve error messages, add debugger
- Week 3-4: Property-based testing for interpreter, fuzzing setup
- Deliverable: Production-ready Python interpreter (v0.1)

### Month 2-3 (Phase 2 & 3 Overlap)
- Month 2:
  - Type system design and implementation (Hindley-Milner)
  - Begin module system
  - Start probabilistic programming design
- Month 3:
  - Complete module system
  - Implement basic probabilistic distributions (Bernoulli, Normal)
  - Conditioning and inference (enumeration)
- Deliverable: Statically-typed ALGOL 26 with probabilistic programming (v0.2)

### Month 4-6 (Phase 4)
- Month 4:
  - Concurrency primitives (async/await, spawn)
  - Begin meta-cognition (AST reification)
- Month 5:
  - Channels, select, deadlock detection
  - Reflection API (stack inspection)
- Month 6:
  - Memory management (GC implementation)
  - Safe eval and sandboxing
  - Concurrency stress tests
- Deliverable: Concurrent, reflective ALGOL 26 (v0.3)

### Month 7-9 (Phase 5 Begins)
- Month 7:
  - Verification syntax (pre/post, invariants)
  - SMT solver integration (Z3 bindings)
- Month 8:
  - Automatic VC generation
  - Proof automation (70% coverage)
- Month 9:
  - Start Rust rewrite (bytecode VM)
  - Performance comparisons
- Deliverable: Core verification and Rust bytecode VM (v0.4)

### Month 10-12 (Phase 5 Complete)
- Month 10:
  - GPU kernel language
  - Self-modifying code sandbox
- Month 11:
  - Multi-GPU scheduling
  - Verification of concurrent programs
- Month 12:
  - Polish documentation
  - Performance tuning
  - v1.0 release candidate
- Deliverable: Production-ready ALGOL 26 v1.0 with verification and GPU support

---

## Dependencies Between Phases

```
Phase 2 (Type System) ──┐
                        ↓
Phase 3 (Probabilistic) → Phase 4 (Concurrency) → Phase 5 (Verification)
                        ↓                        ↓
                 Prob types used in          Prove concurrent
                 concurrent programs          programs correct
                        ↓                        ↓
                 Causal models need           Hardware acceleration
                 deterministic type system    for inference
```

**Critical Dependencies:**
- Phase 3 requires Phase 2: Probabilistic types need static typing
- Phase 4 requires Phase 2: Channels need parametric types for safety
- Phase 5 requires Phase 2: Verification needs type info
- Phase 5 requires Phase 4: Verify concurrent algorithms

**Can Parallelize:**
- Rust rewrite can begin while Python prototype still active (after Month 4)
- Documentation writing can proceed alongside implementation

---

## Risk Assessment and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Type system too complex** | Medium | High | Start with simpler HM inference, add features incrementally; fall back to dynamic typing if needed (gradual typing) |
| **Probabilistic inference too slow** | High | Medium | Implement multiple backends (enumeration, importance sampling, MCMC); allow user to choose; profile and optimize hot paths; use GPU acceleration in Phase 5 |
| **Concurrency bugs (data races, deadlocks)** | Medium | High | Use GC + static analysis to catch races early; deadlock detection at runtime; extensive stress testing |
| **SMT solver integration unstable** | Medium | Medium | Use well-maintained bindings; cache solver results; provide fallback to manual proofs when automation fails |
| **Rust rewrite delayed** | High | Medium | Use Python prototype as reference; limit Rust scope to critical components first (type checker); consider keeping Python as fallback |
| **Feature creep (AGI vision too broad)** | High | High | Strict milestone discipline; defer stretch goals to v2.0; prioritize AGI-critical features (probability, verification) over nice-to-haves |
| **Insufficient testing leads to bugs** | Medium | High | Enforce TDD: write tests before features; mandatory code review; continuous fuzzing |
| **Poor documentation hinders adoption** | Medium | Medium | Docs-as-code: write docs alongside features; user testing with external developers |
| **Hardware acceleration complex** | High | Medium | Start with simple GPU kernels; target specific hardware first (NVIDIA CUDA); abstract device layer for future expansion |
| **Self-modification security vulnerabilities** | Medium | High | Capability system mandatory; sandboxing enforced by compiler; security audit before release |

**Overall Risk Score:** Medium. Vision is ambitious but phases are incremental. Major risk is scope creep and performance bottlenecks. Mitigation via strict milestones and early prototyping of performance-critical components.

---

## Success Metrics (v1.0 Release)

- **Adoption:** 3+ external projects using ALGOL 26 (not GenAI team)
- **Performance:** interpreter <2x slower than optimized C; JIT within 20% of C
- **Verification:** 500+ lemmas proved in stdlib; CI automatically proves PRs
- **AGI Applications:** At least one AGI research prototype (e.g., probabilistic planner) implemented in ALGOL 26
- **Correctness:** Zero soundness bugs found in 6 months after release
- **Usability:** Average onboarding time <1 day for experienced programmers

---

## Conclusion

This roadmap translates the ALGOL 26 vision into an actionable, phased implementation plan. The sequence (types → probability → concurrency → verification) builds capabilities incrementally while maintaining a working language at every stage. The hybrid Python→Rust architecture balances agility with performance. Risk mitigation is built into milestones and testing. If executed as planned, ALGOL 26 will be the first language designed explicitly for AGI development with formal guarantees and hardware acceleration.

**Next Steps:**
1. Finalize Phase 2 specification with team review
2. Begin type system implementation in Python prototype
3. Set up repository structure as outlined
4. Establish CI/CD pipeline (Week 1)
5. Write test plan and initial test suite
6. Begin formal documentation in `docs/`

**Contact:** This roadmap is a living document. Revise quarterly or after major milestone completions.

---

*Document Version:* 1.0  
*Date:* 2025-01-15  
*Author:* GenAI Language Team  
*Status:* Draft for review
