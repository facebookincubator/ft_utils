---
oncalls: ['python_runtime']
---

# ft_utils — Build System & Tests

## Buck2 (fbcode)

```bash
# Build all C extensions
buck2 build fbcode//ft_utils:local
buck2 build fbcode//ft_utils:synchronization
buck2 build fbcode//ft_utils:_concurrency
buck2 build fbcode//ft_utils:_weave

# Build Python libraries
buck2 build fbcode//ft_utils:concurrency    # concurrency.py + _concurrency + local
buck2 build fbcode//ft_utils:weave          # weave.py + _weave
buck2 build fbcode//ft_utils:ft_utils       # everything

# Run tests (regular Python)
buck2 test fbcode//ft_utils:test_ft_utils_concurrency
buck2 test fbcode//ft_utils:test_ft_utils_localwrapper
buck2 test fbcode//ft_utils:test_ft_utils_weave
buck2 test fbcode//ft_utils:test_ft_utils_batchexecutor
buck2 test fbcode//ft_utils:test_ft_utils_intervallock
buck2 test fbcode//ft_utils:test_ft_utils_rwlock
buck2 test fbcode//ft_utils:test_ft_utils_weakref_to
buck2 test fbcode//ft_utils:test_ft_utils_compat
buck2 test fbcode//ft_utils:test_ft_utils_issues
buck2 test fbcode//ft_utils:test_ft_utils_benchmark_utils

# Run tests (free-threading Python 3.14t) — prefix with ft_
buck2 test fbcode//ft_utils:ft_test_ft_utils_concurrency
buck2 test fbcode//ft_utils:ft_test_ft_utils_localwrapper
buck2 test fbcode//ft_utils:ft_test_ft_utils_weave
buck2 test fbcode//ft_utils:ft_test_ft_utils_batchexecutor
buck2 test fbcode//ft_utils:ft_test_ft_utils_intervallock
buck2 test fbcode//ft_utils:ft_test_ft_utils_rwlock
buck2 test fbcode//ft_utils:ft_test_ft_utils_weakref_to
buck2 test fbcode//ft_utils:ft_test_ft_utils_compat
buck2 test fbcode//ft_utils:ft_test_ft_utils_issues

# Benchmarks (regular / free-threading with ft_ prefix)
buck2 run fbcode//ft_utils:atomic_bench
buck2 run fbcode//ft_utils:concurrent_dict_bench
buck2 run fbcode//ft_utils:concurrent_queue_bench
buck2 run fbcode//ft_utils:lock_bench
buck2 run fbcode//ft_utils:merge_sort_bench
buck2 run fbcode//ft_utils:map_reduce_bench
# Also: array_bench, bytearray_bench, list_bench, slots_bench, tsp_bench, concurrent_deque_bench
# Free-threading variants: prefix with ft_ (e.g. ft_atomic_bench)
```

## setuptools (open source)

```bash
python -P setup.py bdist_wheel     # Build wheel
python -m pip install dist/*.whl   # Install
python -m ft_utils.tests.test_run_all  # Run all tests
```

## Test Naming Convention

Every test target has two variants:
- `test_ft_utils_<name>` — regular GIL Python
- `ft_test_ft_utils_<name>` — free-threading Python (`py_version = "3.14.free-threading"`)

Same for benchmarks: `<name>_bench` (regular) and `ft_<name>_bench` (free-threading).

## Test Coverage

| Test file | What it covers |
|-----------|---------------|
| `tests/test_concurrency.py` | ConcurrentDict, AtomicInt64, AtomicReference, ConcurrentDeque, ConcurrentQueue, StdConcurrentQueue, ConcurrentGatheringIterator, AtomicFlag |
| `tests/test_localwrapper.py` | LocalWrapper proxy behavior |
| `tests/test_batchexecutor.py` | BatchExecutor creation and loading |
| `tests/test_intervallock.py` | IntervalLock lock/unlock/poll/cede |
| `tests/test_rwlock.py` | RWLock read/write locking |
| `tests/test_weave.py` | Native destructor registration (uses `_test_weave.c` helper) |
| `tests/test_weakref_to.py` | Weak reference behavior with concurrent types |
| `tests/test_compat.py` | ft_compat.h backward compatibility (uses `_test_compat.c` helper) |
| `tests/test_issues.py` | Regression tests for reported issues |
| `tests/test_benchmark_utils.py` | Benchmark utility functions |
| `tests/test_run_all.py` | Meta-test that runs all tests |
