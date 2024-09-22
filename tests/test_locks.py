import asyncio
from asyncio import sleep as asleep
from contextlib import nullcontext
from threading import Thread
from time import sleep

import pytest

from py_cachify import CachifyLockError
from py_cachify.backend.lib import Cachify, init_cachify
from py_cachify.backend.lock import lock
from py_cachify.backend.types import UNSET


lock_obj = lock(key='test')


@pytest.mark.asyncio
async def test_async_lock(init_cachify_fixture):
    async def async_operation():
        async with lock('lock'):
            return None

    await async_operation()


@pytest.mark.asyncio
async def test_async_lock_already_locked(init_cachify_fixture):
    key = 'lock'

    async def async_operation():
        async with lock(key):
            async with lock(key):
                pass

    with pytest.raises(CachifyLockError, match=f'{key} is already locked!'):
        await async_operation()


def test_lock(init_cachify_fixture):
    def sync_operation():
        with lock('lock'):
            pass

    sync_operation()


def test_lock_already_locked(init_cachify_fixture):
    key = 'lock'

    def sync_operation():
        with lock(key):
            with lock(key):
                pass

    with pytest.raises(CachifyLockError, match=f'{key} is already locked!'):
        sync_operation()


@pytest.mark.parametrize(
    'exp,timeout,expectation', [(1, 2, nullcontext(None)), (2, 1, pytest.raises(CachifyLockError))]
)
def test_waiting_lock(init_cachify_fixture, exp, timeout, expectation):
    key = 'lock'

    def sync_operation():
        with lock(key=key, exp=exp):
            with lock(key=key, nowait=False, timeout=timeout):
                return None

    with expectation as e:
        assert sync_operation() == e


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'exp,timeout,expectation', [(1, 2, nullcontext(None)), (2, 1, pytest.raises(CachifyLockError))]
)
async def test_waiting_lock_async(init_cachify_fixture, exp, timeout, expectation):
    key = 'lock'

    async def async_operation():
        async with lock(key=key, exp=exp):
            async with lock(key=key, nowait=False, timeout=timeout):
                return None

    with expectation as e:
        assert await async_operation() == e


def test_lock_cachify_returns_cachify_instance(init_cachify_fixture):
    assert isinstance(lock_obj._cachify, Cachify)
    assert lock_obj._cachify is not None


def test_lock_recreate_cm_returns_self():
    assert lock_obj._recreate_cm() is lock_obj


@pytest.mark.parametrize('timeout,expected', [(None, float('inf')), (10, 20.0)])
def test_lock_calc_stop_at(mocker, timeout, expected):
    new_lock = lock('test', timeout=timeout)
    mocker.patch('time.time', return_value=10.0)

    assert new_lock._calc_stop_at() == expected


@pytest.mark.parametrize(
    'default_expiration,exp,expected',
    [
        (None, UNSET, 30),
        (60, UNSET, 60),
        (30, 60, 60),
        (30, None, None),
    ],
)
def test_lock_get_ttl(init_cachify_fixture, default_expiration, exp, expected):
    init_dict = {'default_lock_expiration': default_expiration} if default_expiration is not None else {}

    init_cachify(**init_dict)

    lock_obj = lock('test', exp=exp)

    assert lock_obj._get_ttl() == expected


@pytest.mark.parametrize(
    'is_already_locked,key,do_raise,expectation',
    [
        (True, 'test', False, nullcontext(None)),
        (True, 'test', True, pytest.raises(CachifyLockError)),
        (False, 'test', True, nullcontext(None)),
    ],
)
def test_lock_raise_if_cached(mocker, is_already_locked, key, do_raise, expectation):
    patch_log = mocker.patch('py_cachify.backend.lock.logger.warning')

    with expectation:
        lock._raise_if_cached(
            is_already_cached=is_already_locked,
            key=key,
            do_raise=do_raise,
        )
        if is_already_locked is True:
            patch_log.assert_called_once_with(f'{key} is already locked!')


def test_unset_type_bool():
    assert bool(UNSET) is False


@pytest.mark.parametrize(
    'sleep_time,expected',
    [
        (3, True),
        (0, False),
    ],
)
def test_is_locked_on_lock_obj(init_cachify_fixture, sleep_time, expected):
    test_lock = lock('test')

    def sync_function():
        with test_lock:
            sleep(sleep_time)

    thread = Thread(target=sync_function)
    thread.start()
    sleep(0.3)

    assert test_lock.is_locked() is expected


@pytest.mark.parametrize(
    'sleep_time,expected',
    [
        (3, True),
        (0, False),
    ],
)
async def test_is_locked_on_lock_obj_async(init_cachify_fixture, sleep_time, expected):
    test_lock = lock('test')

    async def async_function():
        async with test_lock:
            await asleep(sleep_time)

    task = asyncio.create_task(async_function())

    await asleep(0.2)

    assert await test_lock.is_alocked() is expected

    await task
