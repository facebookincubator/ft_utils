# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import os
import threading
import time
from collections.abc import Iterator
from queue import Empty, Full

try:
    from queue import ShutDown  # type: ignore
except ImportError:

    class ShutDown(Exception):
        pass


from typing import Any, Optional

from ft_utils._concurrent import AtomicInt64, AtomicReference, ConcurrentDict

from ft_utils.local import LocalWrapper


class AtomicFlag:

    def __init__(self, value: bool) -> None:
        self._int64 = AtomicInt64(-1 if value else 0)

    def set(self, value: bool) -> None:
        self._int64.set(-1 if value else 0)

    def __bool__(self) -> bool:
        return bool(self._int64)


class ConcurrentGatheringIterator:
    """
    A concurrent gathering iterator which values from many
    threads and pass them to a reader in order based on integer key..

    The  keys are integers starting from 0 and increasing monotonically.
    Insertions can be out of order and from multiple threads.

    The reading iterator starts from key 0 and increments, checking for the existence of the key in the dictionary.
    If the key exists, it reads the value and deletes the key-value pair.
    The iterator exits when the key taken out of the dict is the maximum value.

    Args:
    scaling (Optional(int)): expected number of threads or cores accessing the structure.
    """

    def __init__(self, scaling: int | None = None) -> None:
        if scaling is not None:
            self._dict: ConcurrentDict[int, object] = ConcurrentDict(scaling)
        else:
            self._dict: ConcurrentDict[int, object] = ConcurrentDict()
        self._cond = threading.Condition()
        # We probably don't need an atomic flag but it
        # it is safe and clear to use one here.
        self._failed = AtomicFlag(False)

    def insert(self, key: int, value: Any) -> None:  # type: ignore
        """
        Inserts a key-value pair into the dictionary.

        Args:
        key (int): The key to insert.
        value (Any): The value associated with the key.
        """
        try:
            self._dict[key] = value
        except:
            self._failed.set(True)
            raise
        finally:
            with self._cond:
                self._cond.notify_all()

    def iterator(self, max_key: int, clear: bool = True) -> Iterator[Any]:  # type: ignore
        """
        Returns an iterator that reads and deletes key-value pairs from the dictionary in order.
        This will block if the next value is not available.
        If the inserter fails due to an exception then all iterators will fail with RuntimeError.

        Args:
        max_key (int): The maximum key value.
        clear (bool): Delete the key/value pair after reading

        Yields:
        Any: The value associated with the current key.
        """
        key = 0
        _dict = LocalWrapper(self._dict)
        _cond = LocalWrapper(self._cond)
        _failed = LocalWrapper(self._failed)
        while key <= max_key:
            try:
                value = _dict[key]
            except KeyError:
                # We check the key in the dict then wait - which efficient but could result
                # in the key being added before we wait. That would mean the notify would be
                # called before the wait and so we miss it. Setting a timeout on the wait
                # fixes this with introducing strict interlocking between producer and consumer
                # (which is the very thing we are trying to avoid).
                with _cond:
                    while key not in _dict:
                        self._cond.wait(0.01)
                        if _failed:
                            raise RuntimeError("Iterator insertion failed")
                value = _dict[key]
            if clear:
                del _dict[key]
            yield value
            key += 1

    def iterator_local(self, max_key: int, clear: bool = True) -> Iterator[Any]:  # type: ignore
        yield from (LocalWrapper(value) for value in self.iterator(max_key, clear))


