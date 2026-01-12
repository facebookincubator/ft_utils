# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import gc
import random
import unittest
import weakref
from concurrent.futures import ThreadPoolExecutor

from ft_utils.local import BatchExecutor


def simple_callable():
    return "result"


def failing_callable():
    raise Exception("Intentional Failure")


class TestBatchExecutor(unittest.TestCase):
    def test_successful_initialization_and_loading(self):
        executor = BatchExecutor(simple_callable, 5)
        self.assertEqual(executor.load(), "result")
        self.assertEqual(executor.load(), "result")

    def test_initialization_with_non_callable_source(self):
        with self.assertRaises(TypeError):
            BatchExecutor("not callable", 5)

    def test_initialization_with_non_integer_size(self):
        with self.assertRaises(TypeError):
            BatchExecutor(simple_callable, "five")

    def test_initialization_with_negative_size(self):
        with self.assertRaises(ValueError):
            BatchExecutor(simple_callable, -1)

    def test_buffer_refill(self):
        executor = BatchExecutor(simple_callable, 1)
        self.assertEqual(executor.load(), "result")
        self.assertEqual(executor.load(), "result")

    def test_exception_in_callable(self):
        executor = BatchExecutor(failing_callable, 5)
        with self.assertRaises(Exception) as context:
            executor.load()
        self.assertTrue("Intentional Failure" in str(context.exception))

    def test_as_local(self):
        executor = BatchExecutor(simple_callable, 5)
        local_wrapper = executor.as_local()
        self.assertIs(local_wrapper.wrapped, executor)
        self.assertEqual(local_wrapper.load(), "result")


class StatefulCallable:
    def __init__(self):
        self.call_count = 0

    def __call__(self):
        self.call_count += 1
        return f"result{self.call_count}"


class TestStatefulBatchExecutor(unittest.TestCase):
    def test_stateful_callable_and_buffer_refill(self):
        callable_instance = StatefulCallable()
        executor = BatchExecutor(callable_instance, 10)

        for i in range(1, 11):
            self.assertEqual(executor.load(), f"result{i}")

        for i in range(11, 21):
            self.assertEqual(executor.load(), f"result{i}")


def stateful_random_callable():
    return random.randint(0, 32767)


class TestBatchExecutorConsistency(unittest.TestCase):
    def test_random_integers_multithreaded(self):
        random.seed(123456)
        what_we_expect = {random.randint(0, 32767) for _ in range(128)}

        random.seed(123456)
        executor = BatchExecutor(stateful_random_callable, 8)

        def load_from_executor():
            return executor.load()

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(load_from_executor) for _ in range(128)]
            results = {future.result() for future in futures}

        self.assertEqual(what_we_expect, results)


class SelfReferencingCallable:
    def __init__(self):
        self.executor = None

    def set_executor(self, executor):
        self.executor = executor

    def __call__(self):
        return "result"


class TestBatchExecutorCyclicGarbageCollection(unittest.TestCase):
    def test_cyclic_garbage_collection(self):
        callable_instance = SelfReferencingCallable()
        executor = BatchExecutor(callable_instance, 5)
        callable_instance.set_executor(executor)
        weak_ref = weakref.ref(executor)

        del executor
        del callable_instance

        while gc.collect():
            pass
        self.assertIsNone(weak_ref(), "Executor should have been garbage collected")


if __name__ == "__main__":
    unittest.main()
