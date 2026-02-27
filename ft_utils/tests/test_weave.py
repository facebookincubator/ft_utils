# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

# We deliberately do not import weave because we want to ensure the native code does this.
import sys
import threading
import unittest

import ft_utils
from ft_utils._test_weave import (  # @manual
    get_destructor_called_1,
    get_destructor_called_2,
    register_destructor_1,
    register_destructor_2,
    register_destructor_reset_1,
    reset,
    unregister_destructor_1,
    unregister_destructor_2,
)


@unittest.skipIf(sys.version_info < (3, 13), "Requires Python 3.13 or later")
class TestTLSManagement(unittest.TestCase):
    def setUp(self) -> None:
        ft_utils.ENABLE_EXPERIMENTAL = True
        reset()

    def test_register_destructor_1(self) -> None:
        def thread_func() -> None:
            register_destructor_1()
            pass

        t: threading.Thread = threading.Thread(target=thread_func)
        t.start()
        t.join()
        self.assertEqual(get_destructor_called_1(), 1)

    def test_unregister_destructor_1(self) -> None:
        register_destructor_1()
        self.assertEqual(1, unregister_destructor_1())

        def thread_func() -> None:
            register_destructor_1()
            unregister_destructor_1()
            pass

        t: threading.Thread = threading.Thread(target=thread_func)
        t.start()
        t.join()
        self.assertEqual(get_destructor_called_1(), 0)

    def test_register_destructor_2(self) -> None:
        def thread_func() -> None:
            register_destructor_2()
            pass

        t: threading.Thread = threading.Thread(target=thread_func)
        t.start()
        t.join()
        self.assertEqual(get_destructor_called_2(), 1)

    def test_unregister_destructor_2(self) -> None:
        register_destructor_2()
        register_destructor_2()
        unregister_destructor_2()
        unregister_destructor_2()
        self.assertEqual(0, unregister_destructor_2())

        register_destructor_2()
        self.assertEqual(1, unregister_destructor_2())
        self.assertEqual(0, unregister_destructor_1())

        def thread_func() -> None:
            register_destructor_2()
            unregister_destructor_2()
            pass

        t: threading.Thread = threading.Thread(target=thread_func)
        t.start()
        t.join()
        self.assertEqual(get_destructor_called_2(), 0)

    def test_unregister_destructor_12(self) -> None:
        register_destructor_1()
        register_destructor_2()
        unregister_destructor_2()
        unregister_destructor_1()
        self.assertEqual(0, unregister_destructor_2())

        def thread_func() -> None:
            register_destructor_1()
            register_destructor_2()
            register_destructor_1()
            register_destructor_2()
            unregister_destructor_1()
            pass

        t: threading.Thread = threading.Thread(target=thread_func)
        t.start()
        t.join()
        self.assertEqual(get_destructor_called_2(), 2)
        self.assertEqual(get_destructor_called_1(), 0)

    def test_unregister_destructor_sequence(self) -> None:
        def thread_func() -> None:
            register_destructor_1()
            register_destructor_1()
            register_destructor_reset_1()
            pass

        t: threading.Thread = threading.Thread(target=thread_func)
        t.start()
        t.join()
        self.assertEqual(get_destructor_called_1(), 100)

    def test_multiple_threads(self) -> None:
        num_threads: int = 10
        threads: list[threading.Thread] = []
        for _ in range(num_threads):

            def thread_func() -> None:
                register_destructor_1()
                pass

            t: threading.Thread = threading.Thread(target=thread_func)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(get_destructor_called_1(), num_threads)


if __name__ == "__main__":
    unittest.main()
