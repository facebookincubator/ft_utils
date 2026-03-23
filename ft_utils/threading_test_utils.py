# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import contextlib
import threading
from collections.abc import Callable, Iterator, Sequence
from typing import Any


class _ExcInfo:
    exc_type: type[BaseException] | None = None
    exc_value: BaseException | None = None
    exc_traceback: Any = None


@contextlib.contextmanager
def _catch_threading_exception() -> Iterator[_ExcInfo]:
    """Context manager catching threading.Thread exception using
    threading.excepthook."""
    cm: _ExcInfo = _ExcInfo()
    old_hook = threading.excepthook

    def hook(args: threading.ExceptHookArgs) -> None:
        cm.exc_type = args.exc_type
        cm.exc_value = args.exc_value
        cm.exc_traceback = args.exc_traceback

    threading.excepthook = hook
    try:
        yield cm
    finally:
        threading.excepthook = old_hook


def _run_concurrently(
    worker_func: Callable[..., None] | list[Callable[..., None]],
    nthreads: int | None = None,
    args: tuple[object, ...] = (),
    kwargs: dict[str, object] | None = None,
) -> None:
    """Run worker function(s) concurrently in multiple threads.

    If ``worker_func`` is a single callable, it is replicated for all threads.
    If it is a list of callables, each callable is used for one thread
    (and ``nthreads`` defaults to ``len(worker_func)``).

    A ``threading.Barrier`` ensures all threads start executing simultaneously.
    Exceptions raised in worker threads are re-raised in the calling thread.
    """
    if kwargs is None:
        kwargs = {}

    funcs: list[Callable[..., None]]
    if isinstance(worker_func, list):
        funcs = worker_func
        if nthreads is None:
            nthreads = len(funcs)
        assert len(funcs) == nthreads
    else:
        assert nthreads is not None, "nthreads is required for a single callable"
        funcs = [worker_func] * nthreads

    barrier: threading.Barrier = threading.Barrier(nthreads)

    def wrapper_func(func: Callable[..., None], *a: object, **kw: object) -> None:
        barrier.wait()
        func(*a, **kw)

    with _catch_threading_exception() as cm:
        workers = [
            threading.Thread(target=wrapper_func, args=(func, *args), kwargs=kwargs)
            for func in funcs
        ]
        for w in workers:
            w.start()
        for w in workers:
            w.join()

        if cm.exc_value is not None:
            raise cm.exc_value


def run_concurrently(
    worker_func: Callable[..., None],
    nthreads: int,
    args: tuple[object, ...] = (),
    kwargs: dict[str, object] | None = None,
) -> None:
    """Run a single worker function concurrently in multiple threads.

    The function is replicated for all threads, each receiving the same
    ``args`` and ``kwargs``.

    A ``threading.Barrier`` ensures all threads start executing simultaneously.
    Exceptions raised in worker threads are re-raised in the calling thread.
    """
    _run_concurrently(worker_func, nthreads, args, kwargs)


def run_each_concurrently(
    funcs: Sequence[Callable[[], None]],
) -> None:
    """Run a list of callables concurrently, one per thread.

    Each callable is invoked with no arguments in its own thread.

    A ``threading.Barrier`` ensures all threads start executing simultaneously.
    Exceptions raised in worker threads are re-raised in the calling thread.
    """
    _run_concurrently(list(funcs))
