# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

from typing import Any

from ft_utils.benchmark_utils import BenchmarkProvider, execute_benchmarks, ft_randint
from ft_utils.local import LocalWrapper


class ListBenchmarkProvider(BenchmarkProvider):
    def __init__(self, operations: int) -> None:
        self._operations = operations
        self._int_list: list[int] = list(range(1024))
        ll = []
        for _ in range(1024):
            ll.append(ll)
        self._ref_list: list[Any] = ll  # pyre-ignore[4]

    def benchmark_random_read_int(self) -> None:
        lst = LocalWrapper(self._int_list)
        num_operations = self._operations
        lsz = len(lst)
        for _ in range(num_operations):
            _ = lst[ft_randint(0, lsz - 1)]

    def benchmark_random_read_ref(self) -> None:
        lst = LocalWrapper(self._ref_list)
        num_operations = self._operations
        lsz = len(lst)
        for _ in range(num_operations):
            _ = lst[ft_randint(0, lsz - 1)][ft_randint(0, lsz - 1)]

    def benchmark_random_write_int(self) -> None:
        lst = LocalWrapper(self._int_list)
        num_operations = self._operations
        lsz = len(lst)
        for idx in range(num_operations):
            lst[ft_randint(0, lsz - 1)] = idx

    def benchmark_random_read_write_int(self) -> None:
        lst = LocalWrapper(self._int_list)
        num_operations = self._operations
        lsz = len(lst)
        for _ in range(num_operations):
            lst[ft_randint(0, lsz - 1)] = lst[ft_randint(0, lsz - 1)]

    def benchmark_sequential_read_write_int(self) -> None:
        lst = LocalWrapper(self._int_list)
        num_operations = self._operations
        lsz = len(lst)
        for idx in range(num_operations):
            pos = idx % lsz
            lst[pos] = idx
            _ = lst[pos]

    def benchmark_resize_int(self) -> None:
        lst = LocalWrapper(self._int_list)
        num_operations = self._operations
        for idx in range(num_operations):
            lst.append(idx)
        for _ in range(num_operations):
            lst.pop()

    def benchmark_resize_ref(self) -> None:
        lst = LocalWrapper(self._ref_list)
        num_operations = self._operations
        for idx in range(num_operations):
            lst.append(idx)
        for _ in range(num_operations):
            lst.pop()

    def benchmark_concurrent_resize_read_write_int(self) -> None:
        self._crrw(self._int_list)

    def benchmark_concurrent_resize_read_write_ref(self) -> None:
        self._crrw(self._ref_list)

    def _crrw(self, lst_in: list[Any]) -> None:  # pyre-ignore[2]
        lst = LocalWrapper(lst_in)
        num_operations = self._operations
        for idx in range(num_operations):
            try_again = True
            while try_again:
                try:
                    pos = idx % len(lst)
                    lst.append(lst[pos])
                    lst.pop(0)
                    pos_a = (37 + idx) % len(lst)
                    pos_b = idx % len(lst)
                    lst[pos_a] = lst[pos_b]
                    try_again = False
                except IndexError:
                    pass


def invoke_main() -> None:
    execute_benchmarks(ListBenchmarkProvider)


if __name__ == "__main__":
    invoke_main()
