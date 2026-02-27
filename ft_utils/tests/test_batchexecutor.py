# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import gc
import random
import unittest
import weakref
from concurrent.futures import Future, ThreadPoolExecutor

from ft_utils.local import BatchExecutor


def simple_callable() -> str:
    return "result"


def failing_callable() -> None:
    raise Exception("Intentional Failure")


class TestBatchExecutor(unittest.TestCase):
    def test_successful_initialization_and_loading(self) -> None:
        executor: BatchExecutor = BatchExecutor(simple_callable, 5)
        self.assertEqual(executor.load(), "result")
        self.assertEqual(executor.load(), "result")

    def test_initialization_with_non_callable_source(self) -> None:
        with self.assertRaises(TypeError):
            BatchExecutor("not callable", 5)  # pyre-ignore[6]

    def test_initialization_with_non_integer_size(self) -> None:
        with self.assertRaises(TypeError):
            BatchExecutor(simple_callable, "five")  # pyre-ignore[6]

    def test_initialization_with_negative_size(self) -> None:
        with self.assertRaises(ValueError):
            BatchExecutor(simple_callable, -1)

    def test_buffer_refill(self) -> None:
        executor: BatchExecutor = BatchExecutor(simple_callable, 1)
        self.assertEqual(executor.load(), "result")
        self.assertEqual(executor.load(), "result")

    def test_exception_in_callable(self) -> None:
        executor: BatchExecutor = BatchExecutor(failing_callable, 5)
        with self.assertRaises(Exception) as context:
            executor.load()
        self.assertTrue("Intentional Failure" in str(context.exception))

    def test_as_local(self) -> None:
        executor: BatchExecutor = BatchExecutor(simple_callable, 5)
        local_wrapper = executor.as_local()
        self.assertIs(local_wrapper.wrapped, executor)
        self.assertEqual(local_wrapper.load(), "result")


class StatefulCallable:
    def __init__(self) -> None:
        self.call_count: int = 0

    def __call__(self) -> str:
        self.call_count += 1
        return f"result{self.call_count}"


class TestStatefulBatchExecutor(unittest.TestCase):
    def test_stateful_callable_and_buffer_refill(self) -> None:
        callable_instance: StatefulCallable = StatefulCallable()
        executor: BatchExecutor = BatchExecutor(callable_instance, 10)

        for i in range(1, 11):
            self.assertEqual(executor.load(), f"result{i}")

        for i in range(11, 21):
            self.assertEqual(executor.load(), f"result{i}")


def stateful_random_callable() -> int:
    return random.randint(0, 32767)


class TestBatchExecutorConsistency(unittest.TestCase):
    def test_random_integers_multithreaded(self) -> None:
        random.seed(123456)
        what_we_expect: set[int] = {random.randint(0, 32767) for _ in range(128)}

        random.seed(123456)
        executor: BatchExecutor = BatchExecutor(stateful_random_callable, 8)

        def load_from_executor() -> int:
            return executor.load()

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures: list[Future[int]] = [
                pool.submit(load_from_executor) for _ in range(128)
            ]
            results: set[int] = {future.result() for future in futures}

        self.assertEqual(what_we_expect, results)


class SelfReferencingCallable:
    def __init__(self) -> None:
        self.executor: BatchExecutor | None = None

    def set_executor(self, executor: BatchExecutor) -> None:
        self.executor = executor

    def __call__(self) -> str:
        return "result"


class TestBatchExecutorCyclicGarbageCollection(unittest.TestCase):
    def test_cyclic_garbage_collection(self) -> None:
        callable_instance: SelfReferencingCallable = SelfReferencingCallable()
        executor: BatchExecutor = BatchExecutor(callable_instance, 5)
        callable_instance.set_executor(executor)
        weak_ref: weakref.ref[BatchExecutor] = weakref.ref(executor)

        del executor
        del callable_instance

        while gc.collect():
            pass
        self.assertIsNone(weak_ref(), "Executor should have been garbage collected")


if __name__ == "__main__":
    unittest.main()
