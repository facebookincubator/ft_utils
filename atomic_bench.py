# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import threading
from typing import Any, Optional

from ft_utils.benchmark_utils import BenchmarkProvider, execute_benchmarks, ft_randint
from ft_utils.concurrent import AtomicReference
from ft_utils.local import LocalWrapper


class LockedReference:
    def __init__(self, value: Optional[Any]) -> None:  # pyre-ignore[2]
        self._value = value
        self._lock = threading.Lock()

    def set(self, value: Any) -> None:  # pyre-ignore[2]
        with self._lock:
            self._value = value

    def get(self) -> Any:  # pyre-ignore[3]
        with self._lock:
            return self._value

    def exchange(self, value: Any) -> Any:  # pyre-ignore
        with self._lock:
            old_value = self._value
            self._value = value
            return old_value

    def compare_exchange(self, expected, value: Any) -> Any:  # pyre-ignore
        with self._lock:
            if self._value is not expected:
                return False
            self._value = value
            return True


class ReferenceBenchmarkProvider(BenchmarkProvider):
    def __init__(self, operations: int) -> None:
        self._operations = operations
        self._atomic_ref = AtomicReference(1)
        self._locked_ref = LockedReference(1)

    def benchmark_atomic_set(self) -> None:
        ref = LocalWrapper(self._atomic_ref)
        for i in range(self._operations):
            ref.set(i % 10)

    def benchmark_atomic_get(self) -> None:
        ref = LocalWrapper(self._atomic_ref)
        for _ in range(self._operations):
            _ = ref.get()

    def benchmark_atomic_exchange(self) -> None:
        ref = LocalWrapper(self._atomic_ref)
        for i in range(self._operations):
            _ = ref.exchange(i % 10)

    def benchmark_atomic_cas(self) -> None:
        ref = LocalWrapper(self._atomic_ref)
        for i in range(self._operations):
            _ = ref.compare_exchange(i % 2, i % 2)

    def benchmark_atomic_mixed_operations(self) -> None:
        ref = LocalWrapper(self._atomic_ref)
        for i in range(self._operations):
            if i % 2:
                ref.set(i % 99)
            else:
                _ = ref.get()

    def benchmark_locked_set(self) -> None:
        ref = LocalWrapper(self._locked_ref)
        for i in range(self._operations):
            ref.set(i % 10)

    def benchmark_locked_get(self) -> None:
        ref = LocalWrapper(self._locked_ref)
        for _ in range(self._operations):
            _ = ref.get()

    def benchmark_locked_exchange(self) -> None:
        ref = LocalWrapper(self._locked_ref)
        for i in range(self._operations):
            _ = ref.exchange(i % 10)

    def benchmark_locked_cas(self) -> None:
        ref = LocalWrapper(self._locked_ref)
        for i in range(self._operations):
            _ = ref.compare_exchange(i % 2, i % 2)

    def benchmark_locked_mixed_operations(self) -> None:
        ref = LocalWrapper(self._locked_ref)
        for i in range(self._operations):
            if i % 2:
                ref.set(i % 99)
            else:
                _ = ref.get()


def invoke_main() -> None:
    execute_benchmarks(ReferenceBenchmarkProvider)


if __name__ == "__main__":
    invoke_main()
