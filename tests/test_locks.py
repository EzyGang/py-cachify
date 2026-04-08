# pyright: reportPrivateUsage=false
import asyncio
from asyncio import sleep as asleep
from contextlib import nullcontext
from threading import Thread
from time import sleep
from typing import Any

import pytest

from py_cachify import CachifyLockError, init_cachify, lock
from py_cachify._backend._lib import CachifyClient
from py_cachify._backend._types._common import UNSET


lock_obj = lock(key='test')


@pytest.mark.asyncio
async def test_async_lock(init_cachify_fixture: None) -> None:
    async def async_operation():
        async with lock('lock'):
            return None

    await async_operation()


@pytest.mark.asyncio
async def test_async_lock_already_locked(init_cachify_fixture: None) -> None:
    key = 'lock'

    async def async_operation():
        async with lock(key):
            async with lock(key):
                pass

    with pytest.raises(CachifyLockError, match=f'{key} is already locked!'):
        await async_operation()


def test_lock(init_cachify_fixture: None) -> None:
    def sync_operation():
        with lock('lock'):
            pass

    sync_operation()


def test_lock_already_locked(init_cachify_fixture: None) -> None:
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
def test_waiting_lock(init_cachify_fixture: None, exp: 'int | None', timeout: float, expectation: Any) -> None:
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
async def test_waiting_lock_async(
    init_cachify_fixture: None, exp: 'int | None', timeout: float, expectation: Any
) -> None:
    key = 'lock'

    async def async_operation():
        async with lock(key=key, exp=exp):
            async with lock(key=key, nowait=False, timeout=timeout):
                return None

    with expectation as e:
        assert await async_operation() == e


def test_lock_cachify_returns_cachify_instance(init_cachify_fixture: None) -> None:
    assert isinstance(lock_obj._cachify, CachifyClient)
    assert lock_obj._cachify is not None


def test_lock_recreate_cm_returns_self() -> None:
    assert lock_obj._recreate_cm() is lock_obj


@pytest.mark.parametrize('timeout,expected', [(None, float('inf')), (10, 20.0)])
def test_lock_calc_stop_at(mocker: Any, timeout: 'int | None', expected: float) -> None:
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
def test_lock_get_ttl(
    init_cachify_fixture: None, default_expiration: 'int | None', exp: Any, expected: 'float | None'
) -> None:
    init_dict = {'default_lock_expiration': default_expiration} if default_expiration is not None else {}

    init_cachify(**init_dict)  # pyright: ignore[reportArgumentType]

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
def test_lock_raise_if_cached(mocker: Any, is_already_locked: bool, key: str, do_raise: bool, expectation: Any) -> None:
    patch_log = mocker.patch('py_cachify._backend._logger.logger.debug')

    with expectation:
        lock._raise_if_cached(
            is_already_cached=is_already_locked,
            key=key,
            do_raise=do_raise,
        )
        if is_already_locked is True:
            patch_log.assert_called_once_with(f'{key} is already locked!')


def test_unset_type_bool() -> None:
    assert bool(UNSET) is False


@pytest.mark.parametrize(
    'sleep_time,expected',
    [
        (1, True),
        (0, False),
    ],
)
def test_is_locked_on_lock_obj(init_cachify_fixture: None, sleep_time: float, expected: bool) -> None:
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
        (1, True),
        (0, False),
    ],
)
async def test_is_locked_on_lock_obj_async(init_cachify_fixture: None, sleep_time: float, expected: bool) -> None:
    test_lock = lock('test')

    async def async_function():
        async with test_lock:
            await asleep(sleep_time)

    task = asyncio.create_task(async_function())

    await asleep(0.2)

    assert await test_lock.is_alocked() is expected

    await task


def test_lock_poll_interval_is_stored_in_cachify_client():
    cachify_instance = init_cachify(lock_poll_interval=0.05, is_global=True)
    assert cachify_instance._client.lock_poll_interval == 0.05


def test_lock_poll_interval_is_used_in_sync_lock(mocker: Any):
    sleep_mock = mocker.patch('time.sleep')
    _ = init_cachify(lock_poll_interval=0.05, is_global=True)

    @lock(key='poll-test', nowait=False, timeout=2.0)
    def sync_function() -> None:
        sleep(0.5)

    thread1 = Thread(target=sync_function)
    thread1.start()
    sleep(0.1)

    thread2 = Thread(target=lambda: sync_function())
    thread2.start()
    thread2.join()
    thread1.join()

    poll_intervals = [call.args[0] for call in sleep_mock.call_args_list if call.args[0] == 0.05]
    assert len(poll_intervals) > 0


@pytest.mark.asyncio
async def test_lock_poll_interval_is_used_in_async_lock(mocker: Any):
    async def mock_sleep(interval: float) -> None:
        await asleep(0.01)

    sleep_mock = mocker.patch('py_cachify._backend._lock.asleep', side_effect=mock_sleep)
    _ = init_cachify(lock_poll_interval=0.05, is_global=True)

    @lock(key='poll-test-async', nowait=False, timeout=2.0)
    async def async_function() -> None:
        await asleep(0.2)

    task1 = asyncio.create_task(async_function())
    await asleep(0.05)

    task2 = asyncio.create_task(async_function())
    await task2
    await task1

    poll_intervals = [call.args[0] for call in sleep_mock.call_args_list if call.args[0] == 0.05]
    assert len(poll_intervals) > 0
