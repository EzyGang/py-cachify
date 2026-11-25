import asyncio
import threading
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any, TypeVar, cast


_R = TypeVar('_R')

# (id of a SingleFlight, key) pairs whose computation runs in the current context. A call for the same key from
# inside its own computation (recursion) runs directly: waiting for itself would never end.
_leading: ContextVar[frozenset[tuple[int, str]]] = ContextVar('pyc_single_flight_leading', default=frozenset())


class _SyncCall:
    __slots__ = ('done', 'error', 'ok', 'result')

    def __init__(self) -> None:
        self.done = threading.Event()
        self.ok = False
        self.result: Any = None
        self.error: Exception | None = None


def _consume_exception(task: 'asyncio.Task[Any]') -> None:
    # Keeps asyncio from logging "exception was never retrieved" when every caller was cancelled.
    _ = task.cancelled() or task.exception()


class SingleFlight:
    """
    Collapses concurrent calls for the same key inside one process into one computation.

    The first caller for a key computes, callers arriving while it runs wait for its result or exception,
    and the entry is dropped the moment the computation ends.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._calls: dict[str, _SyncCall] = {}
        self._tasks: dict[tuple[asyncio.AbstractEventLoop, str], asyncio.Task[Any]] = {}

    def run(self, key: str, func: Callable[[], _R]) -> _R:
        if (id(self), key) in _leading.get():
            return func()

        while True:
            with self._lock:
                call = self._calls.get(key)
                if call is None:
                    call = self._calls[key] = _SyncCall()
                    break

            _ = call.done.wait()
            if call.ok:
                return cast(_R, call.result)
            if call.error is not None:
                raise call.error
            # The computation ended with a BaseException aimed at its own thread
            # (KeyboardInterrupt, SystemExit): compute here instead.

        return self._lead(key, call, func)

    def _lead(self, key: str, call: _SyncCall, func: Callable[[], _R]) -> _R:
        token = _leading.set(_leading.get() | {(id(self), key)})
        try:
            res = func()
            call.result, call.ok = res, True
            return res
        except Exception as e:
            call.error = e
            raise
        finally:
            _leading.reset(token)
            with self._lock:
                del self._calls[key]
            call.done.set()

    async def arun(self, key: str, func: Callable[[], Awaitable[_R]]) -> _R:
        if (id(self), key) in _leading.get():
            return await func()

        loop = asyncio.get_running_loop()
        task_key = (loop, key)
        task = self._tasks.get(task_key)
        if task is None:
            # Built directly instead of through loop.create_task: an eager task factory could run the computation
            # to its end before the task is registered, leaving a finished task in the map.
            task = asyncio.Task(self._alead(task_key, func), loop=loop)
            task.add_done_callback(_consume_exception)
            self._tasks[task_key] = task

        # shield: a cancelled caller cancels neither the computation nor the other callers.
        return await asyncio.shield(task)

    async def _alead(self, task_key: tuple[asyncio.AbstractEventLoop, str], func: Callable[[], Awaitable[_R]]) -> _R:
        # The task runs in its own copy of the context, so the marker needs no reset.
        _ = _leading.set(_leading.get() | {(id(self), task_key[1])})
        try:
            return await func()
        finally:
            del self._tasks[task_key]
