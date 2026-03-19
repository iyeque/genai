# ALGOL 26 Concurrency and Memory Model Specification

*Version: Draft v0.1*
*Date: 2026-03-20*
*Part of: ALGOL_26_SPEC_v0.1.md*

---

## 1. Memory Model

ALGOL 26's memory model combines **ownership** and **borrowing** concepts with a **tracing garbage collector** fallback. This hybrid approach ensures memory safety while allowing flexibility for AI workloads that manipulate complex data structures.

### 1.1 Ownership Semantics (MVP)

Every value in ALGOL 26 has a single **owner** — the variable that holds it directly on the stack or owns the heap allocation. Ownership determines when memory is freed.

**Stack allocation**: Primitive types (`int`, `real`, `bool`, `char`) and fixed-size arrays/records are typically allocated on the stack and automatically freed when the scope exits.

**Heap allocation**: Strings, dynamic arrays (future), and structs containing heap-allocated fields live on the heap and are freed when:
- The owner's scope ends, **and**
- No other references (borrowed or GC roots) exist

**Example:**
```algol26
begin
  var s: string := "Hello";  // s owns the string
  // s goes out of scope here → string freed (if no other references)
end;
```

**Ownership transfer** (MVP: conceptual only):
```algol26
type Buffer = record { data: array [1024] of byte; len: own int };
// The `own` keyword indicates that `len` is owned by the Buffer struct
// and cannot be separately referenced outside the struct
```

**MVP Limitation**: The Week 2 interpreter does **not** enforce ownership at compile time. The `own` keyword is recognized but treated as documentation. Full ownership checking is deferred to post-MVP.

### 1.2 Borrowing with `ref`

To pass a value without transferring ownership, use `ref` (borrowed reference). This allows temporary access to a value while maintaining a single owner.

```algol26
proc double(x: ref int) =
  x := x * 2;

var a: int := 5;
double(a);   // Passes a borrowed reference; `a` remains valid
println(a);  // 10
```

**Borrowing rules (theoretical, not enforced in MVP):**
- At any point, a value can have **either**:
  - Exactly one **mutable** borrow (`ref T`), **or**
  - Zero or more **immutable** borrows (`ref const T` — defer to later)
- Borrowed references must not outlive the owner
- Borrow checking happens at compile time (like Rust)

**MVP Implementation:**
- `ref` parameters are implemented as **pass-by-reference** (similar to C++ references)
- No compile-time borrow checking; the interpreter allows overlapping mutable and immutable references
- Runtime: accessing a reference after the owner is freed is **undefined behavior** (GC may have collected it)

### 1.3 Garbage Collection Fallback

A **simple mark-and-sweep garbage collector** is available as a fallback for heap-allocated objects. This is particularly useful for:
- Strings that escape their scope
- Future dynamic arrays
- Data structures with shared ownership (e.g., graph structures)

**GC Roots:**
- All global variables
- All local variables on the active call stack
- Registers/CPU variables in the interpreter

**Collection Trigger:**
- Manual: `gc_collect()` invoked by program
- Automatic: When heap allocation exceeds threshold (not in MVP)

**MVP Implementation:**
- GC is **disabled by default** in Week 2 interpreter (deterministic drop semantics)
- Stub implementation: `gc_collect()` is a no-op
- Full GC integration is deferred

### 1.4 Interaction with Concurrency

When concurrency is introduced, the memory model must ensure:
- Values shared across threads are either immutable or properly synchronized
- Borrowed references do not escape across thread boundaries without ownership transfer
- The GC is **stop-the-world** in MVP (simple but pauses all threads)

---

## 2. Concurrency Primitives

ALGOL 26 provides a set of concurrency primitives inspired by modern languages (Go, Rust, Kotlin) while maintaining ALGOL 68's structured programming heritage.

### 2.1 Async/Await

**Asynchronous functions** (`async`) allow non-blocking operations that can be suspended and resumed. `await` yields control until the async computation completes.

