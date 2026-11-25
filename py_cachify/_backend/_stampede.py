import asyncio
import threading
import time
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import uuid4

from ._logger import logger
from ._types._common import UNSET, UnsetType


if TYPE_CHECKING:
    from ._lib import CachifyClient


_R = TypeVar('_R')

_leading: ContextVar[frozenset[tuple[int, str]]] = ContextVar('pyc_single_flight_leading', default=frozenset())


class StampedeProtect(Enum):
    """
    What `cached` does when several callers miss the same key at the same time.

    OFF: every caller calls the function.
    IN_MEMORY: callers in one process wait for the call already running.
    LOCK: IN_MEMORY, plus a lock in the cache backend so that one process computes the value
        while the others wait for it. Same as `LockConf()`.
    """

    OFF = 'off'
    IN_MEMORY = 'in_memory'
    LOCK = 'lock'


@dataclass(frozen=True)
class LockConf:
    """
    StampedeProtect.LOCK with custom settings.

    Args:
    exp (Union[int, None, UnsetType], optional): Lock expiration in seconds.
        Defaults to default_lock_expiration of the cachify client.
    wait (Union[float, None, UnsetType], optional): Seconds to wait for another process's value before computing
        it without the lock. Defaults to exp; None waits as long as the lock exists.
    poll_interval (Union[float, UnsetType], optional): Seconds between checks while waiting.
        Defaults to lock_poll_interval of the cachify client.
    """

    exp: int | None | UnsetType = UNSET
    wait: float | None | UnsetType = UNSET
    poll_interval: float | UnsetType = UNSET


class _Call:
    __slots__ = ('done', 'error', 'result')

    def __init__(self) -> None:
        self.done = threading.Event()
        self.result: Any = None
        self.error: BaseException | None = None


class SingleFlight:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._calls: dict[str, _Call] = {}
        self._tasks: dict[tuple[asyncio.AbstractEventLoop, str], asyncio.Task[Any]] = {}

    def run(self, key: str, func: Callable[[], _R]) -> _R:
        if (id(self), key) in _leading.get():
            return func()

        with self._lock:
            call = self._calls.get(key)
            is_leader = call is None
            if call is None:
                call = self._calls[key] = _Call()

        if not is_leader:
            _ = call.done.wait()
            if call.error is not None:
                raise call.error
            return cast(_R, call.result)

        token = _leading.set(_leading.get() | {(id(self), key)})
        try:
            call.result = func()
            return cast(_R, call.result)
        except BaseException as e:
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
            # Not loop.create_task: an eager task factory would finish the task before it is registered.
            task = asyncio.Task(self._alead(task_key, func), loop=loop)
            task.add_done_callback(lambda t: t.cancelled() or t.exception())
            self._tasks[task_key] = task

        return await asyncio.shield(task)

    async def _alead(self, task_key: tuple[asyncio.AbstractEventLoop, str], func: Callable[[], Awaitable[_R]]) -> _R:
        _ = _leading.set(_leading.get() | {(id(self), task_key[1])})
        try:
            return await func()
        finally:
            del self._tasks[task_key]


def _resolve(conf: LockConf, client: 'CachifyClient') -> tuple[int | None, float, float]:
    exp = client.default_expiration if isinstance(conf.exp, UnsetType) else conf.exp
    wait = exp if isinstance(conf.wait, UnsetType) else conf.wait
    poll = client.lock_poll_interval if isinstance(conf.poll_interval, UnsetType) else conf.poll_interval
    return exp, time.monotonic() + wait if wait is not None else float('inf'), poll


@contextmanager
def cache_lock(client: 'CachifyClient', key: str, conf: LockConf) -> Generator[Any, None, None]:
    """
    Yields the value of `key` if another process stored it while waiting, otherwise None:
    with the lock held, or without it once the wait ran out.
    """
    exp, stop_at, poll = _resolve(conf, client)
    lock_key, token = f'{key}_lock', uuid4().hex

    while not client.try_acquire_lock(key=lock_key, ttl=exp, token=token):
        if (remaining := stop_at - time.monotonic()) <= 0:
            logger.debug(f'{lock_key} is still locked, computing {key} without it')
            yield None
            return

        time.sleep(min(poll, remaining))
        if (val := client.get(key=key)) is not None:
            yield val
            return

    try:
        yield client.get(key=key)
    finally:
        client.release_lock(key=lock_key, token=token)


@asynccontextmanager
async def acache_lock(client: 'CachifyClient', key: str, conf: LockConf) -> AsyncGenerator[Any, None]:
    """
    Async version of `cache_lock`.
    """
    exp, stop_at, poll = _resolve(conf, client)
    lock_key, token = f'{key}_lock', uuid4().hex

    while not await client.a_try_acquire_lock(key=lock_key, ttl=exp, token=token):
        if (remaining := stop_at - time.monotonic()) <= 0:
            logger.debug(f'{lock_key} is still locked, computing {key} without it')
            yield None
            return

        await asyncio.sleep(min(poll, remaining))
        if (val := await client.a_get(key=key)) is not None:
            yield val
            return

    try:
        yield await client.a_get(key=key)
    finally:
        await client.a_release_lock(key=lock_key, token=token)
