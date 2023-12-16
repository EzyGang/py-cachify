import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

import pytest

from py_cachify.exceptions import CachifyLockError
from py_cachify.lock import once


def test_once_decorator_sync_function(init_cachify_fixture):
    @once(key='test_key-{arg1}-{arg2}')
    def sync_function(arg1, arg2):
        sleep(1)
        return arg1 + arg2

    with ThreadPoolExecutor(max_workers=2) as e:
        futures = [e.submit(sync_function, arg1=3, arg2=4), e.submit(sync_function, arg1=3, arg2=4)]

    results = [res.result() for res in as_completed(futures)]
    assert None in results
    assert 7 in results


@pytest.mark.asyncio
async def test_once_decorator_async_function(init_cachify_fixture):
    @once(key='test_key-{arg1}-{arg2}')
    async def async_function(arg1, arg2):
        await asyncio.sleep(1)
        return arg1 + arg2

    results = await asyncio.gather(async_function(3, 4), async_function(3, 4))
    assert None in results
    assert 7 in results


def test_once_decorator_raise_on_locked(init_cachify_fixture):
    @once(key='test_key-{arg1}-{arg2}', raise_on_locked=True)
    def sync_function(arg1, arg2):
        sleep(1)
        return arg1 + arg2

    with ThreadPoolExecutor(max_workers=2) as e:
        futures = [e.submit(sync_function, arg1=3, arg2=4), e.submit(sync_function, arg1=3, arg2=4)]

    with pytest.raises(CachifyLockError):
        [res.result() for res in as_completed(futures)]


@pytest.mark.asyncio
async def test_async_once_decorator_raise_on_locked(init_cachify_fixture):
    @once(key='test_key-{arg1}-{arg2}', raise_on_locked=True)
    async def async_function(arg1, arg2):
        await asyncio.sleep(1)
        return arg1 + arg2

    with pytest.raises(CachifyLockError):
        await asyncio.gather(async_function(3, 4), async_function(3, 4))


def test_once_decorator_return_on_locked_sync(init_cachify_fixture):
    to_return = 'test'

    @once(key='test_key-{arg1}', return_on_locked=to_return)
    def sync_function(arg1, arg2):
        sleep(1)
        return arg1 + arg2

    with ThreadPoolExecutor(max_workers=2) as e:
        futures = [e.submit(sync_function, arg1=3, arg2=4), e.submit(sync_function, arg1=3, arg2=4)]

    results = [res.result() for res in as_completed(futures)]
    assert to_return in results
    assert 7 in results


@pytest.mark.asyncio
async def test_once_decorator_return_on_locked_async(init_cachify_fixture):
    to_return = 'test'

    @once(key='test_key-{arg1}', return_on_locked=to_return)
    async def async_function(arg1, arg2):
        await asyncio.sleep(1)
        return arg1 + arg2

    results = await asyncio.gather(async_function(3, 4), async_function(3, 4))
    assert to_return in results
    assert 7 in results
