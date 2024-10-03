import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

import pytest
from typing_extensions import assert_type

from py_cachify import CachifyLockError, async_once, once, sync_once
from py_cachify._backend.types import AsyncWithResetProto, P, R, SyncWithResetProto


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
    async def async_function(arg1: int, arg2: int) -> int:
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


def test_preserves_type_annotations(init_cachify_fixture):
    @async_once(key='test_key-{arg1}')
    async def async_function(arg1: int, arg2: int) -> int:
        await asyncio.sleep(1)
        return arg1 + arg2

    @sync_once(key='test_key-{arg1}-{arg2}', raise_on_locked=True)
    def sync_function(arg1: int, arg2: int) -> int:
        sleep(1)
        return arg1 + arg2

    for name, clz in [('arg1', int), ('arg2', int), ('return', int)]:
        assert sync_function.__annotations__[name] == clz
        assert async_function.__annotations__[name] == clz

    assert_type(sync_function, SyncWithResetProto[P, R])
    assert_type(async_function, AsyncWithResetProto[P, R])


def test_once_wrapped_async_function_has_release_and_is_locked_callables_attached(init_cachify_fixture):
    @once(key='test')
    async def async_function(arg1: int, arg2: int) -> None:
        return None

    assert hasattr(async_function, 'release')
    assert asyncio.iscoroutinefunction(async_function.release)

    assert hasattr(async_function, 'is_locked')
    assert asyncio.iscoroutinefunction(async_function.is_locked)


def test_once_wrapped_function_has_release_and_is_locked_callables_attached(init_cachify_fixture):
    @once(key='test')
    def sync_function() -> None: ...

    assert hasattr(sync_function, 'release')
    assert not asyncio.iscoroutinefunction(sync_function.release)
    assert callable(sync_function.release)

    assert hasattr(sync_function, 'is_locked')
    assert not asyncio.iscoroutinefunction(sync_function.is_locked)
    assert callable(sync_function.is_locked)
