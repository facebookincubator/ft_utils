---
oncalls: ['python_runtime']
---

# ft_utils — Overview

ft_utils is a utility library for Free Threaded Python (no-GIL) providing thread-safe data structures, synchronization primitives, and performance helpers. Python + C11 extensions for high-performance concurrent programming on CPython 3.12+, with full free-threading support on 3.13t+/3.14t+.

- **License:** MIT (open source)
- **Oncall:** python_runtime
- **Languages:** Python (pyre-strict) + C11
- **Platforms:** Linux (x86_64, i686, aarch64), Windows (x86_64), macOS (ARM64)
- **Python versions:** 3.12, 3.13, 3.13t (free-threading), 3.14, 3.14t

## Architecture

Four Python modules backed by four C extensions:

```
ft_utils/
├── __init__.py              # Package root; ENABLE_EXPERIMENTAL flag
├── concurrency.py           # Python wrappers around _concurrency C extension
├── weave.py                 # Python wrappers around _weave C extension
├── _concurrency.pyi         # Type stubs for C extension
├── _weave.pyi               # Type stubs for C extension
├── local.pyi                # Type stubs for C extension
├── synchronization.pyi      # Type stubs for C extension
└── tests/                   # Unit tests + C test helpers
```

Native C code in `native/`:

```
native/
├── include/                 # Public headers (ft_compat.h, ft_refcount.h, ft_utils.h, ft_utime.h, ft_weave.h)
└── src/
    ├── _concurrency.c       # Module init for concurrent data structures
    ├── _weave.c             # Weave module
    ├── ft_core.c            # Shared core utilities
    ├── local.c              # LocalWrapper + BatchExecutor
    ├── synchronization.c    # IntervalLock + RWLock
    └── concurrent_data_structures/  # atomic_int64, atomic_reference, concurrent_deque, concurrent_dict
```

## Key Patterns

### LocalWrapper for Performance

The core optimization: wrap shared objects in `LocalWrapper` to avoid cross-thread refcount contention.

```python
from ft_utils.local import LocalWrapper
_dict = LocalWrapper(shared_dict)  # thread-local copy avoids contention
while condition:
    value = _dict[key]
```

Wrap any frequently-accessed shared object: dicts, functions, conditions, flags.

### IntervalLock for Long Computations

Use `IntervalLock.poll()` inside long-running critical sections to cooperatively yield:

```python
lock = IntervalLock()
with lock:
    for i in range(large_number):
        lock.poll()  # yields only if interval elapsed
        do_work()
```

### Experimental Features

Gated by `ft_utils.ENABLE_EXPERIMENTAL = True`. Must be set before first use. Currently only the weave module uses this.

### C Extension Conventions

- C11 standard. Cross-platform macros in `ft_utils.h` abstract pthreads vs Windows critical sections.
- `ft_compat.h` provides backward-compatible atomics for pre-3.13 Python.
- All modules declare `Py_mod_gil = Py_MOD_GIL_NOT_USED` on 3.13+ via `_PY_NOGIL_MODULE_SLOT`.

### Error Handling

- `ConcurrentQueue`/`StdConcurrentQueue` raise `queue.Empty` on timeout, `queue.ShutDown` on shutdown.
- `ConcurrentGatheringIterator` raises `RuntimeError("Iterator insertion failed")` on producer failure.
- Weave functions raise `RuntimeError` if experimental flag not set or Python version too old.

## File Index

| Path | Purpose |
|------|---------|
| `ft_utils/__init__.py` | Package init; `ENABLE_EXPERIMENTAL` flag |
| `ft_utils/concurrency.py` | AtomicFlag, ConcurrentGatheringIterator, ConcurrentQueue, StdConcurrentQueue |
| `ft_utils/weave.py` | Native destructor registration (experimental) |
| `ft_utils/_concurrency.pyi` | Type stubs: ConcurrentDict, ConcurrentDeque, AtomicInt64, AtomicReference |
| `ft_utils/_weave.pyi` | Type stubs: register/unregister_native_destructor |
| `ft_utils/local.pyi` | Type stubs: LocalWrapper, BatchExecutor |
| `ft_utils/synchronization.pyi` | Type stubs: IntervalLock, RWLock, RWReadContext, RWWriteContext |
| `native/src/local.c` | LocalWrapper + BatchExecutor C implementation |
| `native/src/synchronization.c` | IntervalLock + RWLock C implementation |
| `native/src/_concurrency.c` | Module init for concurrent data structures |
| `native/src/concurrent_data_structures/*.c` | Individual data structure implementations |
| `native/include/*.h` | Public C headers |
| `setup.py` | setuptools build config (6 C extensions) |
| `BUCK` | Buck2 build targets for fbcode |
| `examples/consistent_counter.py` | Demo: AtomicInt64 + IntervalLock |
| `examples/fibonacci.py` | Demo: ConcurrentDict + ConcurrentQueue + LocalWrapper |

## External Dependencies

- **glibc** (Linux): `pthread`, `rt` — required by all C extensions
- No other external dependencies. The library is self-contained.
