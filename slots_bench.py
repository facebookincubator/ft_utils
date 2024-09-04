# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import gc
import weakref

from typing import Any

from ft_utils.benchmark_utils import (
    BenchmarkProvider,
    execute_benchmarks,
    ft_randchoice,
    ft_randint,
)
from ft_utils.local import LocalWrapper


class SlotClass:
    __slots__ = "a", "b", "c", "d", "e", "f", "g", "h", "__weakref__"

    def __init__(
        self,
        a: Any = None,  # pyre-ignore[2]
        b: Any = None,  # pyre-ignore[2]
        c: Any = None,  # pyre-ignore[2]
        d: Any = None,  # pyre-ignore[2]
        e: Any = None,  # pyre-ignore[2]
        f: Any = None,  # pyre-ignore[2]
        g: Any = None,  # pyre-ignore[2]
        h: Any = None,  # pyre-ignore[2]
    ) -> None:
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f
        self.g = g
        self.h = h


class SlotsBenchmarkProvider(BenchmarkProvider):
    def __init__(self, operations: int) -> None:
        self._operations = operations
        self._obj = SlotClass(1, 2, 3, 4, 5)

    def benchmark_modify_attributes(self) -> None:
        obj = LocalWrapper(self._obj)
        settable: tuple[str, ...] = SlotClass.__slots__[:-1]
        for _ in range(self._operations):
            setattr(obj, ft_randchoice(settable), ft_randint(1, 100))

    def benchmark_read_attributes(self) -> None:
        obj = LocalWrapper(self._obj)
        settable: tuple[str, ...] = SlotClass.__slots__[:-1]
        for _ in range(self._operations):
            _ = getattr(obj, ft_randchoice(settable))

    def benchmark_mixed_operations(self) -> None:
        obj = LocalWrapper(self._obj)
        settable: tuple[str, ...] = SlotClass.__slots__[:-1]
        for _ in range(self._operations):
            if ft_randint(0, 1):
                setattr(obj, ft_randchoice(settable), ft_randint(1, 100))
            else:
                _ = getattr(obj, ft_randchoice(settable))

    def benchmark_use_slots_in_generator(self) -> None:
        obj = LocalWrapper(self._obj)
        sum(obj.a for _ in range(self._operations * 10))

    def benchmark_reference_cycle(self) -> None:
        obj = LocalWrapper(self._obj)
        for _ in range(32):
            obj.f = [obj for _ in range(self._operations)]
            obj.f = None

    def benchmark_self_reference(self) -> None:
        obj = LocalWrapper(self._obj)
        for _ in range(self._operations * 10):
            obj.g = None
            obj.g = obj

    def benchmark_tuple_cycle(self) -> None:
        obj = LocalWrapper(self._obj)
        for _ in range(self._operations * 10):
            obj.g = None
            obj.h = (obj,)

    def benchmark_hammer_update(self) -> None:
        obj = LocalWrapper(self._obj)
        for i in range(self._operations):
            obj.a += 1
        for i in range(self._operations // 10):
            obj.a += obj.b
            obj.b += obj.a

    def benchmark_garbage_collection(self) -> None:
        ops = max(1, self._operations // 1000)
        for _ in range(ops):
            obj = SlotClass()
            obj.a = obj
            obj.b = obj.a
            obj.c = obj.b
            obj.d = (obj.b, None)
            obj.e = {1, obj}
            obj.f = self._obj
            del obj
            gc.collect()


def invoke_main() -> None:
    execute_benchmarks(SlotsBenchmarkProvider)


if __name__ == "__main__":
    invoke_main()
