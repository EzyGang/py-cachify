import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

import pytest
from pytest_mock import MockerFixture

from py_cachify._backend._cached import cached
from py_cachify._backend._lock import once


def sync_function(arg1: int, arg2: int) -> int:
    sleep(1)
    return arg1 + arg2


async def async_function(arg1: int, arg2: int) -> int:
    await asyncio.sleep(1)
    return arg1 + arg2


def test_cached_once_merge(init_cachify_fixture, mocker: MockerFixture):
    spy = mocker.spy(sys.modules[__name__], 'sync_function')
    sync_function_wrapped = cached(key='test_key')(sync_function)
    once_wrapped = once(key='test_key')(sync_function_wrapped)

    with ThreadPoolExecutor(max_workers=2) as e:
        futures = [
            e.submit(once_wrapped, arg1=3, arg2=4),
            e.submit(lambda: sleep(0.1) or once_wrapped(arg1=3, arg2=4)),
        ]

    result = once_wrapped(3, 4)

    results = [res.result() for res in as_completed(futures)]
    assert None in results
    assert results.count(7) == 1
    assert result == 7
    assert spy.call_count == 1


@pytest.mark.asyncio
async def test_cached_once_merge_async(init_cachify_fixture, mocker: MockerFixture):
    spy = mocker.spy(sys.modules[__name__], 'async_function')
    async_function_wrapped = cached(key='test_key')(async_function)
    once_wrapped = once(key='test_key')(async_function_wrapped)

    once_wrapped(3, 4)
    results = await asyncio.gather(once_wrapped(3, 4), once_wrapped(3, 4))
    result = await once_wrapped(3, 4)

    assert None in results
    assert results.count(7) == 1
    assert result == 7
    assert spy.call_count == 1
