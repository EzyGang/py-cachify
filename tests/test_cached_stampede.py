# pyright: reportPrivateUsage=false
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from pytest_mock import MockerFixture

import py_cachify._backend._cached as cached_module
from py_cachify import LockConf, StampedeProtect, cached, init_cachify
from py_cachify._backend._lib import CachifyClient, get_cachify_client
from py_cachify._backend._stampede import SingleFlight


@pytest.fixture
def flights(mocker: MockerFixture) -> list[SingleFlight]:
    created: list[SingleFlight] = []

    def _make() -> SingleFlight:
        created.append(SingleFlight())
        return created[-1]

    mocker.patch.object(cached_module, 'SingleFlight', side_effect=_make)
    return created


def _hold_lock(client: CachifyClient, lock_key: str) -> None:
    assert client.try_acquire_lock(key=lock_key, ttl=60, token='other')


def _fake_reads(client: CachifyClient, mocker: MockerFixture, cache_key: str, reads: list[Any]) -> None:
    real_get, pending = client.get, iter(reads)

    def _get(key: str) -> Any:
        return next(pending, None) if key == cache_key else real_get(key)

    mocker.patch.object(client, 'get', side_effect=_get)


def _afake_reads(client: CachifyClient, mocker: MockerFixture, cache_key: str, reads: list[Any]) -> None:
    real_get, pending = client.a_get, iter(reads)

    async def _get(key: str) -> Any:
        return next(pending, None) if key == cache_key else await real_get(key)

    mocker.patch.object(client, 'a_get', side_effect=_get)


async def test_async_concurrent_misses_share_one_call(init_cachify_fixture: None, flights: list[SingleFlight]) -> None:
    calls = 0

    @cached(key='sf-async-{x}')
    async def compute(x: int) -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return x * 2

    assert await asyncio.gather(*(compute(21) for _ in range(100))) == [42] * 100
    assert calls == 1
    assert flights[0]._tasks == {}
    assert await compute(21) == 42
    assert calls == 1


async def test_async_error_reaches_every_waiter_and_is_not_cached(
    init_cachify_fixture: None, flights: list[SingleFlight]
) -> None:
    calls = 0

    @cached(key='sf-async-err')
    async def compute() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        if calls == 1:
            raise ValueError('boom')
        return 7

    results = await asyncio.gather(*(compute() for _ in range(10)), return_exceptions=True)

    assert calls == 1
    assert all(isinstance(r, ValueError) for r in results)
    assert len({id(r) for r in results}) == 1
    assert flights[0]._tasks == {}
    assert await compute() == 7
    assert calls == 2


async def test_async_cancelled_caller_cancels_neither_computation_nor_waiters(
    init_cachify_fixture: None, flights: list[SingleFlight]
) -> None:
    started = asyncio.Event()
    calls = 0

    @cached(key='sf-async-cancel')
    async def compute() -> int:
        nonlocal calls
        calls += 1
        started.set()
        await asyncio.sleep(0.1)
        return 5

    first = asyncio.create_task(compute())
    second = asyncio.create_task(compute())
    await started.wait()
    _ = first.cancel()

    assert await second == 5
    with pytest.raises(asyncio.CancelledError):
        await first
    assert calls == 1
    assert flights[0]._tasks == {}
    assert await get_cachify_client().a_get(key='sf-async-cancel-cached') == 5


async def test_async_computation_fills_cache_when_every_caller_is_cancelled(
    init_cachify_fixture: None, flights: list[SingleFlight]
) -> None:
    started = asyncio.Event()

    @cached(key='sf-async-all-cancelled')
    async def compute() -> int:
        started.set()
        await asyncio.sleep(0.05)
        return 11

    caller = asyncio.create_task(compute())
    await started.wait()
    _ = caller.cancel()
    await asyncio.sleep(0.1)

    assert caller.cancelled()
    assert flights[0]._tasks == {}
    assert await get_cachify_client().a_get(key='sf-async-all-cancelled-cached') == 11


async def test_async_recursive_call_with_same_key_does_not_wait_for_itself(init_cachify_fixture: None) -> None:
    @cached(key='sf-async-rec')
    async def countdown(n: int) -> int:
        if n == 0:
            return 0
        return await countdown(n - 1) + 1

    assert await asyncio.wait_for(countdown(3), timeout=1) == 3


