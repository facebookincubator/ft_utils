# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import gc
import queue
import threading
import time
import unittest
import weakref

import ft_utils.concurrency as concurrency
import ft_utils.local as local


class TestConcurrentDict(unittest.TestCase):
    def test_smoke(self):
        dct = concurrency.ConcurrentDict()
        dct[1] = 2
        self.assertEqual(dct[1], 2)
        self.assertTrue(1 in dct)
        del dct[1]
        with self.assertRaisesRegex(KeyError, "1"):
            dct[1]
        with self.assertRaisesRegex(KeyError, "1"):
            del dct[1]

    def test_big(self):
        dct = concurrency.ConcurrentDict()
        for i in range(10000):
            dct[i] = i + 1
        for i in range(10000):
            self.assertEqual(dct[i], i + 1)
        for i in range(10000):
            dct[str(i)] = str(i * 2)
        for i in range(10000):
            self.assertEqual(dct[str(i)], str(i * 2))

    def test_threads(self):
        dct = concurrency.ConcurrentDict(37)
        lck = threading.Lock()

        def win():
            for i in range(1000):
                dct[i] = i + 1

        def wstr():
            for i in range(1000):
                dct[str(i)] = str(i * 2)

        def wdel():
            with lck:
                for i in range(1000):
                    dct[str(-(i + 1))] = str(i * 2)
                for i in range(1000):
                    del dct[str(-(i + 1))]

        threads = [
            threading.Thread(target=win),
            threading.Thread(target=wstr),
            threading.Thread(target=wdel),
        ]
        threads += [
            threading.Thread(target=win),
            threading.Thread(target=wstr),
            threading.Thread(target=wdel),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        for i in range(1000):
            self.assertEqual(dct[i], i + 1)
        for i in range(1000):
            self.assertEqual(dct[str(i)], str(i * 2))
        with self.assertRaisesRegex(KeyError, "-10"):
            del dct["-10"]

    def test_dundar(self):
        class Hasher:
            def __init__(self, value):
                self._value = value

            def __hash__(self):
                if self._value is None:
                    raise RuntimeError("Invalid Hasher")
                return self._value

        dct = concurrency.ConcurrentDict()
        illegal = Hasher(None)

        with self.assertRaisesRegex(RuntimeError, "Invalid Hasher"):
            dct[illegal]

        with self.assertRaises(RuntimeError):
            illegal in dct

        with self.assertRaisesRegex(RuntimeError, "Invalid Hasher"):
            dct[illegal] = 2

        with self.assertRaisesRegex(RuntimeError, "Invalid Hasher"):
            del dct[illegal]

        legal = Hasher(-1)
        dct[legal] = "dog"
        self.assertTrue(legal in dct)
        self.assertEqual(dct[legal], "dog")
        del dct[legal]
        self.assertFalse(legal in dct)

    def test_as_dict(self):
        cdct = concurrency.ConcurrentDict()
        for i in range(1024):
            cdct[i] = -i
        dct = cdct.as_dict()
        self.assertIs(type(dct), dict)
        for i in range(1024):
            self.assertEqual(dct[i], -i)

    def test_len(self):
        dct = concurrency.ConcurrentDict()
        self.assertEqual(len(dct), 0)
        dct[1] = "a"
        self.assertEqual(len(dct), 1)
        dct[2] = "b"
        dct[3] = "c"
        self.assertEqual(len(dct), 3)
        del dct[2]
        self.assertEqual(len(dct), 2)


class TestConcurrentDictGC(unittest.TestCase):
    def setUp(self):
        gc.collect()

    def test_simple_gc_weakref(self):
        d = concurrency.ConcurrentDict()
        d["key"] = "value"
        ref = weakref.ref(d)
        del d
        gc.collect()
        self.assertIsNone(ref())

    def test_cyclic_gc_weakref(self):
        d1 = concurrency.ConcurrentDict()
        d2 = concurrency.ConcurrentDict()
        d1["d2"] = d2
        d2["d1"] = d1
        ref1 = weakref.ref(d1)
        ref2 = weakref.ref(d2)
        del d1
        del d2
        gc.collect()
        self.assertIsNone(ref1())
        self.assertIsNone(ref2())

    def test_nested_cyclic_gc_weakref(self):
        d1 = concurrency.ConcurrentDict()
        d2 = concurrency.ConcurrentDict()
        d3 = concurrency.ConcurrentDict()
        d1["d2"] = d2
        d2["d3"] = d3
        d3["d1"] = d1
        ref1 = weakref.ref(d1)
        ref2 = weakref.ref(d2)
        ref3 = weakref.ref(d3)
        del d1
        del d2
        del d3
        gc.collect()
        self.assertIsNone(ref1())
        self.assertIsNone(ref2())
        self.assertIsNone(ref3())

    def test_self_referential_gc_weakref(self):
        d = concurrency.ConcurrentDict()
        d["self"] = d
        ref = weakref.ref(d)
        del d
        gc.collect()
        self.assertIsNone(ref())

    def test_gc_garbage_list(self):
        d = concurrency.ConcurrentDict()
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])
        d = concurrency.ConcurrentDict()
        d["self"] = d
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])
        d1 = concurrency.ConcurrentDict()
        d2 = concurrency.ConcurrentDict()
        d1["d2"] = d2
        d2["d1"] = d1
        del d1
        del d2
        gc.collect()
        self.assertTrue(gc.garbage == [])
        d = concurrency.ConcurrentDict()
        d["list"] = [d]
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])


