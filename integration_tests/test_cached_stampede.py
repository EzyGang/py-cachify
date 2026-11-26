import asyncio
import multiprocessing
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Barrier
from threading import Timer
from typing import Any

import pytest
import redis
from redis.asyncio import Redis as RedisAsync

from py_cachify import LockConf, cached, init_cachify
from py_cachify._backend._lib import get_cachify_client


REDIS_URL = 'redis://localhost:6379'

_counter = redis.Redis.from_url(f'{REDIS_URL}/0')  # pyright: ignore[reportUnknownMemberType]


def _calls(item: str) -> int:
    return int(_counter.get(f'stampede-calls-{item}') or 0)  # pyright: ignore[reportArgumentType]


def _count_call(item: str) -> None:
    _ = _counter.incr(f'stampede-calls-{item}')


@cached(key='stampede-async-{item}', stampede_protect=LockConf(poll_interval=0.02))
async def _slow_async(item: str) -> str:
    _count_call(item)
    await asyncio.sleep(0.3)
    return f'value-{item}'


@cached(key='stampede-sync-{item}', stampede_protect=LockConf(poll_interval=0.02))
def _slow_sync(item: str) -> str:
    _count_call(item)
    time.sleep(0.3)
    return f'value-{item}'


@cached(key='stampede-dead-{item}', stampede_protect=LockConf(exp=2, wait=10, poll_interval=0.05))
def _hangs_on_first_call(item: str, hang: bool) -> str:
    _count_call(item)
    if hang:
        time.sleep(60)
    return f'value-{item}'


def _init_like_conftest() -> None:
    init_cachify(
        sync_client=redis.Redis.from_url(f'{REDIS_URL}/0'),  # pyright: ignore[reportUnknownMemberType]
        async_client=RedisAsync.from_url(f'{REDIS_URL}/1'),  # pyright: ignore[reportUnknownMemberType]
    )


def _burst(mode: str, item: str, callers: int, barrier: Barrier, results: 'Queue[list[str]]') -> None:
    _init_like_conftest()
    _ = barrier.wait()

    if mode == 'async':

        async def _all() -> list[str]:
            return await asyncio.gather(*(_slow_async(item) for _ in range(callers)))

        results.put(asyncio.run(_all()))
        return

    def _one(_: int) -> str:
        return _slow_sync(item)

    with ThreadPoolExecutor(max_workers=callers) as pool:
        results.put(list(pool.map(_one, range(callers))))


def _hang_holding_lock(item: str) -> None:
    _init_like_conftest()
    _ = _hangs_on_first_call(item, hang=True)


@pytest.mark.parametrize('mode', ['async', 'sync'])
def test_lock_one_call_across_processes(mode: str) -> None:
    ctx = multiprocessing.get_context('spawn')
    item, processes, callers = uuid.uuid4().hex, 4, 25
    barrier = ctx.Barrier(processes)
    results: Queue[list[str]] = ctx.Queue()
    procs = [ctx.Process(target=_burst, args=(mode, item, callers, barrier, results)) for _ in range(processes)]
    for proc in procs:
        proc.start()

    values = [value for _ in procs for value in results.get(timeout=60)]
    for proc in procs:
        proc.join(timeout=30)
        assert proc.exitcode == 0

    assert values == [f'value-{item}'] * (processes * callers)
    assert _calls(item) == 1


def test_lock_waiter_returns_value_without_taking_lock() -> None:
    client = get_cachify_client()
    item = uuid.uuid4().hex
    cache_key, lock_key = f'stampede-wait-{item}-cached', f'stampede-wait-{item}-cached_lock'
    assert client.try_acquire_lock(key=lock_key, ttl=60, token='other')
    filler = Timer(0.3, client.set, kwargs={'key': cache_key, 'val': f'value-{item}'})
    filler.start()

    @cached(key='stampede-wait-{item}', stampede_protect=LockConf(wait=10, poll_interval=0.02))
    def compute(item: str) -> Any:
        pytest.fail('another process is computing the value')

    assert compute(item) == f'value-{item}'
    assert client.get(key=lock_key) == 'other'
    _ = client.delete(key=lock_key)


def test_lock_left_by_dead_holder_expires_and_next_caller_computes() -> None:
    ctx = multiprocessing.get_context('spawn')
    item = uuid.uuid4().hex
    holder = ctx.Process(target=_hang_holding_lock, args=(item,))
    holder.start()

    deadline = time.monotonic() + 30
    while _calls(item) == 0:
        assert time.monotonic() < deadline, 'the holder never started computing'
        time.sleep(0.05)
    holder.kill()
    holder.join(timeout=10)

    assert get_cachify_client().get(key=f'stampede-dead-{item}-cached_lock') is not None
    started = time.monotonic()
    assert _hangs_on_first_call(item, hang=False) == f'value-{item}'
    assert time.monotonic() - started < 5
    assert _calls(item) == 2


def test_lock_wait_timeout_computes_without_raising() -> None:
    client = get_cachify_client()
    item = uuid.uuid4().hex
    lock_key = f'stampede-timeout-{item}-cached_lock'
    assert client.try_acquire_lock(key=lock_key, ttl=60, token='other')

    @cached(key='stampede-timeout-{item}', stampede_protect=LockConf(wait=0.5, poll_interval=0.05))
    def compute(item: str) -> str:
        _count_call(item)
        return f'value-{item}'

    started = time.monotonic()
    assert compute(item) == f'value-{item}'
    assert 0.5 <= time.monotonic() - started < 3
    assert _calls(item) == 1
    assert client.get(key=lock_key) == 'other'
    _ = client.delete(key=lock_key)
