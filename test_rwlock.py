# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import threading
import time
import unittest

from ft_utils.concurrent import AtomicFlag, AtomicInt64
from ft_utils.lock_test_utils import run_interrupt_handling
from ft_utils.synchronization import RWLock, RWReadContext, RWWriteContext


class TestRWLock(unittest.TestCase):
    def execute(self, what):
        def runnit():
            for _ in range(5):
                what()

        threads = [threading.Thread(target=runnit) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_simple_read_lock(self):
        lock = RWLock()
        lock.lock_read()
        time.sleep(0.01)
        lock.unlock_read()
        lock.lock_read()
        time.sleep(0.01)
        lock.unlock_read()

    def test_simple_write_lock(self):
        lock = RWLock()
        lock.lock_write()
        time.sleep(0.01)
        lock.unlock_write()
        lock.lock_write()
        time.sleep(0.01)
        lock.unlock_write()

    def test_lock_write(self):
        lock = RWLock()
        count = AtomicInt64()
        ok = AtomicFlag(True)
        ran = AtomicFlag(False)

        def check_serialized():
            try:
                lock.lock_write()
                count.incr()
                if count > 1:
                    ok.set(False)
                time.sleep(0.01)
                count.decr()
            finally:
                lock.unlock_write()
            ran.set(True)

        self.execute(check_serialized)
        self.assertTrue(ok)
        self.assertTrue(ran)

    def test_lock_read(self):
        lock = RWLock()
        count = AtomicInt64()
        ok = AtomicFlag(False)
        ran = AtomicFlag(False)

        def check_notserialized():
            try:
                lock.lock_read()
                count.incr()
                if count > 1:
                    ok.set(True)
                time.sleep(0.1)
                count.decr()
            finally:
                lock.unlock_read()
            ran.set(True)

        self.execute(check_notserialized)
        self.assertTrue(ok)
        self.assertTrue(ran)

    def test_lock_read_write(self):
        lock = RWLock()
        rcount = AtomicInt64()
        wcount = AtomicInt64()
        rok = AtomicFlag(False)
        wokr = AtomicFlag(True)
        wokw = AtomicFlag(True)
        rran = AtomicFlag(False)
        wran = AtomicFlag(False)

        def check_both():
            try:
                lock.lock_read()
                rcount.incr()
                if rcount > 1:
                    rok.set(True)
                if wcount > 0:
                    rok.set(True)
                time.sleep(0.01)
                rcount.decr()
                rran.set(True)
            finally:
                lock.unlock_read()
            time.sleep(0.01)
            try:
                lock.lock_write()
                wcount.incr()
                if wcount > 1:
                    wokw.set(False)
                if rcount > 0:
                    wokr.set(False)
                time.sleep(0.01)
                wcount.decr()
                wran.set(True)
            finally:
                lock.unlock_write()

        self.execute(check_both)
        self.assertTrue(rok)
        self.assertTrue(wokr)
        self.assertTrue(wokw)
        self.assertTrue(rran)
        self.assertTrue(wran)

    def test_simple_context(self):
        lock = RWLock()
        with RWReadContext(lock):
            pass
        with RWWriteContext(lock):
            pass

    def test_lock_context(self):
        lock = RWLock()
        rcount = AtomicInt64()
        wcount = AtomicInt64()
        rok = AtomicFlag(False)
        wokr = AtomicFlag(True)
        wokw = AtomicFlag(True)
        rran = AtomicFlag(False)
        wran = AtomicFlag(False)

        def check_both():
            with RWReadContext(lock):
                rcount.incr()
                if rcount > 1:
                    rok.set(True)
                if wcount > 0:
                    rok.set(False)
                    return
                time.sleep(0.01)
                rcount.decr()
                rran.set(True)
            time.sleep(0.01)
            with RWWriteContext(lock):
                wcount.incr()
                if wcount > 1:
                    wokw.set(False)
                    return
                if rcount > 0:
                    wokr.set(False)
                    return
                time.sleep(0.01)
                wcount.decr()
                wran.set(True)

        self.execute(check_both)
        self.assertTrue(rok)
        self.assertTrue(wokr)
        self.assertTrue(wokw)
        self.assertTrue(rran)
        self.assertTrue(wran)

    def test_readers(self):
        lock = RWLock()
        count = AtomicInt64()
        done = AtomicFlag(False)

        def read_wait():
            with RWReadContext(lock):
                count.incr()
                while not done:
                    time.sleep(0.01)

        threads = [threading.Thread(target=read_wait) for _ in range(10)]

        for t in threads:
            t.start()
        while count < 10:
            time.sleep(0.01)
        readers = lock.readers()
        writers_waiting = lock.writers_waiting()
        writer_locked = lock.writer_locked()
        done.set(True)

        for t in threads:
            t.join()

        self.assertEqual(readers, 10)
        self.assertEqual(writers_waiting, 0)
        self.assertEqual(writer_locked, 0)

    def test_writers_block_readers(self):
        lock = RWLock()
        done = AtomicFlag(False)
        locked = AtomicFlag(False)
        new_start = AtomicInt64()
        started = AtomicFlag(False)

        def read_wait1():
            with RWReadContext(lock):
                while not done:
                    time.sleep(0.01)

        def read_wait2():
            new_start.incr()
            with RWReadContext(lock):
                while not done:
                    time.sleep(0.01)
                new_start.decr()

        def write_wait():
            started.set(True)
            with RWWriteContext(lock):
                pass

        # Get 5 read locks
        threads = [threading.Thread(target=read_wait1) for _ in range(5)]

        for t in threads:
            t.start()

        while lock.readers() < 5:
            time.sleep(0.01)

        # Ask for a write lock even though read is held.
        t = threading.Thread(target=write_wait)
        t.start()
        threads.append(t)

        while not started:
            time.sleep(0.01)

        # Now start 5 new read threads which should not get the read lock as the write waiting blocks.
        new_threads = [threading.Thread(target=read_wait2) for _ in range(5)]

        for t in new_threads:
            t.start()
            threads.append(t)

        while new_start < 5:
            time.sleep(0.01)
        readers = lock.readers()
        locked = lock.writer_locked()
        waiting = lock.writers_waiting()
        done.set(True)

        # Drain the second set of readers.
        while new_start > 0:
            time.sleep(0.01)

        for t in threads:
            t.join()

        self.assertEqual(readers, 5)
        self.assertEqual(waiting, 1)
        self.assertFalse(locked)
        self.assertEqual(lock.readers(), 0)

    def test_writers_waiting(self):
        lock = RWLock()
        done = AtomicFlag(False)
        started = AtomicFlag(False)
        locked = AtomicFlag(False)
        unlocked = AtomicFlag(True)

        def read_wait():
            with RWReadContext(lock):
                while not done:
                    time.sleep(0.01)

        def write_wait():
            unlocked.set(not lock.writer_locked())
            started.set(True)
            with RWWriteContext(lock):
                locked.set(lock.writer_locked())

        threads = [threading.Thread(target=read_wait) for _ in range(10)]

        for t in threads:
            t.start()

        while lock.readers() < 0:
            time.sleep(0.01)

        t = threading.Thread(target=write_wait)
        t.start()
        threads.append(t)

        while lock.readers() < 10 or (not started):
            time.sleep(0.01)

        time.sleep(0.1)
        writers_waiting = lock.writers_waiting()
        done.set(True)

        for t in threads:
            t.join()

        self.assertEqual(writers_waiting, 1)
        self.assertTrue(locked)
        self.assertTrue(unlocked)


class TestRWLockSignals(unittest.TestCase):
    def test_interrupt_handling_write(self):
        def acquire(lock):
            lock.lock_write()

        def release(lock):
            lock.unlock_write()

        run_interrupt_handling(self, RWLock(), acquire, release)

    def test_interrupt_handling_read(self):
        phase = AtomicInt64(0)

        def acquire(lock):
            if phase == 0:
                lock.lock_write()
            elif phase == 1:
                lock.lock_read()
            else:
                raise RuntimeError("Acquire lock phase error")
            phase.incr()

        def release(lock):
            if phase == 1:
                lock.unlock_write()
            if phase == 2:
                lock.unlock_read()
            else:
                raise RuntimeError("Release lock phase error")
            phase.incr()

        def excepthook(args):
            if (
                args.exc_type != RuntimeError
                or str(args.exc_value) != "Release lock phase error"
            ):
                raise RuntimeError("Unexpected exception occurred")

        previous = threading.excepthook
        threading.excepthook = excepthook

        try:
            run_interrupt_handling(self, RWLock(), acquire, release)
        finally:
            threading.excepthook = previous


if __name__ == "__main__":
    unittest.main()
