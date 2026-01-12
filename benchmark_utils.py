# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import argparse
import concurrent.futures
import os
import random
import sys
import threading
import time
import traceback
from collections.abc import Callable, Sequence
from typing import List, Type, TypeVar

from ft_utils.local import BatchExecutor


_BATCH_RAND = BatchExecutor(lambda: random.getrandbits(32), 1024)


# Use these for random manipulations as they are much more performant
# in FTPython under contention than the random.* alternatives.
def ft_randint(a: int, b: int) -> int:
    if a > b:
        a, b = b, a

    range_size = b - a + 1
    range_bits = range_size.bit_length()

    accumulated_random = 0
    bits_collected = 0

    while bits_collected < range_bits:
        accumulated_random = (accumulated_random << 32) | _BATCH_RAND.load()
        bits_collected += 32

    result = accumulated_random % range_size
    return a + result


T = TypeVar("T")


def ft_randchoice(seq: Sequence[T]) -> T:
    if not seq:
        raise IndexError("Cannot choose from an empty sequence")
    return seq[ft_randint(0, len(seq) - 1)]


class BenchmarkProvider:
    """
    Base class for benchmark providers.
    """

    def __init__(self, operations: int) -> None:
        self._operations = operations


def parse_arguments(description: str) -> argparse.Namespace:
    """
    Parses command-line arguments common to benchmarking scripts.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--operations", type=int, default=1000, help="Number of operations to perform."
    )
    parser.add_argument(
        "--threads", type=int, default=16, help="Number of threads to use."
    )
    parser.add_argument(
        "--switch_interval",
        type=float,
        default=0.001,
        help="GIL (if used) switch interval in seconds.",
    )
    return parser.parse_args()


def benchmark_operation(operation_func: Callable[[], None]) -> float:
    """
    Measures the time taken to perform a specified operation.
    """
    start_time = time.time()
    operation_func()
    end_time = time.time()
    return end_time - start_time


def worker(
    operation_func: Callable[[], None],
    barrier: threading.Barrier,
) -> list[float]:
    """
    Executes the benchmark multiple times and collects run times.
    """
    barrier.wait()  # Synchronize the start of operations
    run_times: list[float] = [benchmark_operation(operation_func) for _ in range(5)]
    return run_times


def execute_benchmarks(
    provider_class: type[BenchmarkProvider],
) -> None:
    """
    Sets up and executes benchmarks across multiple threads using methods from a BenchmarkProvider.
    """

    args = parse_arguments("list parallel benchmark.")
    num_operations: int = args.operations
    num_threads: int = args.threads
    sys.setswitchinterval(args.switch_interval)

    cmdl_banner = "Command line:" + " ".join(sys.argv)
    print("*" * len(cmdl_banner))
    print("Benchmark for multi-threaded operation")
    print(cmdl_banner)
    print("*" * len(cmdl_banner))

    provider_instance = provider_class(num_operations)
    operation_methods = [
        (method_name[10:], getattr(provider_instance, method_name))
        for method_name in dir(provider_instance)
        if callable(getattr(provider_instance, method_name))
        and method_name.startswith("benchmark_")
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        for operation_name, operation_func in operation_methods:
            if hasattr(provider_instance, "set_up"):
                provider_instance.set_up()  # pyre-ignore[16]
            barrier = threading.Barrier(num_threads)
            futures = [
                executor.submit(worker, operation_func, barrier)
                for _ in range(num_threads)
            ]
            run_times = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    run_times.extend(future.result())
                except IndexError as e:
                    print("Exception in benchmark - exiting hard")
                    print(e)
                    stack_trace = traceback.format_exc()
                    print(stack_trace)
                    os._exit(-1)
            if run_times:
                min_time = min(run_times)
                max_time = max(run_times)
                mean_time = sum(run_times) / len(run_times)
                print(
                    f"    {operation_name:<32} Max: {max_time:.6f} Mean: {mean_time:.6f} Min: {min_time:.6f}"
                )
