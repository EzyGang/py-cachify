# pyright: reportPrivateUsage=false
from time import sleep

import pytest

from py_cachify import cached
from py_cachify._backend._lib import Cachify


def _sync_func(x: int, calls: list[int]) -> int:
    calls.append(1)
    return x * 10


async def _async_func(x: int, calls: list[int]) -> int:
    calls.append(1)
    return x * 10


def test_sync_global_vs_local_redis_isolation(
    cachify_local_redis_second: Cachify,
) -> None:
    calls: list[int] = []

    global_wrapped = cached(key='client_isolation-{x}')(_sync_func)
    local_wrapped = cachify_local_redis_second.cached(key='client_isolation-{x}')(_sync_func)

    res1 = global_wrapped(1, calls)
    res2 = global_wrapped(1, calls)

    assert res1 == 10
    assert res2 == 10
    assert sum(calls) == 1

    res3 = local_wrapped(1, calls)
    res4 = local_wrapped(1, calls)

    assert res3 == 10
    assert res4 == 10
    assert sum(calls) == 2


@pytest.mark.asyncio
async def test_async_global_vs_local_redis_isolation(
    cachify_local_redis_second: Cachify,
) -> None:
    calls: list[int] = []

    global_wrapped = cached(key='client_isolation-async-{x}')(_async_func)
    local_wrapped = cachify_local_redis_second.cached(key='client_isolation-async-{x}')(_async_func)

    res1 = await global_wrapped(2, calls)
    res2 = await global_wrapped(2, calls)

    assert res1 == 20
    assert res2 == 20
    assert sum(calls) == 1

    res3 = await local_wrapped(2, calls)
    res4 = await local_wrapped(2, calls)

    assert res3 == 20
    assert res4 == 20
    assert sum(calls) == 2


def test_ttl_global_vs_local_redis(
    cachify_local_redis_second: Cachify,
) -> None:
    calls: list[int] = []

    global_wrapped = cached(key='ttl-test-{x}', ttl=1)(_sync_func)
    local_wrapped = cachify_local_redis_second.cached(key='ttl-test-{x}', ttl=5)(_sync_func)

    res1 = global_wrapped(3, calls)
    res2 = local_wrapped(3, calls)

    assert res1 == 30
    assert res2 == 30
    assert sum(calls) == 2

    sleep(2)

    res3 = global_wrapped(3, calls)
    res4 = local_wrapped(3, calls)

    assert res3 == 30
    assert res4 == 30
    assert sum(calls) == 3


def test_sync_multilayer_global_redis_inner_local_inmemory_outer_ttl(
    cachify_local_in_memory_client: Cachify,
) -> None:
    calls: list[int] = []

    inner = cached(key='multilayer-{x}', ttl=10)(_sync_func)
    outer = cachify_local_in_memory_client.cached(key='multilayer-{x}', ttl=1)(inner)

    res1 = outer(4, calls)
    assert res1 == 40
    assert sum(calls) == 1

    res2 = outer(4, calls)
    assert res2 == 40
    assert sum(calls) == 1

    sleep(2)

    res3 = outer(4, calls)
    assert res3 == 40
    assert sum(calls) == 1

    sleep(9)

    res4 = outer(4, calls)
    assert res4 == 40
    assert sum(calls) == 2


@pytest.mark.asyncio
async def test_async_multilayer_global_redis_inner_local_inmemory_outer_ttl(
    cachify_local_in_memory_client: Cachify,
) -> None:
    calls: list[int] = []

    inner = cached(key='multilayer-async-{x}', ttl=10)(_async_func)
    outer = cachify_local_in_memory_client.cached(key='multilayer-async-{x}', ttl=1)(inner)

    res1 = await outer(5, calls)
    assert res1 == 50
    assert sum(calls) == 1

    res2 = await outer(5, calls)
    assert res2 == 50
    assert sum(calls) == 1

    sleep(2)

    res3 = await outer(5, calls)
    assert res3 == 50
    assert sum(calls) == 1

    sleep(9)

    res4 = await outer(5, calls)
    assert res4 == 50
    assert sum(calls) == 2


def test_ttl_global_vs_local_inmemory(
    cachify_local_in_memory_client: Cachify,
) -> None:
    calls: list[int] = []

    global_wrapped = cached(key='ttl-test-mem-{x}', ttl=1)(_sync_func)
    local_wrapped = cachify_local_in_memory_client.cached(key='ttl-test-mem-{x}', ttl=5)(_sync_func)

    res1 = global_wrapped(6, calls)
    res2 = local_wrapped(6, calls)

    assert res1 == 60
    assert res2 == 60
    assert sum(calls) == 2

    sleep(2)

    res3 = global_wrapped(6, calls)
    res4 = local_wrapped(6, calls)

    assert res3 == 60
    assert res4 == 60
    assert sum(calls) == 3
