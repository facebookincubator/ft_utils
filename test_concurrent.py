# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import gc
import queue
import threading
import time
import unittest
import weakref

import ft_utils.concurrent as concurrent
import ft_utils.local as local


class TestConcurrentDict(unittest.TestCase):
    def test_smoke(self):
        dct = concurrent.ConcurrentDict()
        dct[1] = 2
        self.assertEqual(dct[1], 2)
        self.assertTrue(1 in dct)
        del dct[1]
        with self.assertRaisesRegex(KeyError, "1"):
            dct[1]
        with self.assertRaisesRegex(KeyError, "1"):
            del dct[1]

    def test_big(self):
        dct = concurrent.ConcurrentDict()
        for i in range(10000):
            dct[i] = i + 1
        for i in range(10000):
            self.assertEqual(dct[i], i + 1)
        for i in range(10000):
            dct[str(i)] = str(i * 2)
        for i in range(10000):
            self.assertEqual(dct[str(i)], str(i * 2))

    def test_threads(self):
        dct = concurrent.ConcurrentDict(37)
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

        dct = concurrent.ConcurrentDict()
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
        cdct = concurrent.ConcurrentDict()
        for i in range(1024):
            cdct[i] = -i
        dct = cdct.as_dict()
        self.assertIs(type(dct), dict)
        for i in range(1024):
            self.assertEqual(dct[i], -i)


class TestConcurrentDictGC(unittest.TestCase):
    def setUp(self):
        gc.collect()

    def test_simple_gc_weakref(self):
        d = concurrent.ConcurrentDict()
        d["key"] = "value"
        ref = weakref.ref(d)
        del d
        gc.collect()
        self.assertIsNone(ref())

    def test_cyclic_gc_weakref(self):
        d1 = concurrent.ConcurrentDict()
        d2 = concurrent.ConcurrentDict()
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
        d1 = concurrent.ConcurrentDict()
        d2 = concurrent.ConcurrentDict()
        d3 = concurrent.ConcurrentDict()
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
        d = concurrent.ConcurrentDict()
        d["self"] = d
        ref = weakref.ref(d)
        del d
        gc.collect()
        self.assertIsNone(ref())

    def test_gc_garbage_list(self):
        d = concurrent.ConcurrentDict()
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])
        d = concurrent.ConcurrentDict()
        d["self"] = d
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])
        d1 = concurrent.ConcurrentDict()
        d2 = concurrent.ConcurrentDict()
        d1["d2"] = d2
        d2["d1"] = d1
        del d1
        del d2
        gc.collect()
        self.assertTrue(gc.garbage == [])
        d = concurrent.ConcurrentDict()
        d["list"] = [d]
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])