class ConcurrentQueue:
    """
    A thread-safe queue implementation that allows concurrent access and modification.

    Note:
        ConcurrentQueue deliberately does not follow the same API as queue.Queue. To get a replacement
        for queue.Queue use StdConcurrentQueue.
    """

    _SHUTDOWN = 1
    _FAILED = 2
    _SHUT_NOW = 4

    def __init__(self, scaling: int | None = None, lock_free: bool = False) -> None:
        """
        Initializes a new instance of the ConcurrentQueue class.
        Args:
            scaling (int | None, optional): The initial parallelism of the queue. Defaults to None, ie system defined.
            lock_free (bool, optional): Whether the queue should use lock-free operations. Defaults to False.
        """
        if scaling is not None:
            self._dict: ConcurrentDict[int, object] = ConcurrentDict(scaling)
        else:
            self._dict: ConcurrentDict[int, object] = ConcurrentDict()
        self._cond = threading.Condition()
        self._flags = AtomicInt64(0)
        self._inkey = AtomicInt64(0)
        self._outkey = AtomicInt64(0)
        self._lock_free = lock_free

    def push(self, value: Any) -> None:  # type: ignore
        """
        Adds an element to the end of the queue.
        Args:
            value (Any): The element to add to the queue.
        Raises:
            Exception: If an error occurs while adding the element to the queue.
            ShutDown: If the instance is shutdown.
        """
        if self._flags & self._SHUTDOWN:
            raise ShutDown
        try:
            self._dict[self._inkey.incr()] = value
        except:
            self._flags |= self._FAILED
            raise
        finally:
            if not self._lock_free:
                with self._cond:
                    self._cond.notify_all()

    def size(self) -> int:
        """
        Gets the number of elements currently in the queue.
        Returns:
            Int: The number of elements in the queue.
        """
        return max(0, int(self._inkey) - int(self._outkey))

    def empty(self) -> bool:
        """
        Gets the number of elements currently in the queue.
        Returns:
            Int: The number of elements in the queue.
        """
        return self.size() == 0

    def shutdown(self, immediate: bool = False) -> None:
        """
        Initiates shutdown of the queue.
        Args:
            immediate (bool, optional): Whether to shut down the queue immediately. Defaults to False.
        Note:
            Shutting down the queue will prevent further elements from being added or removed.
        """
        # There is no good way to make the ordering of immediate shutdown deterministic and still
        # allow the queue to be truly concurrent. shutown immediate is therefpre 'as soon as possible'.
        self._flags |= self._SHUTDOWN
        if immediate:
            self._flags |= self._SHUT_NOW
        # If any pop is waiting then by definition the queue is empty so we need to let the pop waiters
        # wake up and exit.
        if not self._lock_free:
            with self._cond:
                self._cond.notify_all()

    def pop(self, timeout: float | None = None) -> Any:  # type: ignore
        """
        Removes and returns an element from the front of the queue.
        Args:
            timeout (float | None, optional): The maximum time to wait for an element to become available.
            Defaults to None.
        Returns:
            Any: The removed element.
        Raises:
            Empty: If the queue is empty and the timeout expires.
            ShutDown: If the queue is shutting down - i.e. shutdown() has been called.

        Note:
            Timeout can be 0 but this is not recommended; if you want non-blocking behaviour use StdConcurrentQueue.
        """
        next_key = self._outkey.incr()
        _flags = LocalWrapper(self._flags)
        _shutdown = self._SHUTDOWN
        _shut_now = self._SHUT_NOW
        _failed = self._FAILED

        if _flags & _shut_now:
            raise ShutDown
        if _flags & _failed:
            raise RuntimeError("Queue failed")

        _dict = LocalWrapper(self._dict)
        _in_key = LocalWrapper(self._inkey)
        _sleep = LocalWrapper(time.sleep)
        _now = LocalWrapper(time.monotonic)
        start = _now()

        # If we can reasonably expect the key to be in the queue then don't do any
        # further logic - just go get it.
        if _in_key < next_key:

            if self._flags & _shutdown:
                raise ShutDown

            if self._lock_free:
                if timeout is not None:
                    end_time = start + timeout
                else:
                    end_time = None
                # Yield for the first 50ms then start pausing 50ms per iteration
                # after that. Maybe we could make this configurable but that could just
                # cause confusion whilst this is a good value for most cases.
                pause_time = start + 0.05

                while _in_key < next_key:
                    it_now = _now()
                    if it_now > pause_time:
                        _sleep(0.05)
                    else:
                        _sleep(0)
                    if _flags & _shutdown:
                        raise ShutDown
                    if _flags & _failed:
                        raise RuntimeError("Queue failed")
                    if (end_time is not None) and end_time < it_now:
                        self._add_placeholder(next_key)
                        raise Empty
            else:
                _cond = LocalWrapper(self._cond)
                timed_out = False
                with _cond:
                    while _in_key < next_key:
                        if _flags & _shutdown:
                            raise ShutDown
                        if _flags & _failed:
                            raise RuntimeError("Queue failed")
                        if timeout is None:
                            _cond.wait()
                        elif timeout == 0.0 or not _cond.wait(timeout):
                            timed_out = True
                            break
                if timed_out:
                    self._add_placeholder(next_key)
                    raise Empty

        # At this point we can reasonably assume the key is in the queue.
        # There is a short race in push so if we hit it just wait. Using the atomics this way is
        # efficient for the general case with this slightly more complex logic (see _load_placeholder).
        countdown = 100
        while countdown:
            try:
                value = _dict[next_key]
                del _dict[next_key]
                # Now handle the case that this was a placeholder. We have safely acquired it
                # we can process getting the original.
                if type(value) is ConcurrentQueue._PlaceHolder:
                    return self._load_placeholder(value, timeout, start)
                return value
            except KeyError:
                countdown -= 1
                # Spinning on yield here can causes performance collapse in the scheduler, so if we don't get
                # a value quickly, just let other threads catch up.
                if countdown > 95:
                    _sleep(0)
                else:
                    _sleep(0.05)
        raise RuntimeError("Failed to acquire value in timely fashion")

    class _PlaceHolder:
        __slots__ = ("key",)

        def __init__(self, key: int) -> None:
            self.key = key

        def __repr__(self) -> str:
            return f"_PlaceHolder({self.key})"

    def _load_placeholder(self, holder: _PlaceHolder, timeout: float | None, start: float) -> Any:  # type: ignore
        # We simplify the logic so we just check if the key is in the dict and wait lock free if there is a timeout
        # or we are inherently lock free. The aim is to reduce any chance of complex interactions of the condition
        # and the use of place holders.
        next_key = holder.key
        _flags = LocalWrapper(self._flags)
        _shutdown = self._SHUTDOWN
        _failed = self._FAILED
        _dict = LocalWrapper(self._dict)
        _sleep = LocalWrapper(time.sleep)
        _now = LocalWrapper(time.monotonic)
        if timeout is not None:
            end_time = start + timeout
        else:
            end_time = None

        # Start the time based (rather than yield) pause based on when we started waiting not on when this method
        # was called.
        pause_time = start + 0.05
        while next_key not in _dict:
            if _flags & _shutdown:
                raise ShutDown
            if _flags & _failed:
                raise RuntimeError("Queue failed")

            it_now = _now()
            if (end_time is not None) and end_time < it_now:
                self._add_placeholder(next_key)
                raise Empty
            if it_now > pause_time:
                _sleep(0.05)
            else:
                _sleep(0)

        # The advantage of this less efficient logic is we know for sure that the key is in the dict here.
        value = _dict[next_key]
        del _dict[next_key]
        # In the case that are having huge chains of place holders to placeholders then the stack will blow out
        # which is probably a good guard against overloaded queues so we will leave this as recursive to check
        # for that situation and keep the logic simple.
        if type(value) is ConcurrentQueue._PlaceHolder:
            return self._load_placeholder(value, timeout, start)
        return value

    def _add_placeholder(self, key: int) -> None:
        self.push(ConcurrentQueue._PlaceHolder(key))

    def pop_local(self, timeout: float | None = None) -> LocalWrapper:
        """
        Removes and returns an element from the front of the queue, wrapped in a LocalWrapper.
        Args:
            timeout (float | None, optional): The maximum time to wait for an element to become available. Defaults to None.
        Returns:
            LocalWrapper: The removed element wrapped in a LocalWrapper.
        Raises:
            Empty: If the queue is empty the timeout expires.
            ShutDown: If the queue is shutting down - i.e. shutdown() has been called.

        See: pop()
        """
        return LocalWrapper(self.pop(timeout))


