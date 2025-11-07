# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import random
import threading
from collections.abc import Callable

from ft_utils.benchmark_utils import BenchmarkProvider, execute_benchmarks
from ft_utils.local import BatchExecutor, LocalWrapper
from ft_utils.synchronization import IntervalLock, RWLock, RWWriteContext


class RandomBenchmarkProvider(BenchmarkProvider):
    def __init__(self, operations: int) -> None:
        self._operations = operations
        self._ilock = IntervalLock()
        self._lock = threading.Lock()
        self._rwlock = RWLock()
        self._batch_executor = BatchExecutor(lambda: random.randint(1, 100), 10000)

    def benchmark_random_direct(self) -> None:
        rr = LocalWrapper(random.randint)
        for _ in range(self._operations):
            _ = rr(1, 100)

    def benchmark_interval_locked(self) -> None:
        rr = LocalWrapper(random.randint)
        poll = LocalWrapper(self._ilock.poll)
        with self._ilock:
            for _ in range(self._operations):
                _ = rr(1, 100)
                poll()

    def benchmark_batch_executor(self) -> None:
        be = LocalWrapper(self._batch_executor.load)
        for _ in range(self._operations):
            _ = be()

    def benchmark_simple_locked(self) -> None:
        rr = LocalWrapper(random.randint)
        with self._lock:
            for _ in range(self._operations):
                _ = rr(1, 100)

    def benchmark_rw_locked(self) -> None:
        rr = LocalWrapper(random.randint)
        with RWWriteContext(self._rwlock):
            for _ in range(self._operations):
                _ = rr(1, 100)


def invoke_main() -> None:
    execute_benchmarks(RandomBenchmarkProvider)


if __name__ == "__main__":
    invoke_main()
