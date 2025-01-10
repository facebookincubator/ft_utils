# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import argparse
import concurrent.futures
import random
import timeit

from concurrent.futures import Executor
from typing import Dict, Tuple

from ft_utils.concurrency import AtomicInt64, ConcurrentDict, ConcurrentQueue
from ft_utils.local import LocalWrapper

cached = AtomicInt64()
missed = AtomicInt64()


def fib_tasks(n: int, executor: Executor, workers: int, rs: int) -> None:
    memo = {}
    futures = [
        executor.submit(fib_worker, n + random.randint(0, rs * 2), memo)
        for _ in range(rs)
    ]

    for f in futures:
        f.result()


def fib_queue(n: int, executor: Executor, workers: int, rs: int) -> None:
    q = ConcurrentQueue(workers)
    for _ in range(rs):
        q.push(n + random.randint(0, rs * 2))

    tasks = AtomicInt64(rs)
    memo = ConcurrentDict(workers)

    def compute():  # pyre-ignore
        _memo = LocalWrapper(memo)
        _tasks = LocalWrapper(tasks)
        _fib_worker = LocalWrapper(fib_worker)
        _q = LocalWrapper(q)
        while _tasks.decr() > -1:
            z = _q.pop()
            _fib_worker(z, _memo)

    futures = [executor.submit(compute) for _ in range(workers)]

    for f in futures:
        f.result()


def fib_worker(n: int, memo: dict[int, tuple[int, int]]) -> tuple[int, int]:
    # Check memoization cache in a thread-safe manner
    if n in memo:
        cached.incr()
        return memo[n]
    missed.incr()

    if n == 0:
        result = (0, 1)
    elif n == 1:
        result = (1, 1)
    elif n == 2:
        result = (1, 2)
    else:
        k = n // 2
        a = fib_worker(k, memo)

        # Compute the current Fibonacci numbers using the identities
        c = a[0] * (2 * a[1] - a[0])
        d = a[0] * a[0] + a[1] * a[1]

        if n % 2 == 0:
            result = (c, d)
        else:
            result = (d, c + d)

    # Store the result in the memoization cache
    memo[n] = result

    return result


def invoke_main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute multiple Fibonacci numbers in parallel"
    )
    parser.add_argument(
        "--nth_element",
        type=int,
        required=True,
        help="The position of the Fibonacci number to compute from.",
    )
    parser.add_argument(
        "--run_size", type=int, required=True, help="How many numbers to compute."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=16,
        help="The number of workers in the pool. Defaults to 16.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=("threads", "fast_threads", "processes"),
        help="Operation mode: threads | fast_threads | processes.",
    )

    args = parser.parse_args()

    match args.mode:
        case "threads":
            executor_type = concurrent.futures.ThreadPoolExecutor
            to_execute = fib_tasks

        case "fast_threads":
            executor_type = concurrent.futures.ThreadPoolExecutor
            to_execute = fib_queue

        case "processes":
            executor_type = concurrent.futures.ProcessPoolExecutor
            to_execute = fib_tasks

        case _:
            raise RuntimeError("Code should never get here")

    def calculate_fibonacci():  # pyre-ignore
        with executor_type(max_workers=args.workers) as executor:
            to_execute(args.nth_element, executor, args.workers, args.run_size)

    execution_time = timeit.timeit(calculate_fibonacci, number=5)

    print(f"Report:")
    print(f"---------")
    print(f"- nth Element: {args.nth_element}")
    print(f"- Mode: {args.mode}")
    print(f"- Size: {args.run_size}")
    print(f"- Workers: {args.workers}")
    print(f"- Average Execution Time: {execution_time / 5:.6f} seconds")
    if args.mode != "processes":
        print(f"- Cache rate: {int(cached) / int(missed):.6f}")
    print(f"- Total Execution Time (5 runs): {execution_time:.2f} seconds")


if __name__ == "__main__":
    invoke_main()