class TestAtomicInt64(unittest.TestCase):
    def test_smoke(self):
        ai = concurrency.AtomicInt64()
        self.assertEqual(ai.get(), 0)
        ai.set(10)
        self.assertEqual(ai.get(), 10)

    def test_add(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(ai + 10, 20)

    def test_sub(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(ai - 5, 5)

    def test_mul(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(ai * 5, 50)

    def test_div(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(ai // 2, 5)

    def test_iadd(self):
        ai = concurrency.AtomicInt64(10)
        ai += 10
        self.assertEqual(ai.get(), 20)

    def test_isub(self):
        ai = concurrency.AtomicInt64(10)
        ai -= 5
        self.assertEqual(ai.get(), 5)

    def test_imul(self):
        ai = concurrency.AtomicInt64(10)
        ai *= 5
        self.assertEqual(ai.get(), 50)

    def test_idiv(self):
        ai = concurrency.AtomicInt64(10)
        ai //= 2
        self.assertEqual(ai.get(), 5)

    def test_bool(self):
        ai = concurrency.AtomicInt64(0)
        self.assertFalse(ai)
        ai.set(10)
        self.assertTrue(ai)

    def test_or(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(ai | 5, 15)

    def test_xor(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(ai ^ 5, 15)

    def test_and(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(ai & 5, 0)

    def test_ior(self):
        ai = concurrency.AtomicInt64(10)
        ai |= 5
        self.assertEqual(ai, 15)

    def test_ixor(self):
        ai = concurrency.AtomicInt64(10)
        ai ^= 5
        self.assertEqual(ai, 15)

    def test_iand(self):
        ai = concurrency.AtomicInt64(10)
        ai &= 5
        self.assertEqual(ai, 0)

    def test_not(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(~ai, -11)

    def test_incr(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(ai.incr(), 11)

    def test_decr(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(ai.decr(), 9)

    def test_compare(self):
        ai = concurrency.AtomicInt64()
        self.assertGreater(1, ai)
        self.assertLess(-1, ai)
        self.assertEqual(0, ai)
        self.assertTrue(concurrency.AtomicInt64(2) > 1)

    def test_threads(self):
        ai = concurrency.AtomicInt64(0)

        def worker(n):
            for _ in range(n):
                ai.incr()

        threads = [threading.Thread(target=worker, args=(1000,)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(ai.get(), 10000)

    def test_threads_set(self):
        ai = concurrency.AtomicInt64(0)

        def worker(n):
            ai.set(n)

        threads = [threading.Thread(target=worker, args=(10,)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(ai.get(), 10)

    def test_format(self):
        ai = concurrency.AtomicInt64(10)
        self.assertEqual(f"{ai:x}", "a")
        self.assertEqual(f"{ai:b}", "1010")
        self.assertEqual(f"{ai:o}", "12")
        self.assertEqual(f"{ai:d}", "10")


class BreakingDict(dict):
    def __setitem__(self, key, value):
        raise RuntimeError("Cannot assign to this dictionary")

    def __contains__(self, key):
        return key in self


class TestConcurrentQueue(unittest.TestCase):
    def _get_queue(self):
        return concurrency.ConcurrentQueue()

    def test_smoke(self):
        q = self._get_queue()
        q.push(10)
        self.assertEqual(q.pop(), 10)

    def test_multiple_push(self):
        q = self._get_queue()
        for i in range(10):
            q.push(i)
        for i in range(10):
            self.assertEqual(q.pop(), i)

    def test_multiple_threads(self):
        q = self._get_queue()

        def worker(n):
            for i in range(n):
                q.push(i)

        threads = [threading.Thread(target=worker, args=(10,)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for _ in range(100):
            x = q.pop()
            self.assertIn(x, list(range(10)))

    def test_pop_timeout(self):
        q = self._get_queue()

        def worker():
            q.push(10)

        t = threading.Thread(target=worker)
        t.start()
        self.assertEqual(q.pop(), 10)
        t.join()

    def test_queue_failure(self):
        q = self._get_queue()

        def worker():
            q._dict = BreakingDict()
            try:
                q.push(None)
            except Exception:
                pass

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        with self.assertRaises(RuntimeError):
            q.pop()

    def test_pop_local(self):
        q = self._get_queue()
        q.push(10)
        wrapper = q.pop_local()
        self.assertEqual(wrapper, 10)
        self.assertEqual(type(wrapper), local.LocalWrapper)

    def test_empty_queue(self):
        q = self._get_queue()

        def worker():
            time.sleep(0.1)
            q.push(10)

        for _ in range(5):
            t = threading.Thread(target=worker)
            t.start()
            self.assertEqual(q.pop(), 10)

    def test_pop(self):
        q = self._get_queue()

        def worker():
            time.sleep(0.1)
            q.push(10)

        t = threading.Thread(target=worker)
        t.start()
        self.assertEqual(q.pop(), 10)
        t.join()

    def test_pop_timeout_sleep(self):
        q = self._get_queue()
        f = concurrency.AtomicFlag(False)

        def worker():
            f.set(True)
            time.sleep(0.1)
            q.push(10)

        t = threading.Thread(target=worker)
        t.start()
        while not f:
            pass
        self.assertEqual(q.pop(timeout=1), 10)
        t.join()

    def test_pop_timeout_expires(self):
        q = self._get_queue()
        f = concurrency.AtomicFlag(False)

        def worker():
            f.set(True)
            time.sleep(0.5)
            q.push(10)

        t = threading.Thread(target=worker)
        t.start()
        while not f:
            pass
        with self.assertRaises(queue.Empty):
            q.pop(timeout=0.1)
        t.join()

    def test_pop_waiting(self):
        q = self._get_queue()

        def worker():
            time.sleep(0.1)
            q.push(10)

        t = threading.Thread(target=worker)
        t.start()
        self.assertEqual(q.pop(), 10)
        t.join()

    def test_shutdown(self):
        q = self._get_queue()
        q.push(10)
        q.shutdown()
        with self.assertRaises(concurrency.ShutDown):
            q.push(20)
        self.assertEqual(q.pop(), 10)
        with self.assertRaises(concurrency.ShutDown):
            q.pop()

    def test_shutdown_immediate(self):
        q = self._get_queue()
        q.push(10)
        q.shutdown(immediate=True)
        with self.assertRaises(concurrency.ShutDown):
            q.push(20)
        with self.assertRaises(concurrency.ShutDown):
            q.pop()

    def test_shutdown_empty(self):
        q = self._get_queue()

        def worker():
            time.sleep(0.1)
            q.shutdown()

        t = threading.Thread(target=worker)
        t.start()
        with self.assertRaises(concurrency.ShutDown):
            q.pop()
        t.join()

    def test_size_empty(self):
        q = self._get_queue()
        self.assertEqual(q.size(), 0)
        self.assertTrue(q.empty())
        q.push(35)
        self.assertEqual(q.size(), 1)
        self.assertFalse(q.empty())
        self.assertEqual(q.pop(), 35)
        self.assertEqual(q.size(), 0)
        self.assertTrue(q.empty())

    def test_timeout_placeholdr(self):
        q = self._get_queue()
        t0 = time.monotonic()
        with self.assertRaises(queue.Empty):
            q.pop(timeout=0.1)
        t1 = time.monotonic()
        self.assertGreater(t1 - t0, 0.1)
        self.assertEqual(q.size(), 0)
        q.push(35)
        self.assertEqual(q.size(), 1)
        self.assertEqual(q.pop(), 35)

    def test_timeout_many(self):
        q = self._get_queue()
        p_count = concurrency.AtomicInt64()
        p_vals = concurrency.ConcurrentDict()
        count = 128
        nthread = 4
        errors = []

        def worker():
            while p_count < count:
                try:
                    v = q.pop(timeout=0.01)
                    k = p_count.incr()
                    p_vals[k - 1] = v
                except Exception as e:
                    if type(e) is not concurrency.Empty:
                        errors.append(e)
                        break

        threads = [threading.Thread(target=worker) for _ in range(nthread)]
        for t in threads:
            t.start()

        time.sleep(0.1)
        for v in range(count):
            q.push(v)
            time.sleep(0.03)
            self.assertEqual(errors, [])

        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(int(p_count), count)
        s1 = set(range(count))
        s2 = {p_vals[v] for v in range(count)}
        self.assertEqual(s1, s2)


class TestConcurrentQueueLockFree(TestConcurrentQueue):
    def _get_queue(self):
        return concurrency.ConcurrentQueue(lock_free=True)


class TestStdConcurrentQueue(unittest.TestCase):
    def _get_queue(self, maxsize=0):
        return concurrency.StdConcurrentQueue(maxsize)

    def test_smoke(self):
        q = self._get_queue()
        q.put(10)
        self.assertEqual(q.get(), 10)

    def test_multiple_put(self):
        q = self._get_queue()
        for i in range(10):
            q.put(i)
        for i in range(10):
            self.assertEqual(q.get(), i)

    def test_multiple_threads(self):
        q = self._get_queue()
        flag = concurrency.AtomicFlag(False)

        def worker(n):
            flag.set(True)
            for i in range(n):
                q.put(i)

        threads = [threading.Thread(target=worker, args=(10,)) for _ in range(10)]
        for t in threads:
            t.start()
        while not flag:
            pass
        for t in threads:
            t.join()
        for _ in range(100):
            x = q.get()
            self.assertIn(x, list(range(10)))

    def test_get_timeout(self):
        q = self._get_queue()
        flag = concurrency.AtomicFlag(False)

        def worker():
            flag.set(True)
            time.sleep(0.1)
            q.put(10)

        t = threading.Thread(target=worker)
        t.start()
        while not flag:
            pass
        self.assertEqual(q.get(timeout=1), 10)
        t.join()

    def test_get_timeout_expires(self):
        q = self._get_queue()
        flag = concurrency.AtomicFlag(False)

        def worker():
            flag.set(True)
            time.sleep(0.5)
            q.put(10)

        t = threading.Thread(target=worker)
        t.start()
        while not flag:
            pass
        with self.assertRaises(queue.Empty):
            q.get(timeout=0.1)
        t.join()

    def test_get_waiting(self):
        q = self._get_queue()
        flag = concurrency.AtomicFlag(False)

        def worker():
            flag.set(True)
            time.sleep(0.1)
            q.put(10)

        t = threading.Thread(target=worker)
        t.start()
        while not flag:
            pass
        self.assertEqual(q.get(), 10)
        t.join()

    def test_put_nowait(self):
        q = self._get_queue(maxsize=1)
        q.put_nowait(10)
        with self.assertRaises(queue.Full):
            q.put_nowait(20)

    def test_get_nowait(self):
        q = self._get_queue()
        q.put(10)
        self.assertEqual(q.get_nowait(), 10)
        with self.assertRaises(queue.Empty):
            q.get_nowait()

    def test_empty_queue(self):
        q = self._get_queue()
        flag = concurrency.AtomicFlag(False)

        def worker():
            flag.set(True)
            time.sleep(0.1)
            q.put(10)

        for _ in range(5):
            t = threading.Thread(target=worker)
            t.start()
            while not flag:
                pass
            self.assertEqual(q.get(), 10)

    def test_qsize(self):
        q = self._get_queue()
        self.assertEqual(q.qsize(), 0)
        q.put(10)
        self.assertEqual(q.qsize(), 1)
        q.get()
        self.assertEqual(q.qsize(), 0)

    def test_full(self):
        q = self._get_queue(maxsize=1)
        self.assertFalse(q.full())
        q.put(10)
        self.assertEqual(q.size(), 1)
        self.assertEqual(q._maxsize, 1)
        self.assertTrue(q.full())

    def test_task_done(self):
        q = self._get_queue()
        q.put(10)
        self.assertEqual(10, q.get())
        q.task_done()
        self.assertEqual(int(q._active_tasks), 0)
        q.join()

    def test_join(self):
        q = self._get_queue()

        def worker():
            q.get()
            q.task_done()

        ts = [threading.Thread(target=worker) for _ in range(10)]
        for t in ts:
            t.start()
            q.put(10)
        q.join()
        t.join()
        self.assertEqual(int(q._active_tasks), 0)

    def test_full_shutdown(self):
        q = self._get_queue(1)
        q.put(23)

        def worker():
            q.shutdown()
            q.get()

        t = threading.Thread(target=worker)
        t.start()
        with self.assertRaises(concurrency.ShutDown):
            q.put(32)


class TestConcurrentDeque(unittest.TestCase):
    class RichComparisonFailure:
        def rich_comparison_failure(self, other):
            raise RuntimeError("failure")

        __lt__ = rich_comparison_failure
        __le__ = rich_comparison_failure
        __eq__ = rich_comparison_failure
        __ne__ = rich_comparison_failure
        __gt__ = rich_comparison_failure
        __ge__ = rich_comparison_failure

    def test_smoke(self):
        d = concurrency.ConcurrentDeque[int]()
        d.append(10)

        self.assertEqual(d.pop(), 10)

    def test_appends(self):
        d = concurrency.ConcurrentDeque[int]()
        for i in range(10):
            if i % 2 == 0:
                d.appendleft(i)
            else:
                d.append(i)

        for i in range(9, 0, -1):
            if i % 2 == 0:
                self.assertEqual(d.popleft(), i)
            else:
                self.assertEqual(d.pop(), i)

    def test_appends_concurrency(self):
        n_workers = 10
        n_numbers = 100

        d = concurrency.ConcurrentDeque[int]()
        b = threading.Barrier(n_workers, timeout=1)

        def worker():
            b.wait()
            for i in range(n_numbers):
                time.sleep(0.001)  # attempt to get interleaved appends
                if i % 2 == 0:
                    d.appendleft(i)
                else:
                    d.append(i)

        threads = [threading.Thread(target=worker) for _ in range(n_workers)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(n_workers * n_numbers):
            if i % 2 == 0:
                self.assertIn(d.popleft(), list(range(0, n_numbers, 2)))
            else:
                self.assertIn(d.pop(), list(range(1, n_numbers, 2)))

    def test_clear(self):
        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])
        d.clear()

        self.assertEqual(len(d), 0)

    def test_contains(self):
        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])
        self.assertTrue(1 in d)
        self.assertFalse(0 in d)

    def test_contains_failure(self):
        d = concurrency.ConcurrentDeque([self.RichComparisonFailure()])
        with self.assertRaises(RuntimeError):
            self.assertFalse(0 in d)

    def test_extend(self):
        d = concurrency.ConcurrentDeque[int]()
        d.extend([1, 2, 3])
        d.extend([4, 5])

        self.assertEqual(len(d), 5)
        self.assertEqual(d.pop(), 5)

    def test_extendleft(self):
        d = concurrency.ConcurrentDeque[int]()
        d.extendleft([5, 4])
        d.extendleft([3, 2, 1])

        self.assertEqual(len(d), 5)
        self.assertEqual(d.popleft(), 1)

    def test_item(self):
        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])

        self.assertEqual(d[0], 1)
        self.assertEqual(d[2], 3)
        self.assertEqual(d[4], 5)
        self.assertEqual(d[-1], 5)

        with self.assertRaises(IndexError):
            d[5]

    def test_iter(self):
        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])
        self.assertEqual(list(d), [1, 2, 3, 4, 5])

    def test_remove(self):
        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])
        d.remove(1)
        self.assertEqual(d.popleft(), 2)

        d.remove(5)
        self.assertEqual(d.pop(), 4)

        with self.assertRaises(ValueError):
            d.remove(1)

    def test_remove_failure(self):
        d = concurrency.ConcurrentDeque([self.RichComparisonFailure()])
        with self.assertRaises(RuntimeError):
            d.remove(1)

    def test_rich_comparison(self):
        d1 = concurrency.ConcurrentDeque[int]([])
        d2 = concurrency.ConcurrentDeque[int]([])
        self.assertEqual(d1, d2)  # [] == []

        d2.append(1)
        self.assertLess(d1, d2)  # [] < [1]
        self.assertNotEqual(d1, d2)  # [] != [1]

        d1.extend([1, 2])
        self.assertGreater(d1, d2)  # [1, 2] > [1]

        d2.append(2)
        self.assertLessEqual(d1, d2)  # [1, 2] <= [1, 2]
        self.assertGreaterEqual(d1, d2)  # [1, 2] >= [1, 2]

    def test_rotate(self):
        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])
        d.rotate(1)
        self.assertEqual(d.pop(), 4)

        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])
        d.rotate(-1)
        self.assertEqual(d.pop(), 1)

        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])
        d.rotate(0)
        self.assertEqual(d.pop(), 5)


class TestConcurrentDequeGC(unittest.TestCase):
    def setUp(self):
        gc.collect()

    def test_simple_gc_weakref(self):
        d = concurrency.ConcurrentDeque()

        d.append("value")
        ref = weakref.ref(d)

        del d
        gc.collect()

        self.assertIsNone(ref())

    def test_cyclic_gc_weakref(self):
        d1 = concurrency.ConcurrentDeque()
        d2 = concurrency.ConcurrentDeque()

        d1.append(d2)
        d2.append(d1)
        ref1 = weakref.ref(d1)
        ref2 = weakref.ref(d2)

        del d1
        del d2
        gc.collect()

        self.assertIsNone(ref1())
        self.assertIsNone(ref2())

    def test_nested_cyclic_gc_weakref(self):
        d1 = concurrency.ConcurrentDeque()
        d2 = concurrency.ConcurrentDeque()
        d3 = concurrency.ConcurrentDeque()

        d1.append(d2)
        d2.append(d3)
        d3.append(d1)
        ref1 = weakref.ref(d1)
        ref2 = weakref.ref(d2)
        ref3 = weakref.ref(d3)

        del d1
        del d2
        del d3
        gc.collect()

        self.assertIsNone(ref1())
        self.assertIsNone(ref2())
        self.assertIsNone(ref3())

    def test_self_referential_gc_weakref(self):
        d = concurrency.ConcurrentDeque()
        d.append(d)

        ref = weakref.ref(d)
        del d

        gc.collect()
        self.assertIsNone(ref())

    def test_gc_garbage_list(self):
        self.assertTrue(gc.garbage == [])

        d = concurrency.ConcurrentDeque()
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])

        d = concurrency.ConcurrentDeque()
        d.append(d)
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])

        d1 = concurrency.ConcurrentDeque()
        d2 = concurrency.ConcurrentDeque()
        d1.append(d2)
        d2.append(d1)
        del d1
        del d2
        gc.collect()
        self.assertTrue(gc.garbage == [])

        d = concurrency.ConcurrentDeque()
        d.append([d])
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])

    class _TestObject:
        pass

    def test_contains(self):
        d = concurrency.ConcurrentDeque()
        o = self._TestObject()
        ref = weakref.ref(o)

        d.append(o)
        self.assertTrue(o in d)
        del o

        d.pop()
        gc.collect()

        self.assertIsNone(ref())

    def test_contains_cycle(self):
        d1 = concurrency.ConcurrentDeque()
        d2 = concurrency.ConcurrentDeque()
        o = self._TestObject()

        d1.append(o)
        d1.append(d2)

        d2.append(o)
        d2.append(d1)

        ref1 = weakref.ref(d1)
        ref2 = weakref.ref(d2)

        self.assertTrue(o in d1)
        self.assertTrue(d2 in d1)

        self.assertTrue(o in d2)
        self.assertTrue(d1 in d2)

        del d1
        del d2
        gc.collect()

        self.assertIsNone(ref1())
        self.assertIsNone(ref2())

    def test_pop(self):
        d = concurrency.ConcurrentDeque([self._TestObject()])
        ref = weakref.ref(d[0])

        d.pop()
        gc.collect()

        self.assertIsNone(ref())

    def test_popleft(self):
        d = concurrency.ConcurrentDeque([self._TestObject()])
        ref = weakref.ref(d[0])

        d.popleft()
        gc.collect()

        self.assertIsNone(ref())

    def test_remove_head(self):
        d = concurrency.ConcurrentDeque([self._TestObject(), 1, 2, 3])
        ref = weakref.ref(d[0])

        d.remove(d[0])
        gc.collect()

        self.assertIsNone(ref())

    def test_remove_tail(self):
        d = concurrency.ConcurrentDeque([1, 2, 3, self._TestObject()])
        ref = weakref.ref(d[-1])

        d.remove(d[-1])
        gc.collect()

        self.assertIsNone(ref())

    def test_remove_inner(self):
        d = concurrency.ConcurrentDeque([1, 2, self._TestObject(), 3])
        ref = weakref.ref(d[2])

        d.remove(d[2])
        gc.collect()

        self.assertIsNone(ref())

    def test_rotate(self):
        d = concurrency.ConcurrentDeque([1, 2, 3, self._TestObject()])
        ref = weakref.ref(d[3])

        d.rotate(1)
        d.popleft()
        gc.collect()

        self.assertIsNone(ref())

    def test_rotate_cycle(self):
        d1 = concurrency.ConcurrentDeque([1, 2, 3])
        d2 = concurrency.ConcurrentDeque([4, 5, 6])

        d1.append(d2)
        d2.append(d1)
        ref1 = weakref.ref(d1)
        ref2 = weakref.ref(d2)

        d1.rotate(1)
        d2.rotate(1)

        del d1
        del d2
        gc.collect()

        self.assertIsNone(ref1())
        self.assertIsNone(ref2())


