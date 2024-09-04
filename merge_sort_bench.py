# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import argparse
import array
import concurrent.futures
import os
import random
import sys
import threading
import time

from ft_utils.local import LocalWrapper


class MergeSortBenchmark:
    def __init__(
        self,
        n_cpus: int = 16,
        max_size: int = 1000000,
        threshold: int = 1000,
        max_threads: int = 2,
    ) -> None:
        self.n_cpus: int = n_cpus
        self.max_size: int = max_size
        self.threshold: int = threshold
        self.target: array.array = array.array(
            "i", [random.randint(0, 9999) for _ in range(self.max_size)]
        )
        self.lock: threading.Lock = threading.Lock()
        self.thread_counter: int = 0
        self.peak_threads: int = 0
        self.max_threads: float = max_threads / 2

    def increment_thread_count(self) -> None:
        with self.lock:
            self.thread_counter += 1
            self.peak_threads = max(self.thread_counter, self.peak_threads)

    def decrement_thread_count(self) -> None:
        with self.lock:
            self.thread_counter -= 1

    @staticmethod
    def merge(
        target: array.array | LocalWrapper, left: int, mid: int, right: int
    ) -> None:
        n1: int = mid - left + 1
        n2: int = right - mid

        L: array.array = target[left : left + n1]
        R: array.array = target[mid + 1 : mid + 1 + n2]

        i: int = 0
        j: int = 0
        k: int = left

        while i < n1 and j < n2:
            if L[i] <= R[j]:
                target[k] = L[i]
                i += 1
            else:
                target[k] = R[j]
                j += 1
            k += 1

        while i < n1:
            target[k] = L[i]
            i += 1
            k += 1

        while j < n2:
            target[k] = R[j]
            j += 1
            k += 1

    def sequential_merge_sort(
        self, target: array.array | LocalWrapper, left: int, right: int
    ) -> None:
        if left < right:
            mid: int = left + (right - left) // 2
            self.sequential_merge_sort(target, left, mid)
            self.sequential_merge_sort(target, mid + 1, right)
            self.merge(target, left, mid, right)

    def merge_sort(
        self,
        target: array.array | LocalWrapper,
        left: int,
        right: int,
        new_thread: bool = False,
    ) -> None:
        if new_thread:
            self.increment_thread_count()
            # Make view here.
            if isinstance(target, array.array):
                target = LocalWrapper(target)
            else:
                target = LocalWrapper(target.wrapped)
        if left < right:
            mid: int = left + (right - left) // 2

            if right - left > self.threshold:
                if self.thread_counter < self.max_threads:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future1: concurrent.futures.Future = executor.submit(
                            self.merge_sort, target, left, mid, True
                        )
                        future2: concurrent.futures.Future = executor.submit(
                            self.merge_sort, target, mid + 1, right, True
                        )
                    future1.result()
                    future2.result()
                else:
                    self.merge_sort(target, left, mid)
                    self.merge_sort(target, mid + 1, right)
            else:
                self.sequential_merge_sort(target, left, mid)
                self.sequential_merge_sort(target, mid + 1, right)

            self.merge(target, left, mid, right)
        if new_thread:
            self.decrement_thread_count()

    def run(self) -> int:
        os.sched_setaffinity(0, list(range(int(self.n_cpus))))
        gil_enabled: bool = getattr(sys, "_is_gil_enabled", lambda: True)()  # pyre-ignore[16]
        start_time: float = time.time()
        self.merge_sort(self.target, 0, self.max_size - 1)
        end_time: float = time.time()
        total_time: float = end_time - start_time

        for i in range(1, self.max_size):
            if self.target[i - 1] > self.target[i]:
                print(f"Error: Array is not sorted at position {i}.")
                return -1

        print("Array is correctly sorted.")
        print(
            f"Parameters: N_CPUS={self.n_cpus}, MAX_SIZE={self.max_size}, THRESHOLD={self.threshold}, MAX_THREADS={self.max_threads*2}"
        )
        print(f"Time taken: {total_time} seconds")
        print(f"Peak_threads: {self.peak_threads}")
        print(f"GIL Enabled: {gil_enabled}")
        return 0


def invoke_main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--n_cpus", type=int, default=16)
    parser.add_argument("--max_size", type=int, default=1000000)
    parser.add_argument("--threshold", type=int, default=1000)
    parser.add_argument("--max_threads", type=int, default=2)
    args: argparse.Namespace = parser.parse_args()
    if args.max_threads < 2:
        raise ValueError("Minimum threads is 2")

    benchmark: MergeSortBenchmark = MergeSortBenchmark(
        args.n_cpus, args.max_size, args.threshold, args.max_threads
    )
    benchmark.run()


if __name__ == "__main__":
    invoke_main()