**Syntax:**
```algol26
async proc fetchData(url: string) => string
  // body may contain I/O calls that suspend
  begin
    var response := http_get(url);  // hypothetical async I/O
    await response;                // yield until response ready
    result := response.body
  end;

begin
  var task := fetchData("https://api.example.com/data");
  // task is a "promise" or "future" that will contain the string result
  println("Task started, doing other work...");
  var data: string := await task;  // blocks until fetchData completes
  println("Received: ", data)
end
```

**Semantics:**
- `async proc` returns a **future** (a handle to an in-progress computation)
- `await expr` suspends the current async context until `expr` resolves
- `async` functions can call `await` on futures; non-async functions cannot
- The runtime may execute multiple async functions on a thread pool

**MVP Implementation:**
- `async` and `await` are **recognized but stubbed**
- `async proc` returns a dummy future object
- `await` immediately returns the value (no suspension)
- Full async runtime (event loop, futures, task scheduling) is deferred

**Deferred:**
- `async let` bindings (structured concurrency)
- Task cancellation
- Timeouts

### 2.2 Channels

**Channels** (`chan`) provide typed, synchronous or asynchronous message passing between concurrent tasks (actors/threads).

**Syntax:**
```algol26
var ch: chan int := chan int();      // unbuffered (synchronous) channel
var bufCh: chan string := chan string(10);  // buffered channel with capacity 10

// Send
ch send 42;               // blocks until receiver ready
bufCh send "hello";       // non-blocking if buffer not full

// Receive
var msg: int := ch recv;  // blocks until message arrives
var s: string := bufCh recv;  // blocks if buffer empty

// Non-blocking try (future):
if ch try recv into msg then
  println("Got: ", msg)
else
  println("No message yet")
```

**Channel types:**
- `chan T` — channel that carries values of type `T`
- Unbuffered channels: sender and receiver must both be ready (rendezvous)
- Buffered channels: `chan T(capacity)` allows `capacity` pending sends without receiver

**Example: Producer-Consumer**
```algol26
async proc producer(out: chan int) =>
  for i: int := 1 to 10 do
    begin
      println("Producing: ", i);
      out send i
    end;

async proc consumer(in: chan int) =>
  begin
    var count: int := 0;
    while count < 10 do
      begin
        var item: int := in recv;
        println("Consumed: ", item);
        count := count + 1
      end
  end;

begin
  var q: chan int := chan int(5);  // buffered
  var p := producer(q);
  var c := consumer(q);
  await p;  // wait for producer to finish
  await c   // wait for consumer to finish
end
```

**MVP Implementation:**
- `chan T` is a **stub type**; `chan int()` returns a dummy object
- `send` and `recv` are no-ops or return immediate dummy values
- No actual concurrency; all operations are synchronous in the single-threaded interpreter

**Deferred:**
- Buffered vs unbuffered channel semantics
- Channel selection (`select` statement: wait on multiple channels)
- Channel closing
- Broadcast channels

### 2.3 Spawn/Thread

**Thread creation** (`spawn`) launches a new OS thread (or green thread) that executes a procedure concurrently.

**Syntax:**
```algol26
spawn proc worker(id: int) =>
  begin
    println("Worker ", id, " starting");
    // do work...
    println("Worker ", id, " done")
  end;

begin
  var t1 := spawn worker(1);
  var t2 := spawn worker(2);
  // Wait for both threads to complete
  t1 join;
  t2 join
end
```

**Thread handles:**
- `spawn proc foo(args)` returns a **thread handle** (`thread`)
- `t join` blocks until thread `t` finishes
- `t detach` allows thread to run independently (fire-and-forget)

**Shared memory:**
- Threads share the same address space (global variables, heap)
- Local variables are thread-private
- Synchronization required for shared mutable state (see Section 4)

**MVP Implementation:**
- `spawn` runs the procedure **synchronously** in the current thread (no actual parallelism)
- Returns a dummy thread handle with `join` that does nothing
- No thread creation or context switching