class TestConcurrentGatheringIterator(unittest.TestCase):
    def test_smoke(self):
        iterator = concurrency.ConcurrentGatheringIterator()
        iterator.insert(0, 10)
        self.assertEqual(list(iterator.iterator(0)), [10])

    def test_multiple_inserts(self):
        iterator = concurrency.ConcurrentGatheringIterator()
        for i in range(10):
            iterator.insert(i, i)
        self.assertEqual(list(iterator.iterator(9)), list(range(10)))

    def test_multiple_threads(self):
        iterator = concurrency.ConcurrentGatheringIterator()

        def worker(n, offset):
            for i in range(n):
                i += n * offset
                iterator.insert(i, i)

        for i in range(5):
            threads = [threading.Thread(target=worker, args=(10, i)) for i in range(10)]
            for t in reversed(threads):
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(list(iterator.iterator(99)), list(range(100)))

    def test_iterator_failure(self):
        iterator = concurrency.ConcurrentGatheringIterator()
        iterator._dict = BreakingDict()

        def worker():
            try:
                iterator.insert(0, None)
            except RuntimeError:
                # We want the insert to fail and set the internal flag to
                # indicate that a failure occurred. We don't want the error to
                # propagate further than this.
                pass

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        with self.assertRaises(RuntimeError):
            list(iterator.iterator(0))

    def test_iterator_local(self):
        iterator = concurrency.ConcurrentGatheringIterator()
        iterator.insert(0, 10)
        self.assertEqual(list(iterator.iterator_local(0)), [10])

    def test_empty_iterator(self):
        iterator = concurrency.ConcurrentGatheringIterator()

        def worker():
            time.sleep(0.1)
            iterator.insert(0, 10)

        for _ in range(5):
            t = threading.Thread(target=worker)
            t.start()
            self.assertEqual(list(iterator.iterator(0)), [10])

    def test_max_key(self):
        iterator = concurrency.ConcurrentGatheringIterator()
        for i in range(10):
            iterator.insert(i, i)
        self.assertEqual(list(iterator.iterator(5)), list(range(6)))

    def test_clear(self):
        iterator = concurrency.ConcurrentGatheringIterator()
        iterator.insert(0, 10)
        self.assertEqual(list(iterator.iterator(0, clear=True)), [10])


