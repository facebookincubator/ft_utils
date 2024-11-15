# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import os
import queue

from ft_utils.benchmark_utils import BenchmarkProvider, execute_benchmarks
from ft_utils.concurrent import ConcurrentQueue, StdConcurrentQueue
from ft_utils.local import LocalWrapper

ConcurrentQueue.put = ConcurrentQueue.push  # type: ignore
ConcurrentQueue.get = ConcurrentQueue.pop  # type: ignore


class ConcurretQueueBenchmarkProvider(BenchmarkProvider):
    def __init__(self, operations: int) -> None:
        self._operations = operations
        self._queue: ConcurrentQueue | None = None
        self._queue_lf: ConcurrentQueue | None = None
        self._queue_queue: queue.Queue | None = None  # type: ignore
        self._queue_std: StdConcurrentQueue | None = None  # type: ignore

    def set_up(self) -> None:
        self._queue = ConcurrentQueue(os.cpu_count())
        self._queue_lf = ConcurrentQueue(os.cpu_count(), lock_free=True)
        self._queue_queue = queue.Queue()
        self._queue_std = StdConcurrentQueue()

    def benchmark_locked(self) -> None:
        lw = LocalWrapper(self._queue)
        self._bm(lw)

    def benchmark_lock_free(self) -> None:
        lw = LocalWrapper(self._queue_lf)
        self._bm(lw)

    def benchmark_std(self) -> None:
        lw = LocalWrapper(self._queue_std)
        self._bm(lw)

    def benchmark_queue(self) -> None:
        lw = LocalWrapper(self._queue_queue)
        self._bm(lw)

    def _bm(self, lw) -> None:  # type: ignore
        for n in range(self._operations):
            lw.put(n)
            lw.get()

    def benchmark_locked_batch(self) -> None:
        lw = LocalWrapper(self._queue)
        self._bmb(lw)

    def benchmark_lock_free_batch(self) -> None:
        lw = LocalWrapper(self._queue_lf)
        self._bmb(lw)

    def benchmark_std_batch(self) -> None:
        lw = LocalWrapper(self._queue_std)
        self._bmb(lw)

    def benchmark_queue_batch(self) -> None:
        lw = LocalWrapper(self._queue_queue)
        self._bmb(lw)

    def _bmb(self, lw) -> None:  # type: ignore
        for n in range(self._operations // 100):
            for _ in range(100):
                lw.put(n)
            for _ in range(100):
                lw.get()


def invoke_main() -> None:
    execute_benchmarks(ConcurretQueueBenchmarkProvider)


if __name__ == "__main__":
    invoke_main()
