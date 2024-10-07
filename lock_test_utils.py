# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import signal
import sys
import threading
import time
import unittest
from collections.abc import Callable

from ft_utils.concurrent import AtomicFlag, AtomicReference


def run_interrupt_handling(
    self: unittest.TestCase,
    lock: object,
    acquire: Callable[[object], None],
    release: Callable[[object], None],
) -> None:
    """
    Run interrupt handling test.

    :param self: Test instance
    :param lock: Lock object
    :param acquire: Function to acquire the lock
    :param release: Function to release the lock
    """

    # Create atomic flags and references to synchronize between threads
    started_flag = AtomicFlag(False)
    signal_received_flag = AtomicFlag(False)
    main_thread_id_ref = AtomicReference()  # pyre-ignore
    handler_thread_id_ref = AtomicReference()  # pyre-ignore

    main_thread_id_ref.set(threading.get_ident())

    def signal_handler(signum: int, *args: object) -> None:  # pyre-ignore
        """
        Signal handler function.

        :param signum: Signal number
        :param args: Additional arguments
        """
        handler_thread_id_ref.set(threading.get_ident())
        signal_received_flag.set(True)

    if sys.platform == "win32":
        plat_signal = signal.SIGBREAK
    else:
        plat_signal = signal.SIGINT

    signal.signal(plat_signal, signal_handler)

    # Define a function to run in a separate thread
    def worker() -> None:  # pyre-ignore
        """
        Worker function to run in a separate thread.
        """
        acquire(lock)
        try:
            started_flag.set(True)
            signal.raise_signal(plat_signal)
        finally:
            release(lock)

    # Start the worker thread
    thread = threading.Thread(target=worker)
    thread.start()

    while not started_flag:
        time.sleep(0.001)

    try:
        acquire(lock)
        self.assertTrue(signal_received_flag)
    finally:
        release(lock)

    thread.join()

    self.assertTrue(signal_received_flag)
    self.assertEqual(main_thread_id_ref.get(), handler_thread_id_ref.get())
