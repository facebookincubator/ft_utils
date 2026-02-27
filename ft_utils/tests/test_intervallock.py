# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import threading
import time
import unittest

from ft_utils.lock_test_utils import run_interrupt_handling
from ft_utils.synchronization import IntervalLock


class TestIntervalLock(unittest.TestCase):
    def test_lock_and_unlock(self) -> None:
        lock: IntervalLock = IntervalLock()
        self.assertIsNone(lock.lock())
        self.assertIsNone(lock.unlock())

    def test_lock_twice_from_same_thread(self) -> None:
        lock: IntervalLock = IntervalLock()
        self.assertIsNone(lock.lock())
        with self.assertRaises(RuntimeError):
            lock.lock()
        self.assertIsNone(lock.unlock())

    def test_unlock_from_different_thread(self) -> None:
        lock: IntervalLock = IntervalLock()
        lock.lock()

        def try_unlock() -> None:
            with self.assertRaises(RuntimeError):
                lock.unlock()

        thread: threading.Thread = threading.Thread(target=try_unlock)
        thread.start()
        thread.join()

        self.assertIsNone(lock.unlock())

    def test_poll_without_lock(self) -> None:
        lock: IntervalLock = IntervalLock()
        with self.assertRaises(RuntimeError):
            lock.poll()

    def test_cede_without_lock(self) -> None:
        lock: IntervalLock = IntervalLock()
        with self.assertRaises(RuntimeError):
            lock.cede()

    def test_poll_after_interval(self) -> None:
        lock: IntervalLock = IntervalLock(interval=0.01)  # 10ms
        self.assertFalse(lock.locked())
        lock.lock()
        self.assertTrue(lock.locked())
        time.sleep(0.02)  # Sleep longer than the interval
        self.assertIsNone(lock.poll())
        self.assertTrue(lock.locked())
        lock.unlock()
        self.assertFalse(lock.locked())

    def test_cede_functionality(self) -> None:
        lock: IntervalLock = IntervalLock(interval=0.01)  # 10ms
        self.assertFalse(lock.locked())
        lock.lock()
        self.assertTrue(lock.locked())
        self.assertIsNone(lock.cede())
        self.assertTrue(lock.locked())
        lock.unlock()
        self.assertFalse(lock.locked())

    def test_context_manager(self) -> None:
        lock: IntervalLock = IntervalLock()
        with lock:
            self.assertTrue(lock.locked())
        self.assertFalse(lock.locked())

    def test_multiple_threads_locking(self) -> None:
        lock: IntervalLock = IntervalLock()
        results: list[int] = []

        def thread_func() -> None:
            lock.lock()
            time.sleep(0.01)
            results.append(threading.get_ident())
            lock.unlock()

        threads: list[threading.Thread] = [
            threading.Thread(target=thread_func) for _ in range(10)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check if results have unique thread IDs
        self.assertEqual(len(set(results)), 10)

    def _test_lock_method_allows_other_threads_to_acquire_lock(
        self, lock_method: str, use_sleep: bool, with_cede: bool
    ) -> None:
        lock: IntervalLock = IntervalLock(interval=0.01)  # 10ms
        lock.lock()

        num_threads: int = 10
        started_events: list[threading.Event] = [
            threading.Event() for _ in range(num_threads)
        ]
        acquired_events: list[threading.Event] = [
            threading.Event() for _ in range(num_threads)
        ]

        def other_thread_func(
            started_event: threading.Event, acquired_event: threading.Event
        ) -> None:
            started_event.set()  # Signal that the thread has started
            with lock:
                if with_cede:
                    lock.cede()
                acquired_event.set()  # Signal that the lock was acquired

        threads: list[threading.Thread] = [
            threading.Thread(
                target=other_thread_func, args=(started_events[i], acquired_events[i])
            )
            for i in range(num_threads)
        ]

        for thread in threads:
            thread.start()

        for started_event in started_events:
            started_event.wait()  # Wait until all threads have started

        for acquired_event in acquired_events:
            if use_sleep:
                time.sleep(0.02)  # Ensure the interval has passed
            getattr(lock, lock_method)()  # Call the lock method (poll or yield)

            acquired_event.wait(1)  # Wait for each thread to acquire the lock

        for acquired_event in acquired_events:
            self.assertTrue(
                acquired_event.is_set()
            )  # Check if each thread acquired the lock

        lock.unlock()

        for thread in threads:
            thread.join()

    def test_poll_allows_other_thread_to_acquire_lock(self) -> None:
        self._test_lock_method_allows_other_threads_to_acquire_lock(
            "poll", use_sleep=True, with_cede=False
        )

    def test_cede_allows_other_thread_to_acquire_lock(self) -> None:
        self._test_lock_method_allows_other_threads_to_acquire_lock(
            "cede", use_sleep=False, with_cede=False
        )

    def test_poll_allows_other_thread_to_acquire_lock_inner(self) -> None:
        self._test_lock_method_allows_other_threads_to_acquire_lock(
            "poll", use_sleep=True, with_cede=True
        )

    def test_cede_allows_other_thread_to_acquire_lock_inner(self) -> None:
        self._test_lock_method_allows_other_threads_to_acquire_lock(
            "cede", use_sleep=False, with_cede=True
        )


class TestIntervalLockSignals(unittest.TestCase):
    def test_interrupt_handling(self) -> None:
        def acquire(lock: object) -> None:
            lock.lock()  # pyre-ignore[16]

        def release(lock: object) -> None:
            lock.unlock()  # pyre-ignore[16]

        run_interrupt_handling(self, IntervalLock(), acquire, release)


if __name__ == "__main__":
    unittest.main()