class TestAtomicInt64(unittest.TestCase):
    def test_smoke(self):
        ai = concurrent.AtomicInt64()
        self.assertEqual(ai.get(), 0)
        ai.set(10)
        self.assertEqual(ai.get(), 10)

    def test_add(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(ai + 10, 20)

    def test_sub(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(ai - 5, 5)

    def test_mul(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(ai * 5, 50)

    def test_div(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(ai // 2, 5)

    def test_iadd(self):
        ai = concurrent.AtomicInt64(10)
        ai += 10
        self.assertEqual(ai.get(), 20)

    def test_isub(self):
        ai = concurrent.AtomicInt64(10)
        ai -= 5
        self.assertEqual(ai.get(), 5)

    def test_imul(self):
        ai = concurrent.AtomicInt64(10)
        ai *= 5
        self.assertEqual(ai.get(), 50)

    def test_idiv(self):
        ai = concurrent.AtomicInt64(10)
        ai //= 2
        self.assertEqual(ai.get(), 5)

    def test_bool(self):
        ai = concurrent.AtomicInt64(0)
        self.assertFalse(ai)
        ai.set(10)
        self.assertTrue(ai)

    def test_or(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(ai | 5, 15)

    def test_xor(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(ai ^ 5, 15)

    def test_and(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(ai & 5, 0)

    def test_ior(self):
        ai = concurrent.AtomicInt64(10)
        ai |= 5
        self.assertEqual(ai, 15)

    def test_ixor(self):
        ai = concurrent.AtomicInt64(10)
        ai ^= 5
        self.assertEqual(ai, 15)

    def test_iand(self):
        ai = concurrent.AtomicInt64(10)
        ai &= 5
        self.assertEqual(ai, 0)

    def test_not(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(~ai, -11)

    def test_incr(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(ai.incr(), 11)

    def test_decr(self):
        ai = concurrent.AtomicInt64(10)
        self.assertEqual(ai.decr(), 9)

    def test_compare(self):
        ai = concurrent.AtomicInt64()
        self.assertGreater(1, ai)
        self.assertLess(-1, ai)
        self.assertEqual(0, ai)
        self.assertTrue(concurrent.AtomicInt64(2) > 1)

    def test_threads(self):
        ai = concurrent.AtomicInt64(0)

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
        ai = concurrent.AtomicInt64(0)

        def worker(n):
            ai.set(n)

        threads = [threading.Thread(target=worker, args=(10,)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(ai.get(), 10)

    def test_format(self):
        ai = concurrent.AtomicInt64(10)
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
        return concurrent.ConcurrentQueue()

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
        f = concurrent.AtomicFlag(False)

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
        f = concurrent.AtomicFlag(False)

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
        with self.assertRaises(concurrent.ShutDown):
            q.push(20)
        self.assertEqual(q.pop(), 10)
        with self.assertRaises(concurrent.ShutDown):
            q.pop()

    def test_shutdown_immediate(self):
        q = self._get_queue()
        q.push(10)
        q.shutdown(immediate=True)
        with self.assertRaises(concurrent.ShutDown):
            q.push(20)
        with self.assertRaises(concurrent.ShutDown):
            q.pop()

    def test_shutdown_empty(self):
        q = self._get_queue()

        def worker():
            time.sleep(0.1)
            q.shutdown()

        t = threading.Thread(target=worker)
        t.start()
        with self.assertRaises(concurrent.ShutDown):
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
        p_count = concurrent.AtomicInt64()
        p_vals = concurrent.ConcurrentDict()
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
                    if type(e) is not concurrent.Empty:
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
        return concurrent.ConcurrentQueue(lock_free=True)


class TestStdConcurrentQueue(unittest.TestCase):
    def _get_queue(self, maxsize=0):
        return concurrent.StdConcurrentQueue(maxsize)

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
        flag = concurrent.AtomicFlag(False)

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
        flag = concurrent.AtomicFlag(False)

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
        flag = concurrent.AtomicFlag(False)

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
        flag = concurrent.AtomicFlag(False)

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
        flag = concurrent.AtomicFlag(False)

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
        with self.assertRaises(concurrent.ShutDown):
            q.put(32)


class TestConcurrentGatheringIterator(unittest.TestCase):
    def test_smoke(self):
        iterator = concurrent.ConcurrentGatheringIterator()
        iterator.insert(0, 10)
        self.assertEqual(list(iterator.iterator(0)), [10])

    def test_multiple_inserts(self):
        iterator = concurrent.ConcurrentGatheringIterator()
        for i in range(10):
            iterator.insert(i, i)
        self.assertEqual(list(iterator.iterator(9)), list(range(10)))

    def test_multiple_threads(self):
        iterator = concurrent.ConcurrentGatheringIterator()

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
        iterator = concurrent.ConcurrentGatheringIterator()
        iterator._dict = BreakingDict()

        def worker():
            iterator.insert(0, None)

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        with self.assertRaises(RuntimeError):
            list(iterator.iterator(0))

    def test_iterator_local(self):
        iterator = concurrent.ConcurrentGatheringIterator()
        iterator.insert(0, 10)
        self.assertEqual(list(iterator.iterator_local(0)), [10])

    def test_empty_iterator(self):
        iterator = concurrent.ConcurrentGatheringIterator()

        def worker():
            time.sleep(0.1)
            iterator.insert(0, 10)

        for _ in range(5):
            t = threading.Thread(target=worker)
            t.start()
            self.assertEqual(list(iterator.iterator(0)), [10])

    def test_max_key(self):
        iterator = concurrent.ConcurrentGatheringIterator()
        for i in range(10):
            iterator.insert(i, i)
        self.assertEqual(list(iterator.iterator(5)), list(range(6)))

    def test_clear(self):
        iterator = concurrent.ConcurrentGatheringIterator()
        iterator.insert(0, 10)
        self.assertEqual(list(iterator.iterator(0, clear=True)), [10])


class TestAtomicReference(unittest.TestCase):
    def test_set_get(self):
        ref = concurrent.AtomicReference()
        ref.set("value")
        self.assertEqual(ref.get(), "value")

    def test_exchange(self):
        ref = concurrent.AtomicReference()
        ref.set("old_value")
        new_value = "new_value"
        exchanged_value = ref.exchange(new_value)
        self.assertEqual(exchanged_value, "old_value")
        self.assertEqual(ref.get(), new_value)

    def test_compare_exchange(self):
        ov = "old_value"
        mv = "middle_value"
        nv = "new_value"
        ref = concurrent.AtomicReference(ov)
        ref.set(mv)
        self.assertFalse(ref.compare_exchange(ov, nv))
        self.assertIs(ref.get(), mv)
        self.assertTrue(ref.compare_exchange(mv, nv))
        self.assertIs(ref.get(), nv)

    def test_concurrent_set(self):
        ref = concurrent.AtomicReference()

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

    def test_concurrent_exchange(self):
        ref = concurrent.AtomicReference()
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
            ref = concurrent.AtomicReference()
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
        ref = concurrent.AtomicReference()
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
            ref = concurrent.AtomicReference()
            obj1 = concurrent.AtomicReference()
            obj2 = concurrent.AtomicReference()
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
        x = concurrent.AtomicReference()
        self.assertIs(x.get(), None)
        y = concurrent.AtomicReference(x)
        self.assertIs(y.get(), x)
        with self.assertRaisesRegex(
            TypeError, r"AtomicReference\(\) takes zero or one argument$"
        ):
            concurrent.AtomicReference(x, y)


if __name__ == "__main__":
    unittest.main()
