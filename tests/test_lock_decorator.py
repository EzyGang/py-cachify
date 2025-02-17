import asyncio
from asyncio import sleep as asleep
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from time import sleep

import pytest

from py_cachify import CachifyLockError, init_cachify, lock
from py_cachify._backend._lib import get_cachify
from py_cachify._backend._types._common import UNSET


@pytest.mark.parametrize(
    'sleep_time,input1,input2,result1,result2',
    [
        (1, 3, 3, nullcontext(13), pytest.raises(CachifyLockError)),
        (1, 3, 5, nullcontext(13), nullcontext(15)),
    ],
)
def test_lock_decorator_no_wait_sync(init_cachify_fixture, sleep_time, input1, input2, result1, result2):
    @lock(key='test_key-{arg}')
    def sync_function(arg: int) -> int:
        sleep(sleep_time)
        return arg + 10

    with ThreadPoolExecutor(max_workers=2) as e:
        future_1, future_2 = (
            e.submit(sync_function, arg=input1),
            e.submit(sync_function, arg=input2),
        )

    with result1 as r1:
        assert r1 == future_1.result()

    with result2 as r2:
        assert r2 == future_2.result()


@pytest.mark.parametrize(
    'sleep_time,input1,input2,result1,result2',
    [
        (1, 3, 3, nullcontext(13), pytest.raises(CachifyLockError)),
        (1, 3, 5, nullcontext(13), nullcontext(15)),
    ],
)
@pytest.mark.asyncio
async def test_lock_decorator_no_wait_async(init_cachify_fixture, sleep_time, input1, input2, result1, result2):
    @lock(key='test_key-{arg}')
    async def async_function(arg: int) -> int:
        await asleep(sleep_time)
        return arg + 10

    task1 = asyncio.create_task(async_function(input1))
    task2 = asyncio.create_task(async_function(input2))

    with result1 as r1:
        assert r1 == await task1

    with result2 as r2:
        assert r2 == await task2


@pytest.mark.parametrize(
    'sleep_time,timeout,input,result1,result2',
    [
        (1, 2, 3, nullcontext(13), nullcontext(13)),
        (2, 1, 3, nullcontext(13), pytest.raises(CachifyLockError)),
        (0, 1, 3, nullcontext(13), nullcontext(13)),
    ],
)
def test_lock_decorator_no_wait_false_sync(init_cachify_fixture, sleep_time, timeout, input, result1, result2):
    @lock(key='test_key-{arg}', nowait=False, timeout=timeout)
    def sync_function(arg: int) -> int:
        sleep(sleep_time)
        return arg + 10

    with ThreadPoolExecutor(max_workers=2) as e:
        future_1, future_2 = (
            e.submit(sync_function, arg=input),
            e.submit(sync_function, arg=input),
        )

    with result1 as r1:
        assert r1 == future_1.result()

    with result2 as r2:
        assert r2 == future_2.result()


@pytest.mark.parametrize(
    'sleep_time,timeout,input,result1,result2',
    [
        (1, 2, 3, nullcontext(13), nullcontext(13)),
        (1, 0.5, 3, nullcontext(13), pytest.raises(CachifyLockError)),
        (0, 0.5, 3, nullcontext(13), nullcontext(13)),
    ],
)
@pytest.mark.asyncio
async def test_lock_decorator_no_wait_false_async(init_cachify_fixture, sleep_time, timeout, input, result1, result2):
    @lock(key='test_key-{arg}', nowait=False, timeout=timeout)
    async def async_function(arg: int) -> int:
        await asleep(sleep_time)
        return arg + 10

    task1 = asyncio.create_task(async_function(input))
    task2 = asyncio.create_task(async_function(input))

    with result1 as r1:
        assert r1 == await task1

    with result2 as r2:
        assert r2 == await task2


@pytest.mark.parametrize(
    'sleep_time,timeout,exp,default_exp,result1,result2',
    [
        (3, 2, 1, None, nullcontext(15), nullcontext(15)),
        (2, 2, UNSET, 1, nullcontext(15), nullcontext(15)),
        (2, 1, UNSET, 2, nullcontext(15), pytest.raises(CachifyLockError)),
        (3, 2, 4, 1, nullcontext(15), pytest.raises(CachifyLockError)),
        (3, 2, 1, 4, nullcontext(15), nullcontext(15)),
    ],
)
def test_lock_decorator_expiration_sync(init_cachify_fixture, sleep_time, timeout, exp, default_exp, result1, result2):
    init_cachify(default_lock_expiration=default_exp)

    @lock(key='test_key-{arg}', nowait=False, timeout=timeout, exp=exp)
    def sync_function(arg: int) -> int:
        sleep(sleep_time)
        return arg + 10

    with ThreadPoolExecutor(max_workers=2) as e:
        future_1, future_2 = (
            e.submit(sync_function, arg=5),
            e.submit(sync_function, arg=5),
        )

    with result1 as r1:
        assert r1 == future_1.result()

    with result2 as r2:
        assert r2 == future_2.result()