async def test_async_protection_off_calls_once_per_caller(init_cachify_fixture: None) -> None:
    calls = 0

    @cached(key='sf-async-off', stampede_protect=StampedeProtect.OFF)
    async def compute() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return 1

    assert await asyncio.gather(*(compute() for _ in range(10))) == [1] * 10
    assert calls == 10


async def test_async_leader_returns_value_filled_after_callers_miss(
    init_cachify_fixture: None, mocker: MockerFixture
) -> None:
    _afake_reads(get_cachify_client(), mocker, 'sf-async-reread-cached', [None, 'stored'])

    @cached(key='sf-async-reread')
    async def compute() -> str:
        pytest.fail('the value was already cached')

    assert await compute() == 'stored'


async def test_async_reset_during_computation_does_not_strand_waiters(init_cachify_fixture: None) -> None:
    started = asyncio.Event()

    @cached(key='sf-async-reset', stampede_protect=StampedeProtect.LOCK)
    async def compute() -> int:
        started.set()
        await asyncio.sleep(0.05)
        return 3

    callers = asyncio.gather(*(compute() for _ in range(10)))
    await started.wait()
    await compute.reset()

    assert await asyncio.wait_for(callers, timeout=1) == [3] * 10


async def test_async_encoder_and_decoder_with_lock(init_cachify_fixture: None) -> None:
    @cached(key='sf-async-enc', enc_dec=(lambda v: v + 5, lambda v: v - 5), stampede_protect=StampedeProtect.LOCK)
    async def compute() -> int:
        await asyncio.sleep(0.05)
        return 10

    assert await asyncio.gather(*(compute() for _ in range(10))) == [10] * 10
    assert await get_cachify_client().a_get(key='sf-async-enc-cached') == 15
    assert await compute() == 10


def test_sync_concurrent_misses_share_one_call(init_cachify_fixture: None, flights: list[SingleFlight]) -> None:
    calls = 0
    barrier = threading.Barrier(100)

    @cached(key='sf-sync-{x}')
    def compute(x: int) -> int:
        nonlocal calls
        calls += 1
        time.sleep(0.3)
        return x * 2

    def _caller(_: int) -> int:
        _ = barrier.wait()
        return compute(21)

    with ThreadPoolExecutor(max_workers=100) as pool:
        results = list(pool.map(_caller, range(100)))

    assert results == [42] * 100
    assert calls == 1
    assert flights[0]._calls == {}
    assert compute(21) == 42
    assert calls == 1


def test_sync_error_reaches_every_waiter_and_is_not_cached(
    init_cachify_fixture: None, flights: list[SingleFlight]
) -> None:
    calls = 0
    barrier = threading.Barrier(10)

    @cached(key='sf-sync-err')
    def compute() -> int:
        nonlocal calls
        calls += 1
        time.sleep(0.2)
        if calls == 1:
            raise ValueError('boom')
        return 7

    def _caller(_: int) -> int:
        _ = barrier.wait()
        return compute()

    with ThreadPoolExecutor(max_workers=10) as pool:
        errors = [f.exception() for f in [pool.submit(_caller, i) for i in range(10)]]

    assert calls == 1
    assert all(isinstance(e, ValueError) for e in errors)
    assert len({id(e) for e in errors}) == 1
    assert flights[0]._calls == {}
    assert compute() == 7
    assert calls == 2


def test_sync_recursive_call_with_same_key_does_not_wait_for_itself(init_cachify_fixture: None) -> None:
    @cached(key='sf-sync-rec')
    def countdown(n: int) -> int:
        if n == 0:
            return 0
        return countdown(n - 1) + 1

    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(countdown, 3).result(timeout=1) == 3


def test_sync_protection_off_calls_once_per_caller(init_cachify_fixture: None) -> None:
    calls = 0
    calls_lock = threading.Lock()
    barrier = threading.Barrier(5)

    @cached(key='sf-sync-off', stampede_protect=StampedeProtect.OFF)
    def compute() -> int:
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.1)
        return 1

    def _caller(_: int) -> int:
        _ = barrier.wait()
        return compute()

    with ThreadPoolExecutor(max_workers=5) as pool:
        assert list(pool.map(_caller, range(5))) == [1] * 5

    assert calls == 5


