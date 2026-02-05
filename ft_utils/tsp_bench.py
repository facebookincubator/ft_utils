# Copyright (c) Meta Platforms, Inc. and affiliates.

import argparse
import random
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

# pyre-strict


def setup() -> None:
    global NUM_THREADS, CITIES, MAX_COST, NUM_RUNS
    parser = argparse.ArgumentParser(description="TSP Solver")
    parser.add_argument("--num_threads", type=int, default=8, help="Number of threads")
    parser.add_argument("--num_runs", type=int, default=5, help="Number of runs")
    parser.add_argument("--cities", type=int, default=8, help="Number of cities")
    args: argparse.Namespace = parser.parse_args()
    NUM_THREADS = args.num_threads  # pyre-ignore[10]
    NUM_RUNS = args.num_runs  # pyre-ignore[10]
    CITIES = args.cities  # pyre-ignore[10]
    MAX_COST = sys.maxsize  # pyre-ignore[10]
    if NUM_THREADS > CITIES:
        raise ValueError("num_threads > cities will produce misleading results")
    print(f"TSP run for ncities={CITIES}, nthreads={NUM_THREADS}")


def swap(array: list[int], pos1: int, pos2: int) -> None:
    array[pos1], array[pos2] = array[pos2], array[pos1]


def calculate_cost_bf(perm: list[int], matrix: list[list[int]]) -> int:
    cost = 0
    for i in range(CITIES - 1):
        cost += matrix[perm[i]][perm[i + 1]]
    cost += matrix[perm[CITIES - 1]][perm[0]]  # Returning to the start city
    return cost


def permute(
    array: list[int],
    start: int,
    end: int,
    matrix: list[list[int]],
    min_cost: list[int],
) -> None:
    if start == end:
        current_cost = calculate_cost_bf(array, matrix)
        if current_cost < min_cost[0]:
            min_cost[0] = current_cost
        return
    for i in range(start, end + 1):
        swap(array, start, i)
        permute(array, start + 1, end, matrix, min_cost)
        swap(array, start, i)  # backtrack


def brute_force_tsp(matrix: list[list[int]]) -> int:
    min_cost = [MAX_COST]
    cities = list(range(CITIES))
    permute(cities, 0, CITIES - 1, matrix, min_cost)
    return min_cost[0]


class SharedData:
    def __init__(self) -> None:
        self.city_matrix: list[list[int]] = [[0] * CITIES for _ in range(CITIES)]
        self.best_cost: int = MAX_COST
        self.lock: threading.Lock = threading.Lock()


def calculate_cost(path: list[int], matrix: list[list[int]]) -> int:
    cost = 0
    num_cities = len(path)
    for i in range(num_cities - 1):
        cost += matrix[path[i]][path[i + 1]]
    cost += matrix[path[num_cities - 1]][path[0]]
    return cost


def branch_and_bound(
    data: SharedData, start_city: int, barrier: threading.Barrier
) -> None:
    barrier.wait()
    visited = [False] * CITIES
    current_path = [0] * (CITIES + 1)
    # Rotate cities so that start_city is at the beginning
    cities = list(range(CITIES))
    cities = cities[start_city:] + cities[:start_city]
    visited[0] = True
    current_path[0] = cities[0]
    solve_tsp(data, visited, current_path, 1, cities)


def solve_tsp(
    data: SharedData,
    visited: list[bool],
    current_path: list[int],
    level: int,
    cities: list[int],
) -> None:
    if level == CITIES:
        cost = calculate_cost(current_path, data.city_matrix)
        if cost < data.best_cost:
            with data.lock:
                if cost < data.best_cost:
                    data.best_cost = cost
        return
    for i in range(CITIES):
        if not visited[i]:
            visited[i] = True
            current_path[level] = cities[i]
            solve_tsp(data, visited, current_path, level + 1, cities)
            visited[i] = False


def generate_matrix(matrix: list[list[int]]) -> None:
    for i in range(CITIES):
        for j in range(CITIES):
            matrix[i][j] = 0 if i == j else random.randint(1, 100)


class ExceptionWrapper:
    def __init__(self, func: Callable[..., Any]) -> None:  # pyre-ignore[2]
        self.func = func
        self.exception: Exception | None = None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # pyre-ignore[3]
        try:
            return self.func(*args, **kwargs)
        except Exception as e:
            self.exception = e


def run_test(test_number: int, matrix: list[list[int]]) -> None:
    data = SharedData()
    data.city_matrix = matrix
    start = time.time()
    futures = []
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        barrier = threading.Barrier(NUM_THREADS)
        for i in range(NUM_THREADS):
            wrapper = ExceptionWrapper(branch_and_bound)
            future = executor.submit(wrapper, data, i, barrier)
            futures.append((future, wrapper))

    def check_except(future: Future, wrapper: ExceptionWrapper) -> None:
        if future.exception() is not None:
            print(f"Exception occurred in thread {future}: {future.exception()}")
        elif wrapper.exception is not None:
            print(
                f"Exception occurred in function {wrapper.func.__name__}: {wrapper.exception}"
            )
        else:
            return
        exit(1)

    for future, wrapper in futures:
        check_except(future, wrapper)

    end = time.time()
    print(f"Test {test_number}: {end - start} seconds, cost: {data.best_cost}")


def invoke_main() -> None:
    setup()
    random.seed()
    test_matrices: list[list[list[int]]] = [
        [[0] * CITIES for _ in range(CITIES)] for _ in range(NUM_RUNS)
    ]

    for test in range(NUM_RUNS):
        generate_matrix(test_matrices[test])
        run_test(test + 1, test_matrices[test])

    print(f"\nDouble Check = {brute_force_tsp(test_matrices[-1])}")


if __name__ == "__main__":
    invoke_main()  # pragma: no cover
