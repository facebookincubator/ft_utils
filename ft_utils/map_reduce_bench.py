# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import argparse
import concurrent.futures
import random
import time

from ft_utils.local import LocalWrapper


def is_prime(n: int) -> bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i: int = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def map_primes(numbers: list[int]) -> list[int]:
    wrapped: LocalWrapper = LocalWrapper(numbers)
    return [n for n in wrapped if is_prime(n)]


def run_prime_calculation(
    nodes: int, per_node: int, numbers: list[int], use_threads: bool
) -> list[int]:
    futures: list[concurrent.futures.Future[list[int]]] = []
    prime_numbers: list[int] = []

    Executor: type[concurrent.futures.Executor]
    if use_threads:
        Executor = concurrent.futures.ThreadPoolExecutor
    else:
        Executor = concurrent.futures.ProcessPoolExecutor

    with Executor(max_workers=nodes) as executor:
        for i in range(nodes):
            segment: list[int] = numbers[i * per_node : (i + 1) * per_node]
            futures.append(executor.submit(map_primes, segment))

        for future in concurrent.futures.as_completed(futures):
            prime_numbers.extend(future.result())

    return prime_numbers


def run(nodes: int, per_node: int, use_threads: bool) -> None:
    start_time: float = time.time()
    total_numbers: int = nodes * per_node
    numbers: list[int] = list(range(1, total_numbers + 1))
    random.shuffle(numbers)
    for _ in range(10):
        run_prime_calculation(nodes, per_node, numbers, use_threads)
    end_time: float = time.time()
    print(f"Total time for 10 runs: {end_time - start_time:.2f} seconds")


def invoke_main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Find prime numbers using multiprocessing or threading."
    )
    parser.add_argument(
        "--nodes",
        type=int,
        required=True,
        help="Number of nodes (processes or threads).",
    )
    parser.add_argument(
        "--per-node", type=int, required=True, help="Number of integers per node."
    )
    parser.add_argument(
        "--use-threads",
        action="store_true",
        default=False,
        help="Use threading instead of multiprocessing.",
    )
    args: argparse.Namespace = parser.parse_args()
    run(args.nodes, args.per_node, args.use_threads)
