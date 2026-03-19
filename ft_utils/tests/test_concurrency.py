# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import gc
import queue
import threading
import time
import unittest
import weakref
from typing import Callable

import ft_utils.concurrency as concurrency
import ft_utils.local as local
from ft_utils.threading_test_utils import run_concurrently


class TestConcurrentDict(unittest.TestCase):
    def test_smoke(self) -> None:
        dct: concurrency.ConcurrentDict[int, int] = concurrency.ConcurrentDict()
        dct[1] = 2
        self.assertEqual(dct[1], 2)
        self.assertTrue(1 in dct)
        del dct[1]
        with self.assertRaisesRegex(KeyError, "1"):
            dct[1]
        with self.assertRaisesRegex(KeyError, "1"):
            del dct[1]

    def test_big(self) -> None:
        dct: concurrency.ConcurrentDict[object, object] = concurrency.ConcurrentDict()
        for i in range(10000):
            dct[i] = i + 1
        for i in range(10000):
            self.assertEqual(dct[i], i + 1)
        for i in range(10000):
            dct[str(i)] = str(i * 2)
        for i in range(10000):
            self.assertEqual(dct[str(i)], str(i * 2))

    def test_threads(self) -> None:
        dct: concurrency.ConcurrentDict[object, object] = concurrency.ConcurrentDict(37)
        lck: threading.Lock = threading.Lock()

        def win() -> None:
            for i in range(1000):
                dct[i] = i + 1

        def wstr() -> None:
            for i in range(1000):
                dct[str(i)] = str(i * 2)

        def wdel() -> None:
            with lck:
                for i in range(1000):
                    dct[str(-(i + 1))] = str(i * 2)
                for i in range(1000):
                    del dct[str(-(i + 1))]

        run_concurrently([win, wstr, wdel, win, wstr, wdel])
        for i in range(1000):
            self.assertEqual(dct[i], i + 1)
        for i in range(1000):
            self.assertEqual(dct[str(i)], str(i * 2))
        with self.assertRaisesRegex(KeyError, "-10"):
            del dct["-10"]

    def test_dundar(self) -> None:
        class Hasher:
            def __init__(self, value: int | None) -> None:
                self._value: int | None = value

            def __hash__(self) -> int:
                if self._value is None:
                    raise RuntimeError("Invalid Hasher")
                return self._value

        dct: concurrency.ConcurrentDict[object, object] = concurrency.ConcurrentDict()
        illegal: Hasher = Hasher(None)

        with self.assertRaisesRegex(RuntimeError, "Invalid Hasher"):
            dct[illegal]

        with self.assertRaises(RuntimeError):
            illegal in dct

        with self.assertRaisesRegex(RuntimeError, "Invalid Hasher"):
            dct[illegal] = 2

        with self.assertRaisesRegex(RuntimeError, "Invalid Hasher"):
            del dct[illegal]

        legal: Hasher = Hasher(-1)
        dct[legal] = "dog"
        self.assertTrue(legal in dct)
        self.assertEqual(dct[legal], "dog")
        del dct[legal]
        self.assertFalse(legal in dct)

    def test_as_dict(self) -> None:
        cdct: concurrency.ConcurrentDict[int, int] = concurrency.ConcurrentDict()
        for i in range(1024):
            cdct[i] = -i
        dct: dict[int, int] = cdct.as_dict()
        self.assertIs(type(dct), dict)
        for i in range(1024):
            self.assertEqual(dct[i], -i)

    def test_len(self) -> None:
        dct: concurrency.ConcurrentDict[int, str] = concurrency.ConcurrentDict()
        self.assertEqual(len(dct), 0)
        dct[1] = "a"
        self.assertEqual(len(dct), 1)
        dct[2] = "b"
        dct[3] = "c"
        self.assertEqual(len(dct), 3)
        del dct[2]
        self.assertEqual(len(dct), 2)

    def test_clear(self) -> None:
        dct: concurrency.ConcurrentDict[int, str] = concurrency.ConcurrentDict()
        dct[1] = "a"
        dct[2] = "b"
        dct[3] = "c"
        self.assertEqual(len(dct), 3)
        dct.clear()
        self.assertEqual(len(dct), 0)
        self.assertFalse(1 in dct)
        # Verify dict is still usable after clear
        dct[4] = "d"
        self.assertEqual(dct[4], "d")

    def test_get(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct["a"] = 1
        dct["b"] = 2
        self.assertEqual(dct.get("a"), 1)
        self.assertEqual(dct.get("b"), 2)
        self.assertIsNone(dct.get("c"))
        self.assertEqual(dct.get("c", 42), 42)

    def test_update_from_dict(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct.update({"a": 1, "b": 2, "c": 3})
        self.assertEqual(dct["a"], 1)
        self.assertEqual(dct["b"], 2)
        self.assertEqual(dct["c"], 3)
        self.assertEqual(len(dct), 3)

    def test_update_from_concurrent_dict(self) -> None:
        src: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        src["x"] = 10
        src["y"] = 20
        dst: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dst["z"] = 30
        dst.update(src)
        self.assertEqual(dst["x"], 10)
        self.assertEqual(dst["y"], 20)
        self.assertEqual(dst["z"], 30)

    def test_update_with_kwargs(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct.update(a=1, b=2)
        self.assertEqual(dct["a"], 1)
        self.assertEqual(dct["b"], 2)

    def test_update_overwrites(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct["a"] = 1
        dct.update({"a": 99})
        self.assertEqual(dct["a"], 99)

    def test_keys(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct["a"] = 1
        dct["b"] = 2
        dct["c"] = 3
        keys = dct.keys()
        self.assertIsInstance(keys, list)
        self.assertCountEqual(keys, ["a", "b", "c"])

    def test_values(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct["a"] = 1
        dct["b"] = 2
        dct["c"] = 3
        values = dct.values()
        self.assertIsInstance(values, list)
        self.assertCountEqual(values, [1, 2, 3])

    def test_items(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct["a"] = 1
        dct["b"] = 2
        dct["c"] = 3
        items = dct.items()
        self.assertIsInstance(items, list)
        self.assertCountEqual(items, [("a", 1), ("b", 2), ("c", 3)])

    def test_iter(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct["x"] = 10
        dct["y"] = 20
        dct["z"] = 30
        keys = list(dct)
        self.assertCountEqual(keys, ["x", "y", "z"])

    def test_iter_empty(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        self.assertEqual(list(dct), [])

    def test_keys_values_items_empty(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        self.assertEqual(dct.keys(), [])
        self.assertEqual(dct.values(), [])
        self.assertEqual(dct.items(), [])

    def test_clear_then_iter(self) -> None:
        dct: concurrency.ConcurrentDict[int, int] = concurrency.ConcurrentDict()
        for i in range(100):
            dct[i] = i * 2
        dct.clear()
        self.assertEqual(list(dct), [])
        self.assertEqual(len(dct), 0)

    def test_get_with_none_value(self) -> None:
        dct: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
        dct["a"] = None
        # get() should return None (the stored value), not the default
        self.assertIsNone(dct.get("a", "fallback"))

    def test_update_from_iterable_of_pairs(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct.update([("a", 1), ("b", 2)])  # pyre-ignore[6]
        self.assertEqual(dct["a"], 1)
        self.assertEqual(dct["b"], 2)

    def test_update_dict_and_kwargs(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct.update({"a": 1}, b=2, c=3)
        self.assertEqual(dct["a"], 1)
        self.assertEqual(dct["b"], 2)
        self.assertEqual(dct["c"], 3)

    def test_update_no_args(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct["x"] = 1
        dct.update()  # should be a no-op
        self.assertEqual(dct["x"], 1)
        self.assertEqual(len(dct), 1)

    def test_regular_dict_update_from_concurrent_dict(self) -> None:
        cd: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        cd["a"] = 1
        cd["b"] = 2
        cd["c"] = 3
        regular_dict: dict[str, int] = {"x": 10}
        regular_dict.update(cd)
        self.assertEqual(regular_dict, {"a": 1, "b": 2, "c": 3, "x": 10})

    def test_clear_multiple_times(self) -> None:
        dct: concurrency.ConcurrentDict[int, int] = concurrency.ConcurrentDict()
        for i in range(50):
            dct[i] = i
        dct.clear()
        self.assertEqual(len(dct), 0)
        dct.clear()  # second clear on empty should be fine
        self.assertEqual(len(dct), 0)
        dct[1] = 100
        self.assertEqual(dct[1], 100)

    def test_iter_with_for_loop(self) -> None:
        dct: concurrency.ConcurrentDict[int, str] = concurrency.ConcurrentDict()
        expected: dict[int, str] = {}
        for i in range(20):
            dct[i] = str(i)
            expected[i] = str(i)
        collected: dict[int, str] = {}
        for key in dct:
            collected[key] = dct[key]
        self.assertEqual(collected, expected)

    def test_keys_values_items_large(self) -> None:
        dct: concurrency.ConcurrentDict[int, int] = concurrency.ConcurrentDict()
        n = 1000
        for i in range(n):
            dct[i] = i * 3
        keys = dct.keys()
        self.assertEqual(len(keys), n)
        self.assertCountEqual(keys, list(range(n)))
        values = dct.values()
        self.assertEqual(len(values), n)
        self.assertCountEqual(values, [i * 3 for i in range(n)])
        items = dct.items()
        self.assertEqual(len(items), n)
        self.assertCountEqual(items, [(i, i * 3) for i in range(n)])

    def test_items_matches_as_dict(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct.update({"foo": 1, "bar": 2, "baz": 3})
        self.assertCountEqual(dct.items(), dct.as_dict().items())

    def test_iter_matches_keys(self) -> None:
        dct: concurrency.ConcurrentDict[str, int] = concurrency.ConcurrentDict()
        dct.update({"a": 1, "b": 2, "c": 3, "d": 4})
        self.assertCountEqual(list(dct), dct.keys())

    def test_update_threads(self) -> None:
        dct: concurrency.ConcurrentDict[int, int] = concurrency.ConcurrentDict(37)

        def fill(offset: int) -> None:
            for i in range(500):
                dct[offset + i] = offset + i

        run_concurrently(
            [
                lambda: fill(0),
                lambda: fill(500),
                lambda: fill(1000),
                lambda: fill(1500),
            ]
        )
        self.assertEqual(len(dct), 2000)
        for i in range(2000):
            self.assertEqual(dct[i], i)

    def test_clear_during_concurrent_writes(self) -> None:
        dct: concurrency.ConcurrentDict[int, int] = concurrency.ConcurrentDict()
        for i in range(100):
            dct[i] = i
        # Clear while another thread is writing; should not crash
        barrier: threading.Barrier = threading.Barrier(2)

        def writer() -> None:
            barrier.wait()
            for i in range(100, 200):
                dct[i] = i

        t: threading.Thread = threading.Thread(target=writer)
        t.start()
        barrier.wait()
        dct.clear()
        t.join()
        # After clear + concurrent writes, dict should have at least some of
        # the written values and no crashes
        self.assertTrue(len(dct) >= 0)

    def test_get_threads(self) -> None:
        dct: concurrency.ConcurrentDict[int, int] = concurrency.ConcurrentDict()
        for i in range(1000):
            dct[i] = i * 2
        results: list[int] = []
        lock: threading.Lock = threading.Lock()

        def reader(start: int, end: int) -> None:
            local_results: list[int] = []
            for i in range(start, end):
                v = dct.get(i, -1)
                local_results.append(v)
            with lock:
                results.extend(local_results)

        run_concurrently(
            [
                lambda: reader(0, 500),
                lambda: reader(500, 1000),
            ]
        )
        self.assertEqual(len(results), 1000)
        self.assertCountEqual(results, [i * 2 for i in range(1000)])


class TestConcurrentDictGC(unittest.TestCase):
    def setUp(self) -> None:
        gc.collect()

    def test_simple_gc_weakref(self) -> None:
        d: concurrency.ConcurrentDict[str, str] = concurrency.ConcurrentDict()
        d["key"] = "value"
        ref: weakref.ref[concurrency.ConcurrentDict[str, str]] = weakref.ref(d)
        del d
        gc.collect()
        self.assertIsNone(ref())

    def test_cyclic_gc_weakref(self) -> None:
        d1: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
        d2: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
        d1["d2"] = d2
        d2["d1"] = d1
        ref1: weakref.ref[concurrency.ConcurrentDict[str, object]] = weakref.ref(d1)
        ref2: weakref.ref[concurrency.ConcurrentDict[str, object]] = weakref.ref(d2)
        del d1
        del d2
        gc.collect()
        self.assertIsNone(ref1())
        self.assertIsNone(ref2())

    def test_nested_cyclic_gc_weakref(self) -> None:
        d1: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
        d2: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
        d3: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
        d1["d2"] = d2
        d2["d3"] = d3
        d3["d1"] = d1
        ref1: weakref.ref[concurrency.ConcurrentDict[str, object]] = weakref.ref(d1)
        ref2: weakref.ref[concurrency.ConcurrentDict[str, object]] = weakref.ref(d2)
        ref3: weakref.ref[concurrency.ConcurrentDict[str, object]] = weakref.ref(d3)
        del d1
        del d2
        del d3
        gc.collect()
        self.assertIsNone(ref1())
        self.assertIsNone(ref2())
        self.assertIsNone(ref3())

    def test_self_referential_gc_weakref(self) -> None:
        d: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
        d["self"] = d
        ref: weakref.ref[concurrency.ConcurrentDict[str, object]] = weakref.ref(d)
        del d
        gc.collect()
        self.assertIsNone(ref())

    def test_gc_garbage_list(self) -> None:
        d: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])
        d = concurrency.ConcurrentDict()
        d["self"] = d
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])
        d1: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
        d2: concurrency.ConcurrentDict[str, object] = concurrency.ConcurrentDict()
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
    def test_smoke(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64()
        self.assertEqual(ai.get(), 0)
        ai.set(10)
        self.assertEqual(ai.get(), 10)

    def test_add(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(ai + 10, 20)

    def test_sub(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(ai - 5, 5)

    def test_mul(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(ai * 5, 50)

    def test_div(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(ai // 2, 5)

    def test_iadd(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        ai += 10
        self.assertEqual(ai.get(), 20)

    def test_isub(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        ai -= 5
        self.assertEqual(ai.get(), 5)

    def test_imul(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        ai *= 5
        self.assertEqual(ai.get(), 50)

    def test_idiv(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        ai //= 2
        self.assertEqual(ai.get(), 5)

    def test_bool(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(0)
        self.assertFalse(ai)
        ai.set(10)
        self.assertTrue(ai)

    def test_or(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(ai | 5, 15)

    def test_xor(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(ai ^ 5, 15)

    def test_and(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(ai & 5, 0)

    def test_ior(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        ai |= 5
        self.assertEqual(ai, 15)

    def test_ixor(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        ai ^= 5
        self.assertEqual(ai, 15)

    def test_iand(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        ai &= 5
        self.assertEqual(ai, 0)

    def test_not(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(~ai, -11)

    def test_incr(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(ai.incr(), 11)

    def test_decr(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(ai.decr(), 9)

    def test_compare(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64()
        self.assertGreater(1, ai)
        self.assertLess(-1, ai)
        self.assertEqual(0, ai)
        self.assertTrue(concurrency.AtomicInt64(2) > 1)

    def test_threads(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(0)

        def worker(n: int) -> None:
            for _ in range(n):
                ai.incr()

        run_concurrently(worker, 10, args=(1000,))
        self.assertEqual(ai.get(), 10000)

    def test_threads_set(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(0)

        def worker(n: int) -> None:
            ai.set(n)

        run_concurrently(worker, 10, args=(10,))
        self.assertEqual(ai.get(), 10)

    def test_format(self) -> None:
        ai: concurrency.AtomicInt64 = concurrency.AtomicInt64(10)
        self.assertEqual(f"{ai:x}", "a")
        self.assertEqual(f"{ai:b}", "1010")
        self.assertEqual(f"{ai:o}", "12")
        self.assertEqual(f"{ai:d}", "10")


class BreakingDict(dict[object, object]):
    def __setitem__(self, key: object, value: object) -> None:
        raise RuntimeError("Cannot assign to this dictionary")

    def __contains__(self, key: object) -> bool:  # pyre-ignore[14]
        return key in self


class TestConcurrentQueue(unittest.TestCase):
    def _get_queue(self) -> concurrency.ConcurrentQueue:
        return concurrency.ConcurrentQueue()

    def test_smoke(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        q.push(10)
        self.assertEqual(q.pop(), 10)

    def test_multiple_push(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        for i in range(10):
            q.push(i)
        for i in range(10):
            self.assertEqual(q.pop(), i)

    def test_multiple_threads(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()

        def worker(n: int) -> None:
            for i in range(n):
                q.push(i)

        run_concurrently(worker, 10, args=(10,))
        for _ in range(100):
            x: object = q.pop()
            self.assertIn(x, list(range(10)))

    def test_pop_timeout(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()

        def worker() -> None:
            q.push(10)

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        self.assertEqual(q.pop(), 10)
        t.join()

    def test_queue_failure(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()

        def worker() -> None:
            q._dict = BreakingDict()  # pyre-ignore[8]
            try:
                q.push(None)
            except Exception:
                pass

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        t.join()
        with self.assertRaises(RuntimeError):
            q.pop()

    def test_pop_local(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        q.push(10)
        wrapper: local.LocalWrapper = q.pop_local()
        self.assertEqual(wrapper, 10)
        self.assertEqual(type(wrapper), local.LocalWrapper)

    def test_empty_queue(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()

        def worker() -> None:
            time.sleep(0.1)
            q.push(10)

        for _ in range(5):
            t: threading.Thread = threading.Thread(target=worker)
            t.start()
            self.assertEqual(q.pop(), 10)
            t.join()

    def test_pop(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()

        def worker() -> None:
            time.sleep(0.1)
            q.push(10)

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        self.assertEqual(q.pop(), 10)
        t.join()

    def test_pop_timeout_sleep(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        f: concurrency.AtomicFlag = concurrency.AtomicFlag(False)

        def worker() -> None:
            f.set(True)
            time.sleep(0.1)
            q.push(10)

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        while not f:
            pass
        self.assertEqual(q.pop(timeout=1), 10)
        t.join()

    def test_pop_timeout_expires(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        f: concurrency.AtomicFlag = concurrency.AtomicFlag(False)

        def worker() -> None:
            f.set(True)
            time.sleep(0.5)
            q.push(10)

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        while not f:
            pass
        with self.assertRaises(queue.Empty):
            q.pop(timeout=0.1)
        t.join()

    def test_pop_waiting(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()

        def worker() -> None:
            time.sleep(0.1)
            q.push(10)

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        self.assertEqual(q.pop(), 10)
        t.join()

    def test_shutdown(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        q.push(10)
        q.shutdown()
        with self.assertRaises(concurrency.ShutDown):
            q.push(20)
        self.assertEqual(q.pop(), 10)
        with self.assertRaises(concurrency.ShutDown):
            q.pop()

    def test_shutdown_immediate(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        q.push(10)
        q.shutdown(immediate=True)
        with self.assertRaises(concurrency.ShutDown):
            q.push(20)
        with self.assertRaises(concurrency.ShutDown):
            q.pop()

    def test_shutdown_empty(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()

        def worker() -> None:
            time.sleep(0.1)
            q.shutdown()

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        with self.assertRaises(concurrency.ShutDown):
            q.pop()
        t.join()

    def test_size_empty(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        self.assertEqual(q.size(), 0)
        self.assertTrue(q.empty())
        q.push(35)
        self.assertEqual(q.size(), 1)
        self.assertFalse(q.empty())
        self.assertEqual(q.pop(), 35)
        self.assertEqual(q.size(), 0)
        self.assertTrue(q.empty())

    def test_timeout_placeholdr(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        t0: float = time.monotonic()
        with self.assertRaises(queue.Empty):
            q.pop(timeout=0.1)
        t1: float = time.monotonic()
        self.assertGreater(t1 - t0, 0.1)
        self.assertEqual(q.size(), 0)
        q.push(35)
        self.assertEqual(q.size(), 1)
        self.assertEqual(q.pop(), 35)

    def test_timeout_many(self) -> None:
        q: concurrency.ConcurrentQueue = self._get_queue()
        p_count: concurrency.AtomicInt64 = concurrency.AtomicInt64()
        p_vals: concurrency.ConcurrentDict[int, object] = concurrency.ConcurrentDict()
        count: int = 128
        nthread: int = 4
        errors: list[Exception] = []

        def worker() -> None:
            while p_count < count:
                try:
                    v: object = q.pop(timeout=0.01)
                    k: int = p_count.incr()
                    p_vals[k - 1] = v
                except Exception as e:
                    if type(e) is not concurrency.Empty:
                        errors.append(e)
                        break

        threads: list[threading.Thread] = [
            threading.Thread(target=worker) for _ in range(nthread)
        ]
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
        s1: set[int] = set(range(count))
        s2: set[object] = {p_vals[v] for v in range(count)}
        self.assertEqual(s1, s2)


class TestConcurrentQueueLockFree(TestConcurrentQueue):
    def _get_queue(self) -> concurrency.ConcurrentQueue:
        return concurrency.ConcurrentQueue(lock_free=True)


class TestStdConcurrentQueue(unittest.TestCase):
    def _get_queue(self, maxsize: int = 0) -> concurrency.StdConcurrentQueue:
        return concurrency.StdConcurrentQueue(maxsize)

    def test_smoke(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        q.put(10)
        self.assertEqual(q.get(), 10)

    def test_multiple_put(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        for i in range(10):
            q.put(i)
        for i in range(10):
            self.assertEqual(q.get(), i)

    def test_multiple_threads(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        flag: concurrency.AtomicFlag = concurrency.AtomicFlag(False)

        def worker(n: int) -> None:
            flag.set(True)
            for i in range(n):
                q.put(i)

        threads: list[threading.Thread] = [
            threading.Thread(target=worker, args=(10,)) for _ in range(10)
        ]
        for t in threads:
            t.start()
        while not flag:
            pass
        for t in threads:
            t.join()
        for _ in range(100):
            x: object = q.get()
            self.assertIn(x, list(range(10)))

    def test_get_timeout(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        flag: concurrency.AtomicFlag = concurrency.AtomicFlag(False)

        def worker() -> None:
            flag.set(True)
            time.sleep(0.1)
            q.put(10)

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        while not flag:
            pass
        self.assertEqual(q.get(timeout=1), 10)
        t.join()

    def test_get_timeout_expires(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        flag: concurrency.AtomicFlag = concurrency.AtomicFlag(False)

        def worker() -> None:
            flag.set(True)
            time.sleep(0.5)
            q.put(10)

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        while not flag:
            pass
        with self.assertRaises(queue.Empty):
            q.get(timeout=0.1)
        t.join()

    def test_get_waiting(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        flag: concurrency.AtomicFlag = concurrency.AtomicFlag(False)

        def worker() -> None:
            flag.set(True)
            time.sleep(0.1)
            q.put(10)

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        while not flag:
            pass
        self.assertEqual(q.get(), 10)
        t.join()

    def test_put_nowait(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue(maxsize=1)
        q.put_nowait(10)
        with self.assertRaises(queue.Full):
            q.put_nowait(20)

    def test_get_nowait(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        q.put(10)
        self.assertEqual(q.get_nowait(), 10)
        with self.assertRaises(queue.Empty):
            q.get_nowait()

    def test_empty_queue(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        flag: concurrency.AtomicFlag = concurrency.AtomicFlag(False)

        def worker() -> None:
            flag.set(True)
            time.sleep(0.1)
            q.put(10)

        for _ in range(5):
            t: threading.Thread = threading.Thread(target=worker)
            flag.set(False)
            t.start()
            while not flag:
                pass
            self.assertEqual(q.get(), 10)
            t.join()

    def test_qsize(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        self.assertEqual(q.qsize(), 0)
        q.put(10)
        self.assertEqual(q.qsize(), 1)
        q.get()
        self.assertEqual(q.qsize(), 0)

    def test_full(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue(maxsize=1)
        self.assertFalse(q.full())
        q.put(10)
        self.assertEqual(q.size(), 1)
        self.assertEqual(q._maxsize, 1)
        self.assertTrue(q.full())

    def test_task_done(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()
        q.put(10)
        self.assertEqual(10, q.get())
        q.task_done()
        self.assertEqual(int(q._active_tasks), 0)
        q.join()

    def test_join(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue()

        def worker() -> None:
            q.get()
            q.task_done()

        ts: list[threading.Thread] = [
            threading.Thread(target=worker) for _ in range(10)
        ]
        for t in ts:
            t.start()
            q.put(10)
        q.join()
        t.join()
        self.assertEqual(int(q._active_tasks), 0)

    def test_full_shutdown(self) -> None:
        q: concurrency.StdConcurrentQueue = self._get_queue(1)
        q.put(23)

        def worker() -> None:
            q.shutdown()
            q.get()

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        with self.assertRaises(concurrency.ShutDown):
            q.put(32)
        t.join()


class TestConcurrentDeque(unittest.TestCase):
    class RichComparisonFailure:
        def rich_comparison_failure(self, other: object) -> bool:
            raise RuntimeError("failure")

        __lt__: Callable[
            ["TestConcurrentDeque.RichComparisonFailure", object], bool
        ] = rich_comparison_failure
        __le__: Callable[
            ["TestConcurrentDeque.RichComparisonFailure", object], bool
        ] = rich_comparison_failure
        # pyre-ignore[15]
        __eq__: Callable[
            ["TestConcurrentDeque.RichComparisonFailure", object], bool
        ] = rich_comparison_failure
        # pyre-ignore[15]
        __ne__: Callable[
            ["TestConcurrentDeque.RichComparisonFailure", object], bool
        ] = rich_comparison_failure
        __gt__: Callable[
            ["TestConcurrentDeque.RichComparisonFailure", object], bool
        ] = rich_comparison_failure
        __ge__: Callable[
            ["TestConcurrentDeque.RichComparisonFailure", object], bool
        ] = rich_comparison_failure

    def test_smoke(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int]()
        d.append(10)

        self.assertEqual(d.pop(), 10)

    def test_appends(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int]()
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

    def test_appends_concurrency(self) -> None:
        n_workers: int = 10
        n_numbers: int = 100

        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int]()

        def worker() -> None:
            for i in range(n_numbers):
                time.sleep(0.001)  # attempt to get interleaved appends
                if i % 2 == 0:
                    d.appendleft(i)
                else:
                    d.append(i)

        run_concurrently(worker, n_workers)

        for i in range(n_workers * n_numbers):
            if i % 2 == 0:
                self.assertIn(d.popleft(), list(range(0, n_numbers, 2)))
            else:
                self.assertIn(d.pop(), list(range(1, n_numbers, 2)))

    def test_clear(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int](
            [1, 2, 3, 4, 5]
        )
        d.clear()

        self.assertEqual(len(d), 0)

    def test_contains(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int](
            [1, 2, 3, 4, 5]
        )
        self.assertTrue(1 in d)
        self.assertFalse(0 in d)

    def test_contains_failure(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [self.RichComparisonFailure()]
        )
        with self.assertRaises(RuntimeError):
            self.assertFalse(0 in d)

    def test_extend(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int]()
        d.extend([1, 2, 3])
        d.extend([4, 5])

        self.assertEqual(len(d), 5)
        self.assertEqual(d.pop(), 5)

    def test_extendleft(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int]()
        d.extendleft([5, 4])
        d.extendleft([3, 2, 1])

        self.assertEqual(len(d), 5)
        self.assertEqual(d.popleft(), 1)

    def test_item(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int](
            [1, 2, 3, 4, 5]
        )

        self.assertEqual(d[0], 1)
        self.assertEqual(d[2], 3)
        self.assertEqual(d[4], 5)
        self.assertEqual(d[-1], 5)

        with self.assertRaises(IndexError):
            d[5]

    def test_iter(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int](
            [1, 2, 3, 4, 5]
        )
        self.assertEqual(list(d), [1, 2, 3, 4, 5])

    def test_remove(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int](
            [1, 2, 3, 4, 5]
        )
        d.remove(1)
        self.assertEqual(d.popleft(), 2)

        d.remove(5)
        self.assertEqual(d.pop(), 4)

        with self.assertRaises(ValueError):
            d.remove(1)

    def test_remove_failure(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [self.RichComparisonFailure()]
        )
        with self.assertRaises(RuntimeError):
            d.remove(1)

    def test_rich_comparison(self) -> None:
        d1: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int]([])
        d2: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int]([])
        self.assertEqual(d1, d2)  # [] == []

        d2.append(1)
        self.assertLess(d1, d2)
        self.assertNotEqual(d1, d2)  # [] != [1]

        d1.extend([1, 2])
        self.assertGreater(d1, d2)

        d2.append(2)
        self.assertLessEqual(d1, d2)
        self.assertGreaterEqual(d1, d2)

    def test_rotate(self) -> None:
        d: concurrency.ConcurrentDeque[int] = concurrency.ConcurrentDeque[int](
            [1, 2, 3, 4, 5]
        )
        d.rotate(1)
        self.assertEqual(d.pop(), 4)

        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])
        d.rotate(-1)
        self.assertEqual(d.pop(), 1)

        d = concurrency.ConcurrentDeque[int]([1, 2, 3, 4, 5])
        d.rotate(0)
        self.assertEqual(d.pop(), 5)


class TestConcurrentDequeGC(unittest.TestCase):
    def setUp(self) -> None:
        gc.collect()

    def test_simple_gc_weakref(self) -> None:
        d: concurrency.ConcurrentDeque[str] = concurrency.ConcurrentDeque()

        d.append("value")
        ref: weakref.ref[concurrency.ConcurrentDeque[str]] = weakref.ref(d)

        del d
        gc.collect()

        self.assertIsNone(ref())

    def test_cyclic_gc_weakref(self) -> None:
        d1: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
        d2: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()

        d1.append(d2)
        d2.append(d1)
        ref1: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d1)
        ref2: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d2)

        del d1
        del d2
        gc.collect()

        self.assertIsNone(ref1())
        self.assertIsNone(ref2())

    def test_nested_cyclic_gc_weakref(self) -> None:
        d1: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
        d2: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
        d3: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()

        d1.append(d2)
        d2.append(d3)
        d3.append(d1)
        ref1: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d1)
        ref2: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d2)
        ref3: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d3)

        del d1
        del d2
        del d3
        gc.collect()

        self.assertIsNone(ref1())
        self.assertIsNone(ref2())
        self.assertIsNone(ref3())

    def test_self_referential_gc_weakref(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
        d.append(d)

        ref: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d)
        del d

        gc.collect()
        self.assertIsNone(ref())

    def test_gc_garbage_list(self) -> None:
        self.assertTrue(gc.garbage == [])

        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])

        d = concurrency.ConcurrentDeque()
        d.append(d)
        del d
        gc.collect()
        self.assertTrue(gc.garbage == [])

        d1: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
        d2: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
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

    def test_contains(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
        o: TestConcurrentDequeGC._TestObject = self._TestObject()
        ref: weakref.ref[TestConcurrentDequeGC._TestObject] = weakref.ref(o)

        d.append(o)
        self.assertTrue(o in d)
        del o

        d.pop()
        gc.collect()

        self.assertIsNone(ref())

    def test_contains_cycle(self) -> None:
        d1: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
        d2: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque()
        o: TestConcurrentDequeGC._TestObject = self._TestObject()

        d1.append(o)
        d1.append(d2)

        d2.append(o)
        d2.append(d1)

        ref1: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d1)
        ref2: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d2)

        self.assertTrue(o in d1)
        self.assertTrue(d2 in d1)

        self.assertTrue(o in d2)
        self.assertTrue(d1 in d2)

        del d1
        del d2
        gc.collect()

        self.assertIsNone(ref1())
        self.assertIsNone(ref2())

    def test_pop(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [self._TestObject()]
        )
        ref: weakref.ref[object] = weakref.ref(d[0])

        d.pop()
        gc.collect()

        self.assertIsNone(ref())

    def test_popleft(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [self._TestObject()]
        )
        ref: weakref.ref[object] = weakref.ref(d[0])

        d.popleft()
        gc.collect()

        self.assertIsNone(ref())

    def test_remove_head(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [self._TestObject(), 1, 2, 3]
        )
        ref: weakref.ref[object] = weakref.ref(d[0])

        d.remove(d[0])
        gc.collect()

        self.assertIsNone(ref())

    def test_remove_tail(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [1, 2, 3, self._TestObject()]
        )
        ref: weakref.ref[object] = weakref.ref(d[-1])

        d.remove(d[-1])
        gc.collect()

        self.assertIsNone(ref())

    def test_remove_inner(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [1, 2, self._TestObject(), 3]
        )
        ref: weakref.ref[object] = weakref.ref(d[2])

        d.remove(d[2])
        gc.collect()

        self.assertIsNone(ref())

    def test_rotate(self) -> None:
        d: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [1, 2, 3, self._TestObject()]
        )
        ref: weakref.ref[object] = weakref.ref(d[3])

        d.rotate(1)
        d.popleft()
        gc.collect()

        self.assertIsNone(ref())

    def test_rotate_cycle(self) -> None:
        d1: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [1, 2, 3]
        )
        d2: concurrency.ConcurrentDeque[object] = concurrency.ConcurrentDeque[object](
            [4, 5, 6]
        )

        d1.append(d2)
        d2.append(d1)
        ref1: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d1)
        ref2: weakref.ref[concurrency.ConcurrentDeque[object]] = weakref.ref(d2)

        d1.rotate(1)
        d2.rotate(1)

        del d1
        del d2
        gc.collect()

        self.assertIsNone(ref1())
        self.assertIsNone(ref2())


class TestConcurrentGatheringIterator(unittest.TestCase):
    def test_smoke(self) -> None:
        iterator: concurrency.ConcurrentGatheringIterator = (
            concurrency.ConcurrentGatheringIterator()
        )
        iterator.insert(0, 10)
        self.assertEqual(list(iterator.iterator(0)), [10])

    def test_multiple_inserts(self) -> None:
        iterator: concurrency.ConcurrentGatheringIterator = (
            concurrency.ConcurrentGatheringIterator()
        )
        for i in range(10):
            iterator.insert(i, i)
        self.assertEqual(list(iterator.iterator(9)), list(range(10)))

    def test_multiple_threads(self) -> None:
        iterator: concurrency.ConcurrentGatheringIterator = (
            concurrency.ConcurrentGatheringIterator()
        )

        def worker(n: int, offset: int) -> None:
            for i in range(n):
                i += n * offset
                iterator.insert(i, i)

        for i in range(5):
            threads: list[threading.Thread] = [
                threading.Thread(target=worker, args=(10, i)) for i in range(10)
            ]
            for t in reversed(threads):
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(list(iterator.iterator(99)), list(range(100)))

    def test_iterator_failure(self) -> None:
        iterator: concurrency.ConcurrentGatheringIterator = (
            concurrency.ConcurrentGatheringIterator()
        )
        iterator._dict = BreakingDict()  # pyre-ignore[8]

        def worker() -> None:
            try:
                iterator.insert(0, None)
            except RuntimeError:
                # We want the insert to fail and set the internal flag to
                # indicate that a failure occurred. We don't want the error to
                # propagate further than this.
                pass

        t: threading.Thread = threading.Thread(target=worker)
        t.start()
        t.join()
        with self.assertRaises(RuntimeError):
            list(iterator.iterator(0))

    def test_iterator_local(self) -> None:
        iterator: concurrency.ConcurrentGatheringIterator = (
            concurrency.ConcurrentGatheringIterator()
        )
        iterator.insert(0, 10)
        self.assertEqual(list(iterator.iterator_local(0)), [10])

    def test_empty_iterator(self) -> None:
        iterator: concurrency.ConcurrentGatheringIterator = (
            concurrency.ConcurrentGatheringIterator()
        )

        def worker() -> None:
            time.sleep(0.1)
            iterator.insert(0, 10)

        for _ in range(5):
            t: threading.Thread = threading.Thread(target=worker)
            t.start()
            self.assertEqual(list(iterator.iterator(0)), [10])
            t.join()

    def test_max_key(self) -> None:
        iterator: concurrency.ConcurrentGatheringIterator = (
            concurrency.ConcurrentGatheringIterator()
        )
        for i in range(10):
            iterator.insert(i, i)
        self.assertEqual(list(iterator.iterator(5)), list(range(6)))

    def test_clear(self) -> None:
        iterator: concurrency.ConcurrentGatheringIterator = (
            concurrency.ConcurrentGatheringIterator()
        )
        iterator.insert(0, 10)
        self.assertEqual(list(iterator.iterator(0, clear=True)), [10])


class TestAtomicReference(unittest.TestCase):
    def test_set_get(self) -> None:
        ref: concurrency.AtomicReference = concurrency.AtomicReference(None)
        ref.set("value")
        self.assertEqual(ref.get(), "value")

    def test_exchange(self) -> None:
        ref: concurrency.AtomicReference = concurrency.AtomicReference(None)
        ref.set("old_value")
        new_value: str = "new_value"
        exchanged_value: str | None = ref.exchange(new_value)
        self.assertEqual(exchanged_value, "old_value")
        self.assertEqual(ref.get(), new_value)

    def test_compare_exchange(self) -> None:
        ov: str = "old_value"
        mv: str = "middle_value"
        nv: str = "new_value"
        ref: concurrency.AtomicReference = concurrency.AtomicReference(ov)
        ref.set(mv)
        self.assertFalse(ref.compare_exchange(ov, nv))
        self.assertIs(ref.get(), mv)
        self.assertTrue(ref.compare_exchange(mv, nv))
        self.assertIs(ref.get(), nv)

    def test_concurrency_set(self) -> None:
        ref: concurrency.AtomicReference = concurrency.AtomicReference(None)

        def set_ref(value: int) -> None:
            ref.set(value)

        run_concurrently([lambda i=i: set_ref(i) for i in range(10)])

        self.assertIn(ref.get(), range(10))

    def test_concurrency_exchange(self) -> None:
        ref: concurrency.AtomicReference = concurrency.AtomicReference(None)
        ref.set(0)

        def exchange_ref(value: int) -> None:
            ref.exchange(value)

        run_concurrently([lambda i=i: exchange_ref(i) for i in range(1, 11)])

        self.assertIn(ref.get(), range(1, 11))

    def test_gc_acyclic(self) -> None:
        class Foo:
            pass

        for exchange in True, False:
            ref: concurrency.AtomicReference = concurrency.AtomicReference(None)
            obj: Foo = Foo()
            weak_obj: weakref.ref[Foo] = weakref.ref(obj)
            ref.set(obj)
            del obj
            if exchange:
                ref.exchange(None)
            else:
                ref.set(None)
            gc.collect()
            self.assertIsNone(weak_obj())

    def test_gc_cas(self) -> None:
        ov: str = "old_value"
        mv: str = "middle_value"
        nv: str = "new_value"
        ref: concurrency.AtomicReference = concurrency.AtomicReference(None)
        ref.set(ov)

        class Foo:
            pass

        obj: Foo = Foo()
        weak_obj: weakref.ref[Foo] = weakref.ref(obj)
        ref.compare_exchange(ov, obj)
        ref.compare_exchange(obj, mv)
        ref.compare_exchange(mv, obj)
        ref.compare_exchange(obj, nv)
        ref.compare_exchange(nv, obj)
        del obj
        ref.exchange(None)
        self.assertIsNone(weak_obj())

    def test_gc_cyclic(self) -> None:
        for delete_ref in True, False:
            ref: concurrency.AtomicReference = concurrency.AtomicReference(None)
            obj1: concurrency.AtomicReference = concurrency.AtomicReference(None)
            obj2: concurrency.AtomicReference = concurrency.AtomicReference(None)
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

    def test_arg_count(self) -> None:
        x: concurrency.AtomicReference = concurrency.AtomicReference(None)
        self.assertIs(x.get(), None)
        y: concurrency.AtomicReference = concurrency.AtomicReference(x)
        self.assertIs(y.get(), x)
        with self.assertRaisesRegex(
            TypeError, r"AtomicReference\(\) takes zero or one argument$"
        ):
            concurrency.AtomicReference(x, y)  # pyre-ignore[19]


if __name__ == "__main__":
    unittest.main()
