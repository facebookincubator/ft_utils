# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

from types import TracebackType
from typing import Optional, Type, Union

class IntervalLock:
    def __init__(self, interval: float = 0.005) -> None: ...
    def lock(self) -> None: ...
    def unlock(self) -> None: ...
    def poll(self) -> None: ...
    def cede(self) -> None: ...
    def locked(self) -> bool: ...
    def __enter__(self) -> "IntervalLock": ...
    def __exit__(
        self, *args: Optional[Union[Type[BaseException], Exception, TracebackType]]
    ) -> None: ...

class RWLock:
    def lock_read(self) -> None: ...
    def unlock_read(self) -> None: ...
    def lock_write(self) -> None: ...
    def unlock_write(self) -> None: ...
    def readers(self) -> int: ...
    def writer_waiting(self) -> bool: ...
    def writer_locked(self) -> bool: ...

class RWReadContext:
    def __init__(self, lock: RWLock) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(
        self, *args: Optional[Union[Type[BaseException], Exception, TracebackType]]
    ) -> bool: ...

class RWWriteContext:
    def __init__(self, lock: RWLock) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(
        self, *args: Optional[Union[Type[BaseException], Exception, TracebackType]]
    ) -> bool: ...