@pytest.mark.parametrize(
    'sleep_time,timeout,exp,default_exp,result1,result2',
    [
        (3, 2, 1, None, nullcontext(15), nullcontext(15)),
        (2, 2, UNSET, 1, nullcontext(15), nullcontext(15)),
        (2, 1, UNSET, 2, nullcontext(15), pytest.raises(CachifyLockError)),
        (3, 2, 4, 1, nullcontext(15), pytest.raises(CachifyLockError)),
        (3, 2, 1, 4, nullcontext(15), nullcontext(15)),
    ],
)
@pytest.mark.asyncio
async def test_lock_decorator_expiration_async(
    init_cachify_fixture, sleep_time, timeout, exp, default_exp, result1, result2
):
    init_cachify(default_lock_expiration=default_exp)

    @lock(key='test_key-{arg}', nowait=False, timeout=timeout, exp=exp)
    async def async_function(arg: int) -> int:
        await asleep(sleep_time)
        return arg + 10

    task1 = asyncio.create_task(async_function(5))
    task2 = asyncio.create_task(async_function(5))

    with result1 as r1:
        assert r1 == await task1

    with result2 as r2:
        assert r2 == await task2


def test_lock_works_on_methods(init_cachify_fixture):
    class TestClass:
        t: str = 'test'

        @lock(key='method-{self.t}')
        def method(self, a: int, b: int) -> int:
            return a + b

        @staticmethod
        @lock(key='method-static')
        def method_static(a: int, b: int) -> int:
            return a + b

        @classmethod
        @lock(key='method-class')
        def method_class(cls, a: int, b: int) -> int:
            return a + b

    tc = TestClass()
    assert tc.method(1, 2) == 3
    assert tc.method.release(tc, 1, 2) is None
    assert tc.method.is_locked(tc, 1, 2) is False
    # Fix the type annotation to support
    assert tc.method_static(1, 2) == 3
    assert tc.method_static.release(1, 2) is None
    assert tc.method_static.is_locked(1, 2) is False
    # Fix the type annotation to support
    assert tc.method_class(1, 2) == 3
    assert tc.method_class.release(tc.__class__, 1, 2) is None
    assert tc.method_class.is_locked(tc.__class__, 1, 2) is False


@pytest.mark.asyncio
async def test_cached_works_on_async_methods(init_cachify_fixture):
    class TestClass:
        t: str = 'test'

        @lock(key='method-{self.t}')
        async def method(self, a: int, b: int) -> int:
            return a + b

        @staticmethod
        @lock(key='method-static')
        async def method_static(a: int, b: int) -> int:
            return a + b

        @classmethod
        @lock(key='method-class')
        async def method_class(cls, a: int, b: int) -> int:
            return a + b

    tc = TestClass()

    assert await tc.method(1, 2) == 3
    assert await tc.method.release(tc, 1, 2) is None
    assert await tc.method.is_locked(tc, 1, 2) is False
    # Fix the type annotation to support
    assert await tc.method_static(1, 2) == 3
    assert await tc.method_static.release(1, 2) is None
    assert await tc.method_static.is_locked(1, 2) is False
    # Fix the type annotation to support
    assert await tc.method_class(1, 2) == 3
    assert await tc.method_class.release(tc.__class__, 1, 2) is None
    assert await tc.method_class.is_locked(tc.__class__, 1, 2) is False


def test_lock_decorator_cleans_up_on_error(init_cachify_fixture):
    @lock(key='test_key-{arg}', nowait=False, timeout=15, exp=30)
    def sync_function(arg: int) -> int:
        raise RuntimeError()

    try:
        sync_function(123)
    except Exception:
        cachify = get_cachify()
        val = cachify.get('PYC-test_key-123')

        assert val is None


@pytest.mark.asyncio
async def test_async_lock_decorator_cleans_up_on_error(init_cachify_fixture):
    @lock(key='test_key-{arg}', nowait=False, timeout=15, exp=30)
    async def async_function(arg: int) -> int:
        raise RuntimeError()

    try:
        await async_function(123)
    except Exception:
        cachify = get_cachify()
        val = await cachify.a_get('PYC-test_key-123')

        assert val is None
