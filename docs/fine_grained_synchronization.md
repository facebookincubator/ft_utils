![Image](https://github.com/user-attachments/assets/f4ef78b9-8cc0-4264-971f-d6ac76884f3a)
# Fine-Grained Parallelism with Free-Threaded Python and ft_utils

## Legacy Python, the GIL, and Structural Limitations
The Global Interpreter Lock (GIL) in CPython has long been a pragmatic compromise. It protects memory management internals from concurrent access at the cost of serializing all Python bytecode execution. This single lock simplifies reference counting and garbage collection, but it has made true multi-core CPU utilization within one process impossible.

Even in C extensions, while `Py_BEGIN_ALLOW_THREADS` enables the GIL to be dropped, any interaction with Python objects—reference counts, attribute access, even `isinstance` checks—requires reacquiring it. This fragments performance and forces programmers into a mental model where concurrent control and Python data manipulation are mutually exclusive.

The GIL also has non-obvious side effects:
* Priority inversion: high-priority threads can be blocked by low-priority threads simply because the GIL is a FIFO queue without priority awareness.
* Opaque scheduling: thread scheduling is left to the OS, but Python threads can't influence priority, affinity, or yield behavior.

The result is that GIL-based Python gives the appearance of concurrency while hiding deep systemic serialization. Most high-performance developers route around it—via multiprocessing, C++, or GPU offload—each with its own overhead and disconnect from Python ergonomics.

## Free-Threaded Python (FTP): Removing the GIL
FTP (introduced experimentally in CPython 3.13 and maturing in 3.14) removes the GIL and introduces per-object locking semantics to enable real concurrency.

### Key concepts
* Interpreter isolation is gone; threads run Python bytecode concurrently.
* CPython internal APIs are being progressively made thread-safe.
* Developers are now responsible for managing thread safety when manipulating shared objects.

Rather than reintroduce coarse locks, the FTP model shifts toward critical sections, atomic operations, and lock elision strategies. This opens the door for performance models much closer to what C++ and Rust developers expect.

## ft_utils: Fine-Grained Control for the Free-Threaded World
ft_utils, provides infrastructure for working with FTP in production contexts. It includes:
* Atomic primitives: `AtomicInt64`, `AtomicReference` and `AtomicFlag`
* Thread-local state and CPU affinity utilitie at a native level.
* High performance, scalable, thread-safe Python data structures like ConcurrentDict.

This is not abstraction for abstraction’s sake but tools to allow scalable development with exact, fine grained and easy to use control over thread based parallel execution architectures.

### AtomicInt64 and AtomicReference
`AtomicInt64` provides lock-free atomic manipulation of integer state:
```python
from ft_utils import AtomicInt64
counter = AtomicInt64(0)
# Multiple threads can safely increment:
counter.fetch_add(1)
# Or using arithmetic operators
counter += 1
```
In the absence of the GIL, this matters: naive `+= 1` on an `int` is now unsafe without explicit synchronization.

`AtomicReference` generalizes this to object references. It enables low-level constructs like lock-free queues, hazard pointers, or generational GC barriers, depending on your architecture.

`AtomicFlag` is a bool abstraction over AtomicInt64.

These atomic ops are implemented in C using platform-native intrinsics, giving predictable, memory-fenced semantics consistent with modern concurrent programming.

## CPython New Features
### Atomics
Access to many atomic native operations (for example _Py_atomic_add_uint64_t) have been added to the CPython API.
ft_utils provides ft_compat.h which backports these to previous versions of CPython to make cross version coding easier.

### Critical Sections: Per-Object Locking
Critical sections in FTP are explicit per-object locks that allow serial access to shared state. In Cython:
```cython
with cython.critical_section(myobj):
    # Safe access
```
Under the hood, each Python object now carries an optional lock. This unlocks fine-grained synchronization models—reader-writer patterns, lock striping, and even lock-free algorithms with fallback pessimism.

Unlike `threading.Lock`, critical sections are:
* Object-scoped, not manually created.
* Implicitly tied to Python object identity.
* Used by the CPython interpreter itself to manage mutation safely in FTP mode.


### Critical Sections vs Mutexes in Free-Threaded Python
#### Overview

Critical sections and mutexes both provide mutual exclusion to protect shared resources from concurrent access. However, they differ in scope, granularity, performance, and implementation strategy, particularly in the context of Free-Threaded Python (FTP).

#### Conceptual Difference

* Mutex (Mutual Exclusion Object)

  - A general-purpose locking mechanism.
  - Can be named, recursive, or shared across processes.
  - Typically manually managed by the programmer.
  - Exists independently of the resource it protects.

* Critical Section (in FTP)

  - A Python object-specific lock introduced to replace the GIL for finer-grained locking.
  - Tied to a specific object’s internal lock state, not a global or external lock.
  - Automatically integrated with Python object semantics and lifecycle.
  - Encourages object-local concurrency control, like "this object's state is now exclusively accessed."

#### Scope and Granularity

* Mutex

  - May be global or scoped to a module or subsystem.
  - You can protect multiple resources with one mutex, which increases the risk of deadlocks.

* Critical Section

  - Operates at the level of individual Python objects.
  - Promotes fine-grained locking, reducing contention and making parallelism more scalable.

#### Performance

* Critical sections in FTP are optimized for fast entry/exit when there's no contention, often using lock-free or wait-free paths.
* Mutexes, depending on implementation (e.g., POSIX threads), may be heavier-weight and may involve kernel-level scheduling and context switches under contention.

#### Integration with Python Semantics

* Critical sections are part of the object model in FTP.
* For example, Cython’s `with cython.critical_section(obj)` locks `obj`’s critical section lock.
* The CPython interpreter itself uses critical sections to protect access to object internals when the GIL is disabled.
* Mutexes, unless wrapped via a Python extension, are external to Python's object model.

#### Example Comparison

* Using a Critical Section (Cython or FTP-aware extension)

```cython
with cython.critical_section(my_object):
    my_object.value += 1 # safe from race conditions
```

The below is from the batch executor source code in ft_utils where a critical sections protects the refilling of the buffer. Note how the critical section
protects the execution on a per-object basis compare to a mutex which would just be one a code block basis.
```c
    Py_BEGIN_CRITICAL_SECTION(self);
    index = _Py_atomic_load_ssize(&(self->index));
    if (index < size) {
      err = 0;
    } else {
      err = BatchExecutorObject_fill_buffer(self);
    }
    Py_END_CRITICAL_SECTION();
```

*  Using a Mutex (manual threading.Lock)

```python
lock = threading.Lock()
with lock:
    my_object.value += 1 # safe, but scope and ownership are not enforced
```

#### Design Philosophy

* Critical sections represent a language- and VM-integrated concurrency mechanism, specific to Python’s Free-Threaded execution model.
* Mutexes are a more generic, lower-level abstraction, often shared across many languages and platforms.

#### Summary Table

| Feature | Mutex | Critical Section (FTP) |
| --- | --- | --- |
| Scope | Arbitrary | Tied to Python objects |
| Performance | OS/kernel-level (slower) | Fast user-space, object-specific |
| Python Awareness | No | Yes |
| Deadlock Risk | Higher | Lower (if per-object) |
| Use Case | Manual general locking | Fine-grained Python object protection |
| Default in FTP | No | Yes |

## Understanding The GIL

### The GIL Is Not Thread Safe!

The Global Interpreter Lock (GIL) is a mechanism used in CPython, the standard implementation of the Python programming language, to synchronize access to Python objects, preventing multiple native threads from executing Python bytecodes at once. This lock is necessary primarily because CPython's memory management is not thread-safe.

Thread safety refers to the ability of a program or a piece of code to behave correctly when accessed by multiple threads. Achieving thread safety is crucial in multithreaded environments where threads share the same memory space and resources. The challenges in ensuring thread safety include preventing race conditions, deadlocks, and other concurrency-related issues.

The GIL impacts the execution of threads in Python by allowing only one thread to execute Python bytecodes at a time. This means that for CPU-bound threads (those that spend most of their time performing computations), the GIL can significantly limit the benefits of multithreading because it effectively serializes the execution of these threads. However, for I/O-bound threads (those that spend most of their time waiting on I/O operations like reading from a file or network), the GIL is released during the I/O operation, allowing other threads to run.

Despite its role in simplifying certain aspects of Python's threading implementation, the GIL does not make Python code thread-safe. The GIL is released during certain operations like I/O, and even when it is held, operations that appear atomic can still be interrupted. For example, incrementing a counter (`x += 1`) is not atomic; it involves reading the current value, incrementing it, and writing it back; that might then also cause code to run due to properties and all this might change as code evolves. If multiple threads are doing this concurrently, the GIL might be released between these steps, or the thread might be interrupted, leading to a race condition.

Here's an example that demonstrates how the GIL does not prevent race conditions:

```python
import threading

class Counter:
    """Contains a reference to a counted value"""
    def __init__(self) -> None:
        self._counted = 0

    @property
    def counted(self) -> int:
        return self._counted

    @counted.setter
    def counted(self, value: int) -> None:
        self._counted = value

def increment_counter(counter: Counter, num_times: int, barrier: threading.Barrier) -> None:
    """Increments the counter 'num_times' times after waiting on the barrier."""
    barrier.wait()
    for _ in range(num_times):
        counter.counted += 1

def main() -> None:
    """Runs multiple threads to increment a counter and checks for correctness."""

    num_threads = 10
    num_increments = 50000
    iterations = 0
    while True:
        counter = Counter()
        barrier = threading.Barrier(num_threads)

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=increment_counter, args=(counter, num_increments, barrier))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        expected = num_threads * num_increments
        print(f"{iterations}-> Expected: {expected} Actual: {counter.counted}", flush=True)
        if counter.counted != expected:
            return
        iterations += 1

if __name__ == "__main__":
    main()
```

Running this code, you'll likely find that the actual count is less than the expected count due to the race condition in incrementing the counter. Different values for `num_increments` may or may not trigger this behaviour. Similarly, running the code on different machines may impact results. So, code might work as though it is thread safe with the GIL but in relality there is no guarantee; code which works today might suddenly break tomorrow.

To achieve thread safety in Python, developers must use synchronization primitives like locks (`threading.Lock`), queues (`queue.Queue`), or other concurrency control mechanisms. For example, using a lock to protect the counter increment operation:

```python
import threading

class Counter:
    """Contains a reference to a counted value"""
    def __init__(self) -> None:
        self._counted = 0

    @property
    def counted(self) -> int:
        return self._counted

    @counted.setter
    def counted(self, value: int) -> None:
        self._counted = value

def increment_counter(counter: Counter, num_times: int, barrier: threading.Barrier, lock: threading.Lock) -> None:
    """Increments the counter 'num_times' times after waiting on the barrier."""
    barrier.wait()
    for _ in range(num_times):
        # Putting the lock around the entire loop is more efficient.
        # Putting it here is a clearer demonstration of the concept.
        with lock:
            counter.counted += 1

def main() -> None:
    """Runs multiple threads to increment a counter and checks for correctness."""

    num_threads = 10
    num_increments = 50000
    iterations = 0
    lock = threading.Lock()
    while True:
        counter = Counter()
        barrier = threading.Barrier(num_threads)

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=increment_counter, args=(counter, num_increments, barrier, lock))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        expected = num_threads * num_increments
        print(f"{iterations}-> Expected: {expected} Actual: {counter.counted}", flush=True)
        if counter.counted != expected:
            return
        iterations += 1

if __name__ == "__main__":
    main()
```

This version of the code ensures that the counter is incremented correctly, even with multiple threads.

SO, while the GIL simplifies certain aspects of Python's threading by preventing multiple threads from executing Python bytecodes simultaneously, it does not make Python code inherently thread-safe. Developers must still use proper synchronisation techniques to protect shared resources and prevent concurrency-related issues.

### Impact Of Removing The GIL
Logically, none. Any Python code which is _actually_ thread safe with GIL based Python will still be thread safe with FTPython. However, there my be code which appears to work (as you don't notice the race conditions) but is not actually thread safe which will fail _more often_ with free threading. In this case one could argue the GIL is a risk as it hides race conditions which can then bite developers when they least expect it.

## Legacy Python (with the GIL) and Priority Inversion

### What Happens with Thread Priorities and the GIL

In CPython prior to Python 3.13, the Global Interpreter Lock (GIL) is the central mechanism ensuring only one thread runs Python bytecode at a time. Thread scheduling is delegated to the OS, but the GIL adds an interpreter-level override: only one thread may execute Python bytecode at any time.

The GIL is released periodically based on:
* A time slice (`gil_drop_request`) usually every 5 ms.
* Blocking I/O or `time.sleep()`.

The next thread to acquire the GIL is essentially chosen by the OS, but not based on Python-level priority because:
* Python threads do not expose priority control in the standard threading API.
* The GIL implementation is agnostic to thread priority.
* The GIL uses a simple condition-variable and mutex system, without a priority-aware queue.

### Result: Priority Inversion

A high-priority thread (e.g., real-time audio or control loop) can be blocked by lower-priority threads that happen to acquire the GIL. Worse, if those lower-priority threads are preempted or starved by the OS scheduler, they may hold the GIL but not make progress, delaying everyone.

This is classical priority inversion: a low-priority thread prevents a high-priority one from proceeding due to locking mechanics.

### No Python-Level Control

Python does not allow user-level control over GIL scheduling, including:
* No setting of per-thread priorities (`threading.Thread` has no priority API).
* No access to GIL internals.
* No advisory or cooperative yield mechanisms based on urgency.

There are no hooks to influence which thread gets the GIL next, beyond blocking in native code or using `time.sleep()` as a crude yield.

### Implications for Real-Time or Low-Latency Systems

In GIL-locked Python:
* Real-time guarantees are impossible.
* CPU-bound threads fight for the GIL without regard to criticality.
* Workarounds like multiprocessing, ctypes, or Cython nogil are needed to isolate timing-critical tasks.

### Priority Inversion and GIL Pathology
A practical illustration: imagine a 'golden' thread feeding tensors to the GPU. It's on the critical path for inference latency. Meanwhile, a logger thread is periodically flushing buffered output.

With the GIL:
* The logger can acquire the GIL and block the inference thread.
* There's no priority system; scheduling is FIFO at best, starvation at worst.

In FTP:
* The tensor preparation thread can run concurrently.
* Only shared object access needs synchronization and often that can be atomic.
* If contention occurs, you can design around it—with priority-aware locking, yield policies, or lock-free structures.

This is not just an academic benefit. It’s how you make Python viable in systems with mixed criticality.

## Free-Threaded Python Fixes Priority Inversion

In Free Threaded Python (FTP):
* The GIL is optional and removable.
* Critical sections or atomic primitives give fine-grained control over shared state.
* You can use OS-level threads and assign real priorities, scheduler classes, or CPU affinities using `pthread`, `sched_setaffinity()`, etc.
* If you use `ft_utils` or similar, you can implement lock hierarchies or priority inheritance mechanisms yourself.

This makes FTP viable for:
* High-performance parallel apps.
* Soft real-time systems.
* Systems with heterogeneous workloads (e.g., background logging + critical control).

## Multiprocessing vs Fine-Grained Concurrency

### Why multiprocessing Isn't Fine-Grained
Python’s `multiprocessing` module sidesteps the GIL via process isolation:
* Each process has its own interpreter and memory space.
* Data must be serialized and passed across IPC channels.

While good for CPU-bound parallelism, it is unsuitable for fine-grained control because:
* No shared memory for Python objects.
* High latency coordination.
* No per-object synchronization.

If you want to build concurrent in-memory data structures, `multiprocessing` doesn’t help.

### What Multiprocessing is Good For

* Parallel execution across multiple CPU cores.
* Bypassing the GIL, since each process has its own Python interpreter and memory space.
* Running independent tasks in parallel, e.g. data loading, simulations, or batch inference.

### Why Multiprocessing Is Not Fine-Grained Concurrency

1. **Heavyweight Process Model**
   * Each Python process is fully independent.
   * Spawning a process is expensive (in time and memory).
   * Inter-process communication (IPC) is slower than shared memory due to serialization (pickle) and OS overhead.

2. **No Shared Python Objects**
   * Unlike threads, processes do not share memory.
   * Each process has its own copy of objects unless explicitly shared using `multiprocessing.Manager`, `Queue`, `Pipe`, or `SharedMemory`.

3. **Synchronization Is Limited and Coarse**
   * Locks, Semaphores, Events: These are available in multiprocessing, but they operate via OS primitives, not per-object fine-grained locking.
   * `SharedMemory` (3.8+) allows faster shared access for numpy arrays or raw bytes, but requires manual memory layout and synchronization.
   * You cannot protect arbitrary Python data structures with a mutex between processes—they’re in different address spaces.

### Available Tools in Multiprocessing for Coordination

| Tool Type | Granularity | Notes |
| --- | --- | --- |
| Lock, Semaphore | Coarse | OS-based; useful for shared counters or critical sections |
| Queue, Pipe | Coarse | Good for message passing; serialization adds latency |
| Manager.Value/List | Very coarse | Slower, proxied objects using a background server thread |
| shared_memory | Byte-level | Requires manual synchronization, useful for arrays |

`multiprocessing` offers concurrency tools, but not fine-grained concurrency as you’d find in threading or other utilities. It excels at task-level parallelism across CPUs. It lacks low-latency, lock-free primitives and is not designed for concurrent manipulation of shared Python objects.

### Combining Multiprocessing with Fine-Grained Tools

If you must have shared state with fine-grained control, you can either:
* Offload that state management to a shared C/C++ backend using memory-mapped files or ctypes.
* Use Free Threaded Python to regain shared memory and per-object locking.

## Native Code + Threads in Legacy Python (GIL-enabled)

### How it Works

Native C/C++ extensions can release the GIL using `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS`. This allows true parallel execution but only for code that does not touch Python objects.

### When it Fails

The moment a native thread needs to:
- Read or write a Python object (like a list, dict, NumPy array, etc.)
- Call back into Python
- Interact with reference counts or exceptions

it must re-acquire the GIL. This serializes the execution.

### Why This Is Not Fine-Grained Parallelism

| Aspect | Limitation |
| --- | --- |
| **Granularity** | Cannot safely manipulate Python data structures without taking the GIL. So most real-world work is GIL-bound. |
| **Interleaving** | No interleaving of native + Python logic per-thread without GIL churn. |
| **Scalability** | Parallel work is only scalable if it’s fully outside Python (e.g., pure math, IO, or C++ workloads). |
| **Memory Access** | Python’s memory model is not thread-safe without the GIL. You can’t update Python containers from two native threads safely. |
| **Design Overhead** | You need to segment your application logic into “GIL-free” vs “GIL-held” regions. That’s brittle and complex. |

While native threads in legacy Python allow some parallelism, they are not a general-purpose, fine-grained model for concurrency. It’s more like a bolt-on escape hatch for specific use cases (e.g., I/O libraries, compute-heavy extensions).

### Cython nogil is exactly the same thing
Cython supports `nogil` blocks, which are often suggested as a parallelism workaround:
```cython
cdef void do_work() nogil:
    # C code only
```
However:
* Any call to CPython internals requires reacquiring the GIL.
* The model is coarse—there’s no atomic reference support or per-object locks.
* Code must be fully C-safe. No `dict`, `list`, `set`, or native Python object manipulation is possible.

This makes it useful for compute kernels, not general Python concurrency.

## Closing Thoughts
Most concurrency libraries try to protect you. FTPython with ft_utils does something different; it gives you the control you need to design for correctness, rather than depending on global serialization as a crutch. Not only that, it makes key things easy to get right and provides library support of scalability and inter-thread communication. For example, lower level languages like C will crash if something is not thread say, FTPython will not crash, it might give an unexpected result but it keeps on trucking. When you hit issues ft_utils can provide more sophisticated synchronisation like readers/write locks, atomics and ConcurrentDict to tidy up thread correctness without a big performance hit.

Until now, Python has never been suitable for finely tuned concurrent systems. With FTP and ft_utils, that changes. You get the primitives—now you decide how to build with them.

If you're working on systems where performance, determinism, or mixed-criticality scheduling matter, this is finally a Python that respects your intent.
