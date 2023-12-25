import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

import pytest

from py_cachify import CachifyLockError, cached, once


def sync_function(arg1, arg2):
    sleep(2)
    return arg1 + arg2


async def async_function(arg1, arg2):
    await asyncio.sleep(2)
    return arg1 + arg2


def test_once_decorator():
    _sync_function = once(key='test_key-{arg1}-{arg2}', return_on_locked='IF_LOCKED')(sync_function)

    with ThreadPoolExecutor(max_workers=2) as runner:
        futures = [runner.submit(_sync_function, a, b) for a, b in [(1, 2), (1, 2)]]

    results = [res.result() for res in as_completed(futures)]
    assert 'IF_LOCKED' in results
    assert 3 in results


def test_once_decorator_raises():
    _sync_function = once(key='test_key-{arg1}-{arg2}', raise_on_locked=True)(sync_function)

    with ThreadPoolExecutor(max_workers=2) as runner:
        futures = [runner.submit(sync_function, a, b) for a, b in [(1, 2), (1, 2)]]

    with pytest.raises(CachifyLockError):
        [res.result() for res in as_completed(futures)]


@pytest.mark.asyncio
async def test_once_decorator_async_function():
    _async_function = once(key='async_test_key-{arg1}-{arg2}', return_on_locked='IF_LOCKED')(async_function)

    results = await asyncio.gather(_async_function(3, 4), _async_function(3, 4))
    assert 'IF_LOCKED' in results
    assert 7 in results


@pytest.mark.asyncio
async def test_async_once_decorator_raise_on_locked(init_cachify_fixture):
    _async_function = once(key='async_test_key-{arg1}-{arg2}', raise_on_locked=True)(async_function)

    with pytest.raises(CachifyLockError):
        await asyncio.gather(_async_function(3, 4), _async_function(3, 4))


def test_cached_decorator_sync_function():
    _sync_function_wrapped = cached(key='test_key')(sync_function)

    result = _sync_function_wrapped(3, 4)
    result_2 = _sync_function_wrapped(10, 20)

    assert result == 7
    assert result_2 == 7


@pytest.mark.asyncio
async def test_cached_decorator_async_function():
    _async_function_wrapped = cached(key='test_key_{arg1}')(async_function)
    result = await _async_function_wrapped(3, 4)
    result_2 = await _async_function_wrapped(3, 20)

    assert result == 7
    assert result_2 == 7