class StdConcurrentQueue(ConcurrentQueue):
    """
    A class which is a drop in replacement for queue.Queue and behaves as a lock free ConcurrentQueue but supports
    the features of queue.Queue (which ConcurrentQueue does not). These extra features may add some overhead to
    operation and so this Queue is only preferred when an exact replacement for queue.Queue is required.

    Also note that there might be subtle differences in the way sequencing behaves in a multi-threaded environment
    compared to queue.Queue simply because this is a (mainly) lock free algorithm.
    """

    def __init__(self, maxsize: int = 0) -> None:
        osc = os.cpu_count()
        if osc:
            super().__init__(scaling=max(1, osc // 2), lock_free=True)
        else:
            super().__init__(lock_free=True)

        self._maxsize: int = max(maxsize, 0)
        self._active_tasks = AtomicInt64(0)

    def qsize(self) -> int:
        return self.size()

    def get(self, block: bool = True, timeout: float | None = None) -> Any:  # type: ignore
        if block and timeout != 0.0:
            return self.pop(timeout=timeout)
        else:
            # Use this to attempt to avoid excessive placeholder creation.
            if self.size() > 0:
                return self.pop(timeout=0.0)
            else:
                raise Empty

    def full(self) -> bool:
        _maxsize = self._maxsize
        return bool(_maxsize and self.size() >= _maxsize)

    def put(self, item: Any, block: bool = True, timeout: float | None = None) -> None:  # type: ignore

        if block and self._maxsize and self.full():
            _flags = LocalWrapper(self._flags)
            _shutdown = self._SHUTDOWN
            _sleep = LocalWrapper(time.sleep)
            _now = LocalWrapper(time.monotonic)
            start = _now()
            if timeout is not None:
                end_time = start + timeout
            else:
                end_time = None
            pause_time = start + 0.05
            while self.full():
                it_time = _now()
                if _flags & _shutdown:
                    raise ShutDown
                if end_time is not None and it_time > end_time:
                    raise Full
                if it_time < pause_time:
                    _sleep(0)
                else:
                    _sleep(0.05)
        else:
            if self.full():
                raise Full

        self.push(item)
        # The push succeeded so we can do this here.
        self._active_tasks.incr()

    def put_nowait(self, item: Any) -> None:  # type: ignore
        return self.put(item, block=False)

    def get_nowait(self) -> Any:  # type: ignore
        return self.get(block=False)

    def task_done(self) -> None:
        self._active_tasks.decr()

    def join(self) -> None:
        _sleep = LocalWrapper(time.sleep)
        _now = LocalWrapper(time.monotonic)
        _flags = LocalWrapper(self._flags)
        _shut_now = self._SHUT_NOW
        _active_tasks = LocalWrapper(self._active_tasks)
        start = _now()
        pause_time = start + 0.05
        while _active_tasks and not (_flags & _shut_now):
            if _now() < pause_time:
                _sleep(0)
            else:
                _sleep(0.05)
