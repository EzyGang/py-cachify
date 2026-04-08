# pyright: reportPrivateUsage=false
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from typing import Optional

import pytest

from py_cachify._backend._cached import cached
from py_cachify._backend._lock import once
from py_cachify._backend._pool import pool, pooled


def sync_function(arg1: int, arg2: int, calls: Optional[list[int]] = None) -> int:
    sleep(1)
    if calls is not None:
        calls.append(1)
    return arg1 + arg2


async def async_function(arg1: int, arg2: int, calls: Optional[list[int]] = None) -> int:
    await asyncio.sleep(1)
    if calls is not None:
        calls.append(1)
    return arg1 + arg2


def test_cached_once_merge(init_cachify_fixture: None) -> None:
    calls: list[int] = []
    sync_function_wrapped = cached(key='test_key')(sync_function)
    once_wrapped = once(key='test_key')(sync_function_wrapped)

    with ThreadPoolExecutor(max_workers=2) as e:
        futures = [
            e.submit(once_wrapped, 3, 4, calls),
            e.submit(lambda: sleep(0.1) or once_wrapped(3, 4, calls)),
        ]

    result = once_wrapped(3, 4, calls)

    results = [res.result() for res in as_completed(futures)]
    assert None in results
    assert results.count(7) == 1
    assert result == 7
    assert sum(calls) == 1


@pytest.mark.asyncio
async def test_cached_once_merge_async(init_cachify_fixture: None) -> None:
    calls: list[int] = []
    async_function_wrapped = cached(key='test_key')(async_function)
    once_wrapped = once(key='test_key')(async_function_wrapped)

    results = await asyncio.gather(once_wrapped(3, 4, calls), once_wrapped(3, 4, calls))
    result = await once_wrapped(3, 4, calls)

    assert None in results
    assert results.count(7) == 1
    assert result == 7
    assert sum(calls) == 1


def test_pooled_cached_merge_sync(init_cachify_fixture: None) -> None:
    """Test pooled() wrapped with cached() decorator."""

    def _func(arg1: int, arg2: int) -> int:
        sleep(0.1)
        return arg1 + arg2

    # Apply pooled first, then cached
    pooled_wrapped = pooled(key='pooled-cache-sync', max_size=2)(_func)
    cached_wrapped = cached(key='pooled-cache-sync')(pooled_wrapped)

    with ThreadPoolExecutor(max_workers=2) as e:
        futures = [
            e.submit(cached_wrapped, 3, 4),
            e.submit(lambda: sleep(0.05) or cached_wrapped(3, 4)),
        ]

    results = [res.result() for res in as_completed(futures)]

    # Both should get the result (7)
    assert all(r == 7 for r in results)
    # Note: With concurrent execution, cached may call _func more than once
    # since both calls may start before the first completes and caches


@pytest.mark.asyncio
async def test_pooled_cached_merge_async(init_cachify_fixture: None) -> None:
    """Test async pooled() + cached() decorator."""

    async def _func(arg1: int, arg2: int) -> int:
        await asyncio.sleep(0.1)
        return arg1 + arg2

    # Apply pooled first, then cached
    pooled_wrapped = pooled(key='pooled-cache-async', max_size=2)(_func)
    cached_wrapped = cached(key='pooled-cache-async')(pooled_wrapped)

    results = await asyncio.gather(
        cached_wrapped(3, 4),
        cached_wrapped(3, 4),
    )

    # Both should get the result (7)
    assert all(r == 7 for r in results)
    # Note: With concurrent execution, cached may call _func more than once


def test_cached_pooled_merge_sync(init_cachify_fixture: None) -> None:
    """Test cached() wrapped with pooled() decorator."""

    def _func(arg1: int, arg2: int) -> int:
        sleep(0.1)
        return arg1 + arg2

    # Apply cached first, then pooled
    cached_wrapped = cached(key='cache-pooled-sync')(_func)
    pooled_wrapped = pooled(key='cache-pooled-sync', max_size=2)(cached_wrapped)

    with ThreadPoolExecutor(max_workers=2) as e:
        futures = [
            e.submit(pooled_wrapped, 3, 4),
            e.submit(lambda: sleep(0.05) or pooled_wrapped(3, 4)),
        ]

    results = [res.result() for res in as_completed(futures)]

    # Both should get the result (7)
    assert all(r == 7 for r in results)
    # Note: With concurrent execution, _func may be called more than once


