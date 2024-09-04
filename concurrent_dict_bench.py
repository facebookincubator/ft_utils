# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import os
import uuid

from typing import Optional

from ft_utils.benchmark_utils import BenchmarkProvider, execute_benchmarks, ft_randint
from ft_utils.concurrent import ConcurrentDict
from ft_utils.local import LocalWrapper


class ConcurretDictBenchmarkProvider(BenchmarkProvider):
    def __init__(self, operations: int) -> None:
        self._operations = operations
        self._cdct: Optional[ConcurrentDict] = None
        self._dct: Optional[dict[int | str, int]] = None

    def set_up(self) -> None:
        self._cdct = ConcurrentDict(os.cpu_count())
        self._dct = {}

    def benchmark_insert(self) -> None:
        lw = LocalWrapper(self._cdct)
        for _ in range(self._operations):
            x = ft_randint(0, 1048576)
            lw[x] = str(x)

    def benchmark_insert_dict(self) -> None:
        lw = LocalWrapper(self._dct)
        for _ in range(self._operations):
            x = ft_randint(0, 1048576)
            lw[x] = str(x)

    def benchmark_update(self) -> None:
        lw = LocalWrapper(self._cdct)
        what = [ft_randint(0, 1024) for _ in range(self._operations // 3)]
        prefix = str(uuid.uuid4())
        for x in what:
            lw[f"{prefix}{x}"] = x
            lw[f"{prefix}{x}"]
            del lw[f"{prefix}{x}"]

    def benchmark_update_dict(self) -> None:
        lw = LocalWrapper(self._dct)
        what = [ft_randint(0, 1024) for _ in range(self._operations // 3)]
        prefix = str(uuid.uuid4())
        for x in what:
            lw[f"{prefix}{x}"] = x
            lw[f"{prefix}{x}"]
            del lw[f"{prefix}{x}"]

    def benchmark_read(self) -> None:
        lw = LocalWrapper(self._cdct)
        what = [ft_randint(0, 1024) for _ in range(1024)]
        for x in what:
            lw[f"{x}"] = x
        for x in range(self._operations):
            x = what[x % 1024]
            lw[f"{x}"]

    def benchmark_read_dict(self) -> None:
        lw = LocalWrapper(self._dct)
        what = [ft_randint(0, 1024) for _ in range(1024)]
        for x in what:
            lw[f"{x}"] = x
        for x in range(self._operations):
            x = what[x % 1024]
            lw[f"{x}"]


def invoke_main() -> None:
    execute_benchmarks(ConcurretDictBenchmarkProvider)


if __name__ == "__main__":
    invoke_main()