class TestAtomicReference(unittest.TestCase):
    def test_set_get(self):
        ref = concurrency.AtomicReference()
        ref.set("value")
        self.assertEqual(ref.get(), "value")

    def test_exchange(self):
        ref = concurrency.AtomicReference()
        ref.set("old_value")
        new_value = "new_value"
        exchanged_value = ref.exchange(new_value)
        self.assertEqual(exchanged_value, "old_value")
        self.assertEqual(ref.get(), new_value)

    def test_compare_exchange(self):
        ov = "old_value"
        mv = "middle_value"
        nv = "new_value"
        ref = concurrency.AtomicReference(ov)
        ref.set(mv)
        self.assertFalse(ref.compare_exchange(ov, nv))
        self.assertIs(ref.get(), mv)
        self.assertTrue(ref.compare_exchange(mv, nv))
        self.assertIs(ref.get(), nv)

    def test_concurrency_set(self):
        ref = concurrency.AtomicReference()

        def set_ref(value):
            ref.set(value)

        threads = []
        for i in range(10):
            t = threading.Thread(target=set_ref, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertIn(ref.get(), range(10))

    def test_concurrency_exchange(self):
        ref = concurrency.AtomicReference()
        ref.set(0)

        def exchange_ref(value):
            ref.exchange(value)

        threads = []
        for i in range(1, 11):
            t = threading.Thread(target=exchange_ref, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertIn(ref.get(), range(1, 11))

    def test_gc_acyclic(self):
        class Foo:
            pass

        for exchange in True, False:
            ref = concurrency.AtomicReference()
            obj = Foo()
            weak_obj = weakref.ref(obj)
            ref.set(obj)
            del obj
            if exchange:
                ref.exchange(None)
            else:
                ref.set(None)
            gc.collect()
            self.assertIsNone(weak_obj())

    def test_gc_cas(self):
        ov = "old_value"
        mv = "middle_value"
        nv = "new_value"
        ref = concurrency.AtomicReference()
        ref.set(ov)

        class Foo:
            pass

        obj = Foo()
        weak_obj = weakref.ref(obj)
        ref.compare_exchange(ov, obj)
        ref.compare_exchange(obj, mv)
        ref.compare_exchange(mv, obj)
        ref.compare_exchange(obj, nv)
        ref.compare_exchange(nv, obj)
        del obj
        ref.exchange(None)
        self.assertIsNone(weak_obj())

    def test_gc_cyclic(self):
        for delete_ref in True, False:
            ref = concurrency.AtomicReference()
            obj1 = concurrency.AtomicReference()
            obj2 = concurrency.AtomicReference()
            obj1.set(obj2)
            obj2.set(obj1)
            ref.set(obj1)
            del obj1
            del obj2
            gc.collect()
            self.assertIsNotNone(ref.get())

            if delete_ref:
                del ref
            else:
                ref.set(None)
            gc.collect()
            self.assertTrue(gc.garbage == [])

    def test_arg_count(self):
        x = concurrency.AtomicReference()
        self.assertIs(x.get(), None)
        y = concurrency.AtomicReference(x)
        self.assertIs(y.get(), x)
        with self.assertRaisesRegex(
            TypeError, r"AtomicReference\(\) takes zero or one argument$"
        ):
            concurrency.AtomicReference(x, y)


if __name__ == "__main__":
    unittest.main()