@pytest.mark.asyncio
async def test_cached_pooled_merge_async(init_cachify_fixture: None) -> None:
    """Test async cached() + pooled() decorator."""

    async def _func(arg1: int, arg2: int) -> int:
        await asyncio.sleep(0.1)
        return arg1 + arg2

    # Apply cached first, then pooled
    cached_wrapped = cached(key='cache-pooled-async')(_func)
    pooled_wrapped = pooled(key='cache-pooled-async', max_size=2)(cached_wrapped)

    results = await asyncio.gather(
        pooled_wrapped(3, 4),
        pooled_wrapped(3, 4),
    )

    # Both should get the result (7)
    assert all(r == 7 for r in results)
    # Note: With concurrent execution, _func may be called more than once


def test_pooled_once_merge_sync(init_cachify_fixture: None) -> None:
    """Test pooled() + once() merge."""
    calls: list[int] = []

    # Apply pooled first, then once
    pooled_wrapped = pooled(key='pooled-once-sync', max_size=5)(sync_function)
    once_wrapped = once(key='pooled-once-sync')(pooled_wrapped)

    with ThreadPoolExecutor(max_workers=2) as e:
        futures = [
            e.submit(once_wrapped, 3, 4, calls),
            e.submit(lambda: sleep(0.1) or once_wrapped(3, 4, calls)),
        ]

    results = [res.result() for res in as_completed(futures)]

    # One should be None (locked), one should be 7
    assert None in results
    assert 7 in results
    assert sum(calls) == 1


@pytest.mark.asyncio
async def test_pooled_once_merge_async(init_cachify_fixture: None) -> None:
    """Test async pooled() + once()."""
    calls: list[int] = []

    # Apply pooled first, then once
    pooled_wrapped = pooled(key='pooled-once-async', max_size=5)(async_function)
    once_wrapped = once(key='pooled-once-async')(pooled_wrapped)

    # Add delay between calls to ensure first acquires the lock
    results = await asyncio.gather(
        once_wrapped(3, 4, calls),
        asyncio.sleep(0.05) or once_wrapped(3, 4, calls),
    )

    # One should be None (locked), one should be 7
    assert None in results
    assert 7 in results
    assert sum(calls) == 1

    # One should be None (locked), one should be 7
    assert None in results
    assert 7 in results
    assert sum(calls) == 1


def test_pool_context_with_lock_merge_sync(init_cachify_fixture: None) -> None:
    """Test pool context manager + lock decorator (sync)."""
    from py_cachify import lock

    p = pool(key='test-pool-lock', max_size=5, slot_exp=60)

    @lock(key='test-pool-lock-lock', exp=30)
    def locked_func() -> str:
        return 'locked'

    with p:
        result = locked_func()
        assert result == 'locked'


def test_pool_context_with_cached_merge_sync(init_cachify_fixture: None) -> None:
    """Test pool context manager + cached decorator (sync)."""
    from py_cachify import cached

    p = pool(key='test-pool-cached-pool', max_size=5, slot_exp=60)

    call_count = 0

    @cached(key='test-pool-cached-cache')
    def cached_func() -> str:
        nonlocal call_count
        call_count += 1
        return f'result {call_count}'

    with p:
        r1 = cached_func()
        r2 = cached_func()

    assert r1 == r2  # Cached
    assert call_count == 1


@pytest.mark.asyncio
async def test_pool_context_with_lock_merge_async(init_cachify_fixture: None) -> None:
    """Test pool context manager + lock decorator (async)."""
    from py_cachify import lock

    p = pool(key='test-async-pool-lock', max_size=5, slot_exp=60)

    @lock(key='test-async-pool-lock-lock', exp=30)
    async def locked_func() -> str:
        return 'locked'

    async with p:
        result = await locked_func()
        assert result == 'locked'


@pytest.mark.asyncio
async def test_pool_context_with_cached_merge_async(init_cachify_fixture: None) -> None:
    """Test pool context manager + cached decorator (async)."""
    from py_cachify import cached

    p = pool(key='test-async-pool-cache', max_size=5, slot_exp=60)

    call_count = 0

    @cached(key='test-async-pool-cached')
    async def cached_func() -> str:
        nonlocal call_count
        call_count += 1
        return f'result {call_count}'

    async with p:
        r1 = await cached_func()
        r2 = await cached_func()

    assert r1 == r2  # Cached
    assert call_count == 1
