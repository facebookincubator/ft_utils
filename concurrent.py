# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import threading
from typing import Any, Iterator, Optional

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

    def __init__(self, scaling: Optional[int] = None) -> None:
        if scaling is not None:
            self._dict: ConcurrentDict = ConcurrentDict(scaling)
        else:
            self._dict: ConcurrentDict = ConcurrentDict()
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
                    while not _dict.has(key):
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
    def __init__(self, scaling: Optional[int] = None) -> None:
        if scaling is not None:
            self._dict: ConcurrentDict = ConcurrentDict(scaling)
        else:
            self._dict: ConcurrentDict = ConcurrentDict()
        self._cond = threading.Condition()
        self._failed = AtomicFlag(False)
        self._inkey = AtomicInt64(0)
        self._outkey = AtomicInt64(0)

    def push(self, value: Any) -> None:  # type: ignore
        try:
            self._dict[self._inkey.incr()] = value
        except:
            self._failed.set(True)
            raise
        finally:
            with self._cond:
                self._cond.notify_all()

    def pop(self) -> Any:  # type: ignore
        next_key = self._outkey.incr()
        _dict = LocalWrapper(self._dict)
        _cond = LocalWrapper(self._cond)
        try:
            value = _dict[next_key]
        except KeyError:
            with _cond:
                while not _dict.has(next_key):
                    _cond.wait(0.01)
                    if self._failed:
                        raise RuntimeError("Queue failed")
            value = _dict[next_key]
        del _dict[next_key]
        return value

    def pop_local(self) -> LocalWrapper:
        return LocalWrapper(self.pop())
