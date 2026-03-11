---
oncalls: ['cinder']
---

# ft_utils — API Reference

## `ft_utils.concurrency` — Concurrent Data Structures

**Import:** `from ft_utils.concurrency import ...`
**Buck target:** `//ft_utils:concurrency`

### C Extension Types (from `ft_utils._concurrency`)

**`ConcurrentDict[K, V]`** — Thread-safe dictionary with sharded locking.
- `__init__(initial_capacity: int | None = None)` — `initial_capacity` sets parallelism/shard count
- Supports: `__contains__`, `__setitem__`, `__getitem__`, `__delitem__`, `__len__`, `__iter__`
- Methods: `as_dict()`, `clear()`, `get(key, default)`, `update(other)`, `keys()`, `values()`, `items()`

**`AtomicInt64`** — Lock-free atomic 64-bit integer.
- `__init__(value: int = 0)`
- `set(value)`, `get() -> int`
- `incr() -> int` (returns value before increment), `decr() -> int`
- Full arithmetic operators: `+`, `-`, `*`, `//`, `|`, `&`, `^`, `~`, with in-place variants (`+=`, etc.)
- Comparison operators, `__bool__`, `__int__`

**`AtomicReference[V]`** — Lock-free atomic reference to a Python object.
- `__init__(value: V | None = None)`
- `set(value)`, `get() -> V | None`
- `exchange(value) -> V | None` — atomically swap, returns old value
- `compare_exchange(expected, value) -> bool` — CAS operation

**`ConcurrentDeque[E]`** — Thread-safe double-ended queue.
- `__init__(iterable: Sequence[E] | None = None)`
- `append(value)`, `appendleft(value)`, `pop()`, `popleft()`
- `extend(iterable)`, `extendleft(iterable)`
- `remove(value)`, `rotate(n=1)`, `clear()`, `contains(value)`
- Supports: `__getitem__`, `__iter__`, `__len__`, `__contains__`, comparison operators

### Python Types

**`AtomicFlag`** — Boolean flag backed by AtomicInt64.
- `__init__(value: bool)`, `set(value: bool)`, `__bool__() -> bool`

**`ConcurrentGatheringIterator`** — Collects values from multiple producer threads, yields in key order.
- `__init__(scaling: int | None = None)`
- `insert(key: int, value: object)` — thread-safe insert by integer key
- `iterator(max_key: int, clear: bool = True) -> Iterator[object]` — blocks until next key available
- `iterator_local(max_key, clear) -> Iterator[object]` — yields LocalWrapper-wrapped values

**`ConcurrentQueue`** — Thread-safe FIFO queue with optional lock-free mode.
- `__init__(scaling: int | None = None, lock_free: bool = False)`
- `push(value)`, `pop(timeout: float | None = None) -> object`
- `pop_local(timeout) -> LocalWrapper`
- `size() -> int`, `empty() -> bool`
- `shutdown(immediate: bool = False)`

**`StdConcurrentQueue`** — Drop-in replacement for `queue.Queue`, lock-free internally.
- `__init__(maxsize: int = 0)`
- `put(item, block=True, timeout=None)`, `get(block=True, timeout=None)`
- `put_nowait(item)`, `get_nowait()`
- `qsize()`, `full()`, `empty()`, `task_done()`, `join()`, `shutdown(immediate=False)`

## `ft_utils.local` — Thread-Local Performance Helpers

**Import:** `from ft_utils.local import LocalWrapper, BatchExecutor`
**Buck target:** `//ft_utils:local`

**`LocalWrapper`** — Transparent proxy creating thread-local copies, eliminating refcount contention. Supports all Python dunder methods.
- `__init__(wrapped: Any)`
- `get_wrapped() -> Any`, `set_wrapped(value)`, `del_wrapped()`

**`BatchExecutor`** — Creates batches of objects in a single thread, distributes as LocalWrappers.
- `__init__(source: Callable[[], Any], size: int)`
- `load() -> Any`, `as_local() -> LocalWrapper`

**Module functions:** `get_local_wrapper(wrapped)`, `release_local_wrapper(wrapper)`

## `ft_utils.synchronization` — Lock Primitives

**Import:** `from ft_utils.synchronization import IntervalLock, RWLock, RWReadContext, RWWriteContext`
**Buck target:** `//ft_utils:synchronization`

**`IntervalLock`** — Lock with cooperative mid-computation yielding.
- `__init__(interval: float = 0.005)` — interval in seconds
- `lock()`, `unlock()`, `locked() -> bool`
- `poll()` — yield lock briefly if interval elapsed
- `cede()` — unconditionally yield lock
- Context manager support

**`RWLock`** — Writer-prioritized reader-writer lock.
- `lock_read()`, `unlock_read()`, `lock_write()`, `unlock_write()`
- `readers() -> int`, `writers_waiting() -> int`, `writer_locked() -> bool`

**`RWReadContext`** / **`RWWriteContext`** — Context managers for RWLock.

## `ft_utils.weave` — Thread Management (Experimental)

**Import:** `from ft_utils.weave import register_native_destructor, unregister_native_destructor`
**Buck target:** `//ft_utils:weave`

Requires `ft_utils.ENABLE_EXPERIMENTAL = True` and Python >= 3.13.

- `register_native_destructor(var: int, destructor: int) -> None`
- `unregister_native_destructor(var: int) -> bool`
