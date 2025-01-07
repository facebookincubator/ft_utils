# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

from collections import deque
from typing import Deque

from ft_utils.benchmark_utils import BenchmarkProvider, execute_benchmarks
from ft_utils.concurrent import ConcurrentDeque
from ft_utils.local import LocalWrapper


class ConcurretDequeBenchmarkProvider(BenchmarkProvider):
    def __init__(self, operations: int) -> None:
        self._operations = operations
        self._standard: Deque[int] | None = None
        self._concurrent: ConcurrentDeque[int] | None = None

    def set_up(self) -> None:
        self._standard = deque[int]()
        self._concurrent = ConcurrentDeque[int]()

    def benchmark_standard(self) -> None:
        _deque = LocalWrapper(self._standard)

        for n in range(self._operations):
            _deque.append(n)
            _deque.appendleft(n)

        for _ in range(self._operations):
            _deque.pop()
            _deque.popleft()

    def benchmark_concurrent(self) -> None:
        _deque = LocalWrapper(self._concurrent)

        for n in range(self._operations):
            _deque.append(n)
            _deque.appendleft(n)

        for _ in range(self._operations):
            _deque.pop()
            _deque.popleft()

    def benchmark_standard_batch(self) -> None:
        _deque = LocalWrapper(self._standard)
        for n in range(self._operations // 100):
            for _ in range(100):
                _deque.append(n)
                _deque.appendleft(n)
            for _ in range(100):
                _deque.pop()
                _deque.popleft()

    def benchmark_concurrent_batch(self) -> None:
        _deque = LocalWrapper(self._concurrent)
        for n in range(self._operations // 100):
            for _ in range(100):
                _deque.append(n)
                _deque.appendleft(n)
            for _ in range(100):
                _deque.pop()
                _deque.popleft()


def invoke_main() -> None:
    execute_benchmarks(ConcurretDequeBenchmarkProvider)


if __name__ == "__main__":
    invoke_main()
