from threading import Thread
from time import sleep

import pytest

from py_cachify import CachifyLockError, cached, once


def test_once_decorator():
    @once(key='test_key-{arg1}', return_on_locked='IF_LOCKED')
    def _sync_function(arg1, arg2):
        sleep(2)
        return arg1 + arg2

    thread = Thread(target=_sync_function, args=(1, 2))
    thread.start()
    sleep(0.1)
    result = _sync_function(1, 2)

    assert 'IF_LOCKED' == result


def test_once_decorator_raises():
    @once(key='test_key-{arg1}-{arg2}', raise_on_locked=True)
    def _sync_function(arg1, arg2):
        sleep(2)
        return arg1 + arg2

    thread = Thread(target=_sync_function, args=(1, 2))
    thread.start()
    sleep(0.1)
    with pytest.raises(CachifyLockError):
        _sync_function(1, 2)


@pytest.mark.asyncio
async def test_once_decorator_async_function():
    @once(key='async_test_key-{arg1}-{arg2}', return_on_locked='IF_LOCKED')
    async def _async_function(arg1, arg2, initial=True):
        res = None
        if initial:
            res = await _async_function(arg1, arg2, initial=False)
        return arg1 + arg2, res

    results = await _async_function(3, 4)
    assert 'IF_LOCKED' in results
    assert 7 in results


@pytest.mark.asyncio
async def test_async_once_decorator_raise_on_locked(init_cachify_fixture):
    @once(key='async_test_key-{arg1}-{arg2}', raise_on_locked=True)
    async def _async_function(arg1, arg2):
        await _async_function(arg1, arg2)
        return arg1 + arg2

    with pytest.raises(CachifyLockError):
        await _async_function(3, 4)


def test_cached_decorator_sync_function():
    @cached(key='test_key')
    def _sync_function_wrapped(arg1, arg2):
        return arg1 + arg2

    result = _sync_function_wrapped(3, 4)
    result_2 = _sync_function_wrapped(10, 20)

    assert result == 7
    assert result_2 == 7


@pytest.mark.asyncio
async def test_cached_decorator_async_function():
    @cached(key='test_key_{arg1}')
    async def _async_function_wrapped(arg1, arg2):
        return arg1 + arg2

    result = await _async_function_wrapped(3, 4)
    result_2 = await _async_function_wrapped(3, 20)

    assert result == 7
    assert result_2 == 7