**Deferred:**
- Real OS threads or green threads with preemption
- Thread pools
- Thread-local storage
- Thread cancellation

### 2.4 Actor Model (Optional)

ALGOL 26 may support **actors** as a higher-level concurrency primitive (deferred beyond MVP):

```algol26
actor Counter =
  begin
    var count: int := 0;
    proc inc() = count := count + 1;
    proc get() => int = count
  end;

begin
  var c := Counter();   // creates actor with its own thread/mailbox
  c inc();              // message send (asynchronous)
  var current := c get();  // synchronous call or message with response
  println(current)
end
```

Actors combine encapsulated state with a message-passing interface, eliminating shared mutable state by design.

**MVP**: Not implemented. Consider for post-MVP.

---

## 3. Scheduling Model

### 3.1 Cooperative vs Preemptive

ALGOL 26's Week 2 interpreter uses **cooperative scheduling** for async tasks (when implemented):

- Tasks voluntarily yield at `await` points or explicit `yield()` calls
- No involuntary preemption; a long-running CPU-bound task can starve others
- Simpler to implement and reason about

**Future (post-MVP):** May introduce **preemptive scheduling** with time-slicing for CPU-bound tasks, but cooperative is preferred for deterministic behavior and easier formal verification.

### 3.2 Runtime Scheduler (Future Architecture)

When async/await and threads are fully implemented:

- **Thread-per-core**: OS threads for blocking I/O operations
- **Thread pool**: Reusable worker threads for CPU-bound async functions
- **Task queue**: Each thread has a local deque for work-stealing
- **Futures/promises**: Each async function returns a future; completion triggers dependent `await`s

**Context switching**: In MVP, no context switching. In full implementation, lightweight async contexts (stackless coroutines) for async functions, OS threads for `spawn`ed procedures.

### 3.3 Determinism and Reproducibility

ALGOL 26 aims for **deterministic parallel execution** where possible:
- Given same inputs and same scheduling decisions, parallel programs should produce identical outputs
- This is important for formal verification and debugging AI systems
- Randomness (`prob`) must be controlled: either thread-local RNG or explicit RNG parameters

---

## 4. Shared Mutable State Rules

Shared mutable state is a common source of concurrency bugs (data races). ALGOL 26 enforces rules through a combination of ownership, borrowing, and explicit synchronization primitives.

### 4.1 Data Race Prevention

A **data race** occurs when two threads concurrently access the same memory location, and at least one access is a write, and there is no synchronization.

ALGOL 26 prevents data races via:

1. **Ownership uniqueness**: A value can only be mutated by its owner.
2. **Borrow checking**: When a value is borrowed (`ref`), no other mutable access (including another borrow) is allowed during the borrow's lifetime.
3. **Synchronization primitives**: For truly shared data, use locks, atomics, or channels.

### 4.2 The `sync` Qualifier

To share a variable across threads, mark it `sync` (synchronized). This indicates that accesses to the variable are automatically protected by a lock (or are atomic).

```algol26
var counter: sync int := 0;  // thread-safe integer

proc increment() =
  counter := counter + 1;  // atomic or locked increment

begin
  var t1 := spawn increment();
  var t2 := spawn increment();
  t1 join;
  t2 join;
  println(counter)  // guaranteed to be 2 (no data race)
end
```

**MVP Implementation:**
- `sync` is **recognized but not enforced**
- Accesses to `sync` variables are treated as normal (no locking)
- Full `sync` semantics deferred

**Future:**
- `sync` could map to atomic operations for primitive types, or a mutex for composite types
- Could also introduce `atomic` blocks for manual lock-free programming

### 4.3 Locks (Mutexes)

For explicit control, use `lock`:

```algol26
var mutex: lock;  // creates a mutex
var shared: int := 0;

proc safeIncrement() =
  with mutex do
    shared := shared + 1;

begin
  // spawn many safeIncrement tasks
  // ...
end
```