def test_sync_leader_returns_value_filled_after_callers_miss(init_cachify_fixture: None, mocker: MockerFixture) -> None:
    _fake_reads(get_cachify_client(), mocker, 'sf-sync-reread-cached', [None, 'stored'])

    @cached(key='sf-sync-reread')
    def compute() -> str:
        pytest.fail('the value was already cached')

    assert compute() == 'stored'


def test_sync_lock_holder_computes_and_releases(init_cachify_fixture: None) -> None:
    calls: list[int] = []

    @cached(key='l2-sync-{x}', stampede_protect=StampedeProtect.LOCK)
    def compute(x: int) -> int:
        calls.append(x)
        return x + 1

    assert compute(1) == 2
    assert compute(1) == 2
    assert calls == [1]
    assert get_cachify_client().get(key='l2-sync-1-cached_lock') is None


def test_sync_lock_waiter_returns_value_without_taking_lock(init_cachify_fixture: None) -> None:
    client = get_cachify_client()
    _hold_lock(client, 'l2-sync-wait-cached_lock')
    threading.Timer(0.2, client.set, kwargs={'key': 'l2-sync-wait-cached', 'val': 14}).start()

    @cached(
        key='l2-sync-wait',
        enc_dec=(lambda v: v + 5, lambda v: v - 5),
        stampede_protect=LockConf(poll_interval=0.02),
    )
    def compute() -> int:
        pytest.fail('another process is computing the value')

    assert compute() == 9
    assert client.get(key='l2-sync-wait-cached_lock') == 'other'


def test_sync_lock_wait_timeout_computes_without_lock(init_cachify_fixture: None) -> None:
    client = get_cachify_client()
    _hold_lock(client, 'l2-sync-timeout-cached_lock')

    @cached(key='l2-sync-timeout', stampede_protect=LockConf(wait=0.2, poll_interval=0.05))
    def compute() -> str:
        return 'fresh'

    started = time.monotonic()
    assert compute() == 'fresh'
    assert 0.2 <= time.monotonic() - started < 2
    assert client.get(key='l2-sync-timeout-cached') == 'fresh'
    assert client.get(key='l2-sync-timeout-cached_lock') == 'other'


def test_sync_lock_waiter_takes_freed_lock_and_computes(init_cachify_fixture: None) -> None:
    client = get_cachify_client()
    _hold_lock(client, 'l2-sync-freed-cached_lock')
    threading.Timer(0.2, client.delete, kwargs={'key': 'l2-sync-freed-cached_lock'}).start()

    @cached(key='l2-sync-freed', stampede_protect=LockConf(wait=None, poll_interval=0.02))
    def compute() -> str:
        return 'mine'

    assert compute() == 'mine'
    assert client.get(key='l2-sync-freed-cached_lock') is None


def test_sync_lock_holder_rereads_cache_before_computing(init_cachify_fixture: None, mocker: MockerFixture) -> None:
    client = get_cachify_client()
    _fake_reads(client, mocker, 'l2-sync-reread-cached', [None, None, 'stored'])

    @cached(key='l2-sync-reread', stampede_protect=StampedeProtect.LOCK)
    def compute() -> str:
        pytest.fail('the value was already cached')

    assert compute() == 'stored'
    assert client.get(key='l2-sync-reread-cached_lock') is None


def test_sync_lock_released_when_function_raises(init_cachify_fixture: None) -> None:
    calls = 0

    @cached(key='l2-sync-raise', stampede_protect=StampedeProtect.LOCK)
    def compute() -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError('boom')
        return 2

    with pytest.raises(ValueError, match='boom'):
        _ = compute()
    assert get_cachify_client().get(key='l2-sync-raise-cached_lock') is None
    assert compute() == 2


def test_lock_settings_default_to_init_cachify_values(mocker: MockerFixture) -> None:
    cachify_instance = init_cachify(default_lock_expiration=7, is_global=False)
    spy_set = mocker.spy(cachify_instance._client._sync_client, 'set')

    @cachify_instance.cached(key='l2-defaults', stampede_protect=StampedeProtect.LOCK)
    def default_exp() -> int:
        return 1

    @cachify_instance.cached(key='l2-explicit', stampede_protect=LockConf(exp=3))
    def explicit_exp() -> int:
        return 1

    _ = default_exp()
    _ = explicit_exp()

    assert [c.kwargs['ex'] for c in spy_set.call_args_list if c.kwargs['nx']] == [7, 3]


