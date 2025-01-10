# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict


import threading
from collections.abc import Callable

from ft_utils.concurrency import AtomicInt64
from ft_utils.synchronization import IntervalLock

power: int = 10
base: float = 3.14
current_threads = AtomicInt64(0)
peak_threads = AtomicInt64(0)


def run_in_threads(target: Callable[[], None]) -> float:
    global result
    result = 1.0  # pyre-ignore
    threads = []
    for _ in range(power):
        thread = threading.Thread(target=target)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    return result


def run_in_main(target: Callable[[], None]) -> float:
    global result
    result = 1.0
    for _ in range(power):
        target()
    return result


def print_results(descr: str, target: Callable[[], None]) -> None:
    current_threads.set(0)
    peak_threads.set(0)
    print(f"Results from a {descr} example")
    print(f"    Threaded  Result = {run_in_threads(target)}")
    print(f"    Reference Result = {run_in_main(target)}")


def single_multiply_simple() -> None:
    global result
    result *= base


def single_multiply_threads_tracked() -> None:
    global result
    ct = current_threads.incr()
    if ct > peak_threads:
        peak_threads.set(ct)
    result *= base
    current_threads.decr()


def single_multiply_long() -> None:
    global result
    ct = current_threads.incr()
    if ct > peak_threads:
        peak_threads.set(ct)
    for _ in range(100000):
        for _ in range(10):
            result *= base
        for _ in range(10):
            result /= base
    result *= base
    current_threads.decr()


ilock = IntervalLock()


def single_multiply_consistent() -> None:
    global result
    with ilock:
        ct = current_threads.incr()
        if ct > peak_threads:
            peak_threads.set(ct)
        for _ in range(100000):
            ilock.poll()
            for _ in range(10):
                result *= base
            for _ in range(10):
                result /= base
        result *= base
        current_threads.decr()


def invoke_main() -> None:
    print_results("simple", single_multiply_simple)
    print()

    print_results("threads tracked", single_multiply_threads_tracked)
    print(f"Peak theads is {peak_threads}")
    print()

    print_results("very long load", single_multiply_long)
    print(f"Peak theads is {peak_threads}")
    print()

    print_results("fully consistent", single_multiply_consistent)
    print(f"Peak theads is {peak_threads}")
    print()


if __name__ == "__main__":
    invoke_main()