**Syntax:**
```algol26
lock myLock: lock;                    // declare mutex
with myLock do                        // acquire lock, execute block, release
  shared := shared + 1;
```

**MVP Implementation:**
- `lock` type is recognized but `with` does nothing (no actual locking)
- Deferred to post-MVP

### 4.4 Immutable Data

The safest way to share data across threads is to make it **immutable**:

```algol26
const config: record { host: string, port: int } :=
  config { host: "localhost", port: 8080 };

// All threads can read `config` safely because it never changes
```

Constants (`const`) and values that don't use `var` are immutable. Records and arrays are deeply immutable if all their fields/elements are immutable.

**Immutable by default?**
ALGOL 26 does **not** make data immutable by default (unlike Rust). Mutation is allowed but must be carefully controlled in concurrent contexts.

### 4.5 Send vs Share

- **Send** (`chan send value`): Transfers ownership of `value` to the receiver. After sending, the sender cannot access `value` (compiler may enforce or it's a logic error).
- **Share** (via `sync` or immutable data): Both sides can access simultaneously with synchronization.

### 4.6 Summary of Shared State Rules (MVP)

In the Week 2 interpreter (no real concurrency):
- No data races because there are no concurrent threads
- `sync`, `lock`, `ref` are all no-ops
- The rules are **descriptive only**; the interpreter does not enforce them

These rules become critical when the full concurrent runtime is implemented. It's essential to design the type system and semantics now to avoid retrofitting breaking changes.

---

## 5. Interaction with `prob` and `causal`

ALGOL 26's probabilistic programming (`prob`) and causal modeling (`causal`) features must interact correctly with concurrency. This is an advanced topic, especially for AI workloads that require sampling from distributions in parallel or causal inference across distributed data.

### 5.1 Probabilistic Programming and Concurrency

`prob` declarations introduce **random variables** with associated distributions. When combined with concurrency:

- Each concurrent task/thread should have its own **random number generator (RNG) state** to avoid contention and ensure reproducible sampling.
- By default, `prob` variables use a **thread-local RNG** seeded from a global source.
- To share an RNG explicitly (e.g., for correlated sampling), pass an `RNG` object as a parameter.

**Example:**
```algol26
prob x: Distribution<real> ~ Normal(0.0, 1.0);
// x is sampled from thread-local RNG

async proc sampleMany(n: int) => array [n] of real =
  begin
    var results: array [n] of real;
    for i: int := 1 to n do
      results[i] := sample(x);  // each sample uses thread-local RNG
    result := results
  end;
```

**Parallel sampling:**
```algol26
begin
  var tasks: array [4] of future array [1000] of real;
  for i: int := 1 to 4 do
    tasks[i] := sampleMany(1000);  // 4 parallel samplers
  
  // Await all and combine
  var all: array [4000] of real;
  for i: int := 1 to 4 do
    begin
      var chunk := await tasks[i];
      // copy chunk into all
    end
end
```

**Determinism:** For reproducibility, the RNG seed should be controllable:
```algol26
set_rng_seed(12345);  // global seed for main thread
// Or pass explicit RNG objects to tasks to control per-thunk seeds
```

**MVP Implementation:**
- `prob` is a stub; `Distribution<T>` is just `T`
- `sample(expr)` returns a fixed deterministic value (e.g., 0.0)
- No actual random number generation; no thread-local RNG

**Deferred:**
- Proper distribution types and sampling
- Thread-local RNG
- Conditioning (`factor`) in concurrent contexts (complex, needs distributed MCMC?)
- Probabilistic effect tracking (which distributions a function may sample from)

### 5.2 Causal Inference and Concurrency

`causal` blocks and `CausalModel` values represent structural causal models (SCMs). Concurrency may be relevant for:

- **Parallel causal queries**: Different threads querying different interventions on the same causal model
- **Distributed data**: Causal inference across shards (data on different nodes)
- **Monte Carlo simulation**: Running many counterfactual simulations in parallel

**Example:**
```algol26
causal model := CausalModel.fromGraph(/* ... */);

async proc computeEffect(model: CausalModel, intervention: (var := value)) => real =
  begin
    var intervened := intervene(model, intervention);
    result := expectation(intervened, Y)  // average causal effect
  end;

begin
  var tasks: array [10] of future real;
  for i: int := 1 to 10 do
    tasks[i] := computeEffect(model, X := i);
  
  var effects: array [10] of real;
  for i: int := 1 to 10 do
    effects[i] := await tasks[i]
end
```

**Shared causal models:**
- `CausalModel` values could be immutable after construction, making them safe to share across threads
- If mutable (e.g., learning from data), use `sync` or lock around modifications

**MVP Implementation:**
- `causal` is stub; `CausalModel` is a dummy type
- `intervene` and `outcome` are no-ops returning dummy values
- No parallelism

**Deferred:**
- Actual causal inference algorithms
- Parallel causal effect estimation
- Distributed causal models (across network nodes)

### 5.3 Formal Verification (`verify`) and Concurrency

`verify` annotations attach specifications to functions. In concurrent code, specifications must reason about:

- **Thread safety**: "This function is thread-safe" or "requires exclusive access to `x`"
- **Locks**: Pre/post conditions about held locks
- **Ordering**: Happens-before relationships

**Example (future):**
```algol26
proc protectedIncrement(x: ref sync int)
  requires "lock(x.mutex) held"  // ghost condition
  ensures "x = old(x) + 1"
  =
  x := x + 1;
```

**MVP Implementation:**
- `verify` is ignored; specifications are not checked

**Deferred:**
- Integration with SMT solvers for concurrent program verification
- Ghost state for locks and permissions

---

## 6. MVP Scope: Week 2 Interpreter vs Deferred

### 6.1 What's Implemented in Week 2 Interpreter

The Week 2 interpreter is a **single-threaded, non-concurrent** runtime that parses and executes ALGOL 26 programs. Concurrency-related features are recognized at the lexical and syntactic levels but have **no real concurrent behavior**.

**Implemented (syntactic recognition only):**
- Keywords: `async`, `await`, `chan`, `spawn`, `thread` (as type?), `lock`, `sync`, `prob`, `causal`, `verify`
- Type names: `chan T`, `sync T`, `Distribution<T>`, `CausalModel`
- Statement forms: `await expr`, `chan send expr`, `chan recv`, `spawn proc`, `with lock do block`
- `prob` and `causal` blocks/declarations

**Runtime behavior (MVP semantics):**
- `async proc`: Returns a dummy future object; function body executes **synchronously** (no suspension)
- `await`: Immediately returns the expression's value (no blocking)
- `chan`: Creates a dummy object; `send` and `recv` are no-ops or return zero values
- `spawn`: Executes the procedure **synchronously** on the current thread; returns a dummy thread handle; `join` does nothing
- `lock`: `lock` type is a dummy; `with lock do` executes the block normally (no lock acquisition)
- `sync`: No effect; variables behave normally
- `prob`/`causal`/`verify`: Recognized but ignored; behave as normal types/statements

**Memory model:**
- Stack allocation only (strings and arrays are stack-allocated in MVP? Actually strings likely heap but no GC)
- No borrow checking; `ref` is pass-by-reference
- No GC (or simple stub)

### 6.2 What's Deferred to Post-MVP (Prioritized)

| Feature | Priority | Notes |
|---------|----------|-------|
| Basic async/await with suspension | P1 (high) | Need event loop, futures |
| Channels with blocking send/recv | P1 | Unbuffered and buffered |
| Thread pool (`spawn`) | P2 | OS threads or green threads |
| Borrow checking (compile-time) | P1 | Prevent data races |
| `sync` semantics (atomics/locks) | P2 | Thread-safe primitives |
| GC (mark-and-sweep) | P3 | For escaping heap objects |
| Thread-local RNG for `prob` | P2 | Concurrent sampling |
| `select` on multiple channels | P3 | Multiplexing |
| Actor model | P4 | Higher-level abstraction |
| Formal verification for concurrency | P4 | Integration with SMT |
| Distributed causal inference | P4 | Across network nodes |

**Post-MVP phases (tentative):**

- **Phase 1 (MVP+1)**: Implement async/await, channels, and basic thread pool. Still no borrow checking, but add `sync` atomics for primitives.
- **Phase 2 (Safety)**: Add compile-time borrow checking and lifetime analysis. Enforce `ref` rules. Introduce `sync` enforcement.
- **Phase 3 (Scalability)**: Add GC for heap-allocated objects. Optimize concurrency runtime (work stealing, etc.).
- **Phase 4 (AI Integration)**: Full `prob` and `causal` with concurrent sampling and parallel inference.

### 6.3 Why This Split?

The Week 2 interpreter focuses on **core language semantics** (expressions, statements, types, control flow) without the complexity of real concurrency. This allows:
- Testing the type system and grammar
- Writing nontrivial programs (e.g., the neural net demo)
- Validating syntax for concurrency features
- Deferring the hard parts (scheduling, locking, race detection) until the interpreter is stable

Concurrency is **critical for GenAI** but can be added in later weeks once the base language is solid.

---

## 7. Examples: Concurrent Programs

These examples illustrate the intended design of ALGOL 26's concurrency features. They **do not run** in the Week 2 interpreter (concurrency is stubbed), but they demonstrate the target syntax and semantics.

### 7.1 Producer-Consumer with Buffered Channel

A classic pattern where a producer generates data and a consumer processes it, with a bounded buffer decoupling them.

```algol26
async proc producer(out: chan int, n: int) =>
  begin
    for i: int := 1 to n do
      begin
        println("Producing ", i);
        out send i;                    // may block if buffer full
        delay(0.1)                     // simulate work (future)
      end;
    out send -1                       // sentinel = end of stream
  end;

async proc consumer(in: chan int) =>
  begin
    var done: bool := false;
    while not done do
      begin
        var item: int := in recv;      // may block if buffer empty
        if item = -1 then
          done := true
        else
          begin
            println("Consumed ", item);
            // Process item...
          end
      end
  end;

begin
  var bufferSize: int := 5;
  var q: chan int := chan int(bufferSize);
  var p := producer(q, 20);
  var c := consumer(q);
  await p;                            // wait for producer to finish
  // Consumer will exit after receiving -1
  await c
end
```

**Key points:**
- `chan int(5)` creates a buffered channel with capacity 5
- `send` blocks when buffer is full; `recv` blocks when buffer empty
- `await` used to wait for async tasks to complete

**MVP behavior:** The program runs but `send`/`recv` are no-ops, and `await` returns immediately. No actual concurrency.

### 7.2 Parallel Map (Fork-Join)

Map a function over an array in parallel using a thread pool.

```algol26
proc square(x: int) => int = x * x;

async proc parallelMap(arr: array [N] of int, f: proc(int) => int) => array [N] of int =
  begin
    var results: array [N] of int;
    var tasks: array [N] of future int;
    
    // Spawn N tasks, one per element
    for i: int := 1 to N do
      tasks[i] := async_spawn( proc() => int = f(arr[i]) );
    
    // Collect results
    for i: int := 1 to N do
      results[i] := await tasks[i];
    
    result := results
  end;

begin
  var data: array [10] of int := [1,2,3,4,5,6,7,8,9,10];
  var squared: array [10] of int := await parallelMap(data, square);
  println(squared)
end
```

**Notes:**
- `async_spawn` (hypothetical) spawns an async task that runs in parallel
- `future int` is the type of a promise that will yield an `int`
- All tasks join automatically at the `await` loop

**Alternative with `spawn` threads:**
```algol26
proc worker(i: int, in: array [N] of int, out: array [N] of int, f: proc(int) => int) =
  out[i] := f(in[i]);

begin
  var data: array [10] of int := ...;
  var results: array [10] of int;
  var threads: array [10] of thread;
  
  for i: int := 1 to 10 do
    threads[i] := spawn worker(i, data, results, f);
  
  for i: int := 1 to 10 do
    threads[i] join;
  
  println(results)
end
```

**MVP behavior:** All tasks run sequentially on the main thread; `await` returns immediately.

### 7.3 Parallel Reduction with Locks

Compute the sum of an array using multiple threads with a shared accumulator protected by a lock.

```algol26
var total: sync int := 0;      // thread-safe integer
var totalLock: lock;           // explicit lock alternative

proc worker(start: int, end: int, arr: array [N] of int) =
  begin
    var localSum: int := 0;
    for i: int := start to end do
      localSum := localSum + arr[i];
    // Critical section
    with totalLock do
      total := total + localSum
  end;

begin
  var data: array [1000] of int := ...;
  var numWorkers: int := 4;
  var chunk: int := 1000 / numWorkers;
  var threads: array [4] of thread;
  
  for w: int := 1 to 4 do
    threads[w] := spawn worker((w-1)*chunk + 1, w*chunk, data);
  
  for w: int := 1 to 4 do
    threads[w] join;
  
  println("Sum = ", total)
end
```

**MVP behavior:** Lock does nothing; data race would occur in real concurrent execution. In MVP single-threaded, works correctly.

### 7.4 Concurrent Probabilistic Sampling

Sample from multiple distributions in parallel, then combine.

```algol26
prob x: Distribution<real> ~ Normal(0.0, 1.0);
prob y: Distribution<real> ~ Normal(0.0, 1.0);

async proc sampleBatch(n: int) => array [n] of real =
  begin
    var batch: array [n] of real;
    for i: int := 1 to n do
      batch[i] := sample(x) + sample(y);  // independent samples from thread-local RNG
    result := batch
  end;

begin
  var batches: array [4] of future array [1000] of real;
  for i: int := 1 to 4 do
    batches[i] := sampleBatch(1000);
  
  // Combine all samples
  var allSamples: array [4000] of real;
  var idx: int := 1;
  for i: int := 1 to 4 do
    begin
      var batch := await batches[i];
      // copy batch into allSamples starting at idx
      idx := idx + 1000
    end;
  
  // Compute statistics on allSamples...
end
```

**MVP behavior:** `sample(x)` returns deterministic (e.g., 0.0); no parallelism.

---

## 8. Summary and Design Rationale

ALGOL 26's concurrency model is designed to meet the needs of AI/AGI systems while maintaining safety and clarity:

1. **Async/await** for I/O-bound async operations (network, disk) with cooperative scheduling.
2. **Channels** for message-passing concurrency (Go-style), avoiding shared state where possible.
3. **Threads (`spawn`)** for CPU-bound parallelism when needed.
4. **Ownership and borrowing** to statically prevent data races (compile-time guarantee).
5. **`sync` and locks** as fallbacks for complex shared state patterns.
6. **Integration with `prob` and `causal`** to support concurrent probabilistic inference and causal effect estimation.
7. **Determinism** where possible for reproducibility of AI experiments.
8. **MVP strategy**: Recognize concurrency syntax but run sequentially, adding real parallelism incrementally with safety checks.

This model balances **performance** (parallelism), **safety** (no data races), and **expressiveness** (multiple concurrency paradigms). It also aligns with ALGOL 26's goal of being a language for AGI: concurrent, probabilistic, causal, and verifiable.

---

**Next Steps:**
- Implement Week 2 interpreter with stub concurrency
- Write test programs that exercise the syntax (even if not truly concurrent)
- Design the async runtime and thread pool for post-MVP
- Explore integrating lightweight actor model as a library on top of channels

---

**End of Concurrency Specification**