def test_release_lock_keeps_lock_held_by_another_token(init_cachify_fixture: None) -> None:
    client = get_cachify_client()
    assert client.try_acquire_lock(key='l2-release', ttl=10, token='a')

    client.release_lock(key='l2-release', token='b')
    assert client.get(key='l2-release') == 'a'

    client.release_lock(key='l2-release', token='a')
    assert client.get(key='l2-release') is None


async def test_async_lock_holder_computes_and_releases(init_cachify_fixture: None) -> None:
    calls: list[int] = []

    @cached(key='l2-async-{x}', stampede_protect=StampedeProtect.LOCK)
    async def compute(x: int) -> int:
        calls.append(x)
        return x + 1

    assert await compute(1) == 2
    assert await compute(1) == 2
    assert calls == [1]
    assert await get_cachify_client().a_get(key='l2-async-1-cached_lock') is None


async def test_async_lock_waiter_returns_value_without_taking_lock(init_cachify_fixture: None) -> None:
    client = get_cachify_client()
    _hold_lock(client, 'l2-async-wait-cached_lock')

    async def _other_process_fills() -> None:
        await asyncio.sleep(0.2)
        await client.a_set(key='l2-async-wait-cached', val=14)

    filler = asyncio.create_task(_other_process_fills())

    @cached(
        key='l2-async-wait',
        enc_dec=(lambda v: v + 5, lambda v: v - 5),
        stampede_protect=LockConf(poll_interval=0.02),
    )
    async def compute() -> int:
        pytest.fail('another process is computing the value')

    assert await compute() == 9
    await filler
    assert await client.a_get(key='l2-async-wait-cached_lock') == 'other'


async def test_async_lock_wait_timeout_computes_without_lock(init_cachify_fixture: None) -> None:
    client = get_cachify_client()
    _hold_lock(client, 'l2-async-timeout-cached_lock')

    @cached(key='l2-async-timeout', stampede_protect=LockConf(wait=0.2, poll_interval=0.05))
    async def compute() -> str:
        return 'fresh'

    started = time.monotonic()
    assert await compute() == 'fresh'
    assert 0.2 <= time.monotonic() - started < 2
    assert await client.a_get(key='l2-async-timeout-cached') == 'fresh'
    assert await client.a_get(key='l2-async-timeout-cached_lock') == 'other'


async def test_async_lock_waiter_takes_freed_lock_and_computes(init_cachify_fixture: None) -> None:
    client = get_cachify_client()
    _hold_lock(client, 'l2-async-freed-cached_lock')

    async def _other_process_releases() -> None:
        await asyncio.sleep(0.2)
        await client.a_delete(key='l2-async-freed-cached_lock')

    releaser = asyncio.create_task(_other_process_releases())

    @cached(key='l2-async-freed', stampede_protect=LockConf(wait=None, poll_interval=0.02))
    async def compute() -> str:
        return 'mine'

    assert await compute() == 'mine'
    await releaser
    assert await client.a_get(key='l2-async-freed-cached_lock') is None


async def test_async_lock_holder_rereads_cache_before_computing(
    init_cachify_fixture: None, mocker: MockerFixture
) -> None:
    client = get_cachify_client()
    _afake_reads(client, mocker, 'l2-async-reread-cached', [None, None, 'stored'])

    @cached(key='l2-async-reread', stampede_protect=StampedeProtect.LOCK)
    async def compute() -> str:
        pytest.fail('the value was already cached')

    assert await compute() == 'stored'
    assert await client.a_get(key='l2-async-reread-cached_lock') is None


async def test_async_lock_released_when_function_raises(init_cachify_fixture: None) -> None:
    calls = 0

    @cached(key='l2-async-raise', stampede_protect=StampedeProtect.LOCK)
    async def compute() -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError('boom')
        return 2

    with pytest.raises(ValueError, match='boom'):
        _ = await compute()
    assert await get_cachify_client().a_get(key='l2-async-raise-cached_lock') is None
    assert await compute() == 2


async def test_async_release_lock_keeps_lock_held_by_another_token(init_cachify_fixture: None) -> None:
    client = get_cachify_client()
    assert await client.a_try_acquire_lock(key='l2-arelease', ttl=10, token='a')

    await client.a_release_lock(key='l2-arelease', token='b')
    assert await client.a_get(key='l2-arelease') == 'a'

    await client.a_release_lock(key='l2-arelease', token='a')
    assert await client.a_get(key='l2-arelease') is None
