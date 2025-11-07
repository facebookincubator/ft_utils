# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import threading
from collections.abc import Callable

from ft_utils.benchmark_utils import BenchmarkProvider, execute_benchmarks
from ft_utils.local import LocalWrapper
from ft_utils.synchronization import IntervalLock, RWLock, RWWriteContext


class LockBenchmarkProvider(BenchmarkProvider):
    def __init__(self, operations: int) -> None:
        self._operations = operations
        self._lock = threading.Lock()
        self._rwlock = RWLock()

    def benchmark_simple_locked(self) -> None:
        _lock = LocalWrapper(self._lock)
        for _ in range(self._operations):
            with _lock:
                pass

    def benchmark_rw_locked(self) -> None:
        _cont = RWWriteContext(self._rwlock)
        for _ in range(self._operations):
            with _cont:
                pass


def invoke_main() -> None:
    execute_benchmarks(LockBenchmarkProvider)


if __name__ == "__main__":
    invoke_main()
