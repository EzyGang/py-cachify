# pyright: reportPrivateUsage=false
import time
from types import SimpleNamespace
from typing import Any

import pytest
from pytest_mock import MockerFixture

import py_cachify._backend._lib
from py_cachify import CachifyInitError
from py_cachify._backend._clients import AsyncWrapper, MemoryCache
from py_cachify._backend._lib import Cachify, CachifyClient, get_cachify_client, init_cachify
from py_cachify._backend._types._common import UNSET


@pytest.fixture
def memory_cache() -> MemoryCache:
    return MemoryCache()


@pytest.fixture
def async_wrapper(memory_cache: MemoryCache) -> AsyncWrapper:
    return AsyncWrapper(memory_cache)


@pytest.fixture
def cachify(memory_cache: MemoryCache, async_wrapper: AsyncWrapper) -> CachifyClient:
    return CachifyClient(
        sync_client=memory_cache,
        async_client=async_wrapper,
        default_expiration=30,
        default_cache_ttl=None,
        prefix='_PYC_',
    )


@pytest.fixture
def cachify_instance(memory_cache: MemoryCache, async_wrapper: AsyncWrapper) -> Cachify:
    return Cachify(
        sync_client=memory_cache,
        async_client=async_wrapper,
        prefix='_PYC_',
        default_expiration=30,
        default_cache_ttl=None,
    )


def test_memory_cache_set_and_get(memory_cache: MemoryCache) -> None:
    memory_cache.set('key', 'value', ex=10)
    assert memory_cache.get('key') == 'value'


def test_memory_cache_set_and_get_with_expiry(memory_cache: MemoryCache) -> None:
    memory_cache.set('key', 'value', ex=-1)
    assert memory_cache.get('key') is None


def test_memory_cache_get_with_default(memory_cache: MemoryCache) -> None:
    assert memory_cache.get('nonexistent_key') is None


def test_memory_cache_delete(memory_cache: MemoryCache) -> None:
    memory_cache.set('key', 'value')
    memory_cache.delete('key')
    assert memory_cache.get('key') is None


@pytest.mark.asyncio
async def test_async_wrapper_get(async_wrapper: AsyncWrapper, mocker: MockerFixture) -> None:
    mocker.patch.object(time, 'time', return_value=0)
    async_wrapper._cache.set('key', 'value', ex=10)

    result = await async_wrapper.get('key')
    assert result == 'value'


@pytest.mark.asyncio
async def test_async_wrapper_get_with_default(async_wrapper: AsyncWrapper, mocker: MockerFixture) -> None:
    mocker.patch.object(time, 'time', return_value=0)
    result = await async_wrapper.get('nonexistent_key')
    assert result is None


@pytest.mark.asyncio
async def test_async_wrapper_delete(async_wrapper: AsyncWrapper, mocker: MockerFixture) -> None:
    mocker.patch.object(time, 'time', return_value=0)
    async_wrapper._cache.set('key', 'value')

    await async_wrapper.delete('key', 'nonexistent_key')
    assert async_wrapper._cache.get('key') is None


@pytest.mark.asyncio
async def test_async_wrapper_set(async_wrapper: AsyncWrapper, mocker: MockerFixture) -> None:
    mocker.patch.object(time, 'time', return_value=0)
    await async_wrapper.set('key', 'value', ex=10)
    assert async_wrapper._cache.get('key') == 'value'


def test_cachify_set_and_get(cachify: CachifyClient) -> None:
    cachify.set('key', 'value', ttl=10)
    assert cachify.get('key') == 'value'


def test_cachify_set_and_get_with_ttl(cachify: CachifyClient) -> None:
    cachify.set('key', 'value', ttl=-1)
    assert cachify.get('key') is None


def test_cachify_get_with_nonexistent_key(cachify: CachifyClient) -> None:
    assert cachify.get('nonexistent_key') is None


def test_cachify_get(cachify: CachifyClient) -> None:
    cachify.set('key', 'value')
    result = cachify.get('key')
    assert result == 'value'


def test_cachify_delete(cachify: CachifyClient) -> None:
    cachify.set('key', 'value')
    cachify.delete('key')
    assert cachify.get('key') is None


def test_cachify_try_acquire_lock_acquires_when_free(cachify_instance: Cachify) -> None:
    acquired = cachify_instance._client.try_acquire_lock('lock-key', ttl=30)
    assert acquired is True
    # underlying cache should now have the lock set
    assert cachify_instance._client._sync_client.get(f'{cachify_instance._client._prefix}lock-key') is not None


def test_cachify_try_acquire_lock_fails_when_held(cachify_instance: Cachify) -> None:
    client = cachify_instance._client
    # first acquire
    assert client.try_acquire_lock('lock-key', ttl=30) is True
    # second attempt should fail because nx=True semantics
    assert client.try_acquire_lock('lock-key', ttl=30) is False


@pytest.mark.asyncio
async def test_cachify_a_try_acquire_lock_acquires_when_free(cachify_instance: Cachify) -> None:
    acquired = await cachify_instance._client.a_try_acquire_lock('lock-key', ttl=30)
    assert acquired is True
    # underlying async cache (AsyncWrapper over MemoryCache) should now have the lock set
    assert await cachify_instance._client._async_client.get(f'{cachify_instance._client._prefix}lock-key') is not None


@pytest.mark.asyncio
async def test_cachify_a_try_acquire_lock_fails_when_held(cachify_instance: Cachify) -> None:
    client = cachify_instance._client
    # first acquire
    assert await client.a_try_acquire_lock('lock-key', ttl=30) is True
    # second attempt should fail because nx=True semantics
    assert await client.a_try_acquire_lock('lock-key', ttl=30) is False


@pytest.mark.asyncio
async def test_cachify_a_get(cachify: CachifyClient) -> None:
    cachify.set('key', 'value')
    result = await cachify.a_get('key')
    assert result == 'value'


@pytest.mark.asyncio
async def test_cachify_a_get_with_nonexistent_key(cachify: CachifyClient) -> None:
    result = await cachify.a_get('nonexistent_key')
    assert result is None


@pytest.mark.asyncio
async def test_cachify_a_delete(cachify: CachifyClient) -> None:
    cachify.set('key', 'value')
    await cachify.a_delete('key')
    assert cachify.get('key') is None


@pytest.mark.asyncio
async def test_cachify_a_set(cachify: CachifyClient) -> None:
    await cachify.a_set('key', 'value')
    assert cachify.get('key') == 'value'


def test_init_cachify(init_cachify_fixture: None) -> None:
    assert py_cachify._backend._lib._cachify is not None


def test_get_cachify_raises_error() -> None:
    with pytest.raises(CachifyInitError, match='Cachify is not initialized, did you forget to call `init_cachify`?'):
        get_cachify_client()


def test_get_cachify_client_returns_global_value(init_cachify_fixture: None) -> None:
    _client = get_cachify_client()

    assert isinstance(_client, CachifyClient)


def test_cachify_cached_delegates_to__cached_impl(cachify_instance: Cachify, mocker: MockerFixture) -> None:
    dummy_cached = SimpleNamespace()
    mocked_impl = mocker.patch(
        'py_cachify._backend._cached._cached_impl',
        return_value=dummy_cached,
    )

    result = cachify_instance.cached(
        key='k-{x}',
        ttl=123,
        enc_dec=('enc', 'dec'),  # pyright: ignore[reportArgumentType]
    )

    assert result is dummy_cached

    call = mocked_impl.call_args
    assert call.kwargs['key'] == 'k-{x}'
    assert call.kwargs['ttl'] == 123
    assert call.kwargs['enc_dec'] == ('enc', 'dec')

    client_provider = call.kwargs['client_provider']
    client = client_provider()
    assert client is cachify_instance._client


def test_cachify_lock_delegates_and_injects_client(cachify_instance: Cachify, mocker: MockerFixture) -> None:
    dummy_lock = SimpleNamespace()
    mocked_lock = mocker.patch(
        'py_cachify._backend._lock.lock',
        return_value=dummy_lock,
    )

    lk = cachify_instance.lock(
        key='lk-{y}',
        nowait=False,
        timeout=1.5,
        exp=999,
    )

    assert lk is dummy_lock

    call = mocked_lock.call_args
    assert call.kwargs['key'] == 'lk-{y}'
    assert call.kwargs['nowait'] is False
    assert call.kwargs['timeout'] == 1.5
    assert call.kwargs['exp'] == 999

    assert hasattr(lk, '_cachify')
    assert lk._cachify is cachify_instance._client

    # ensure default values also propagate correctly
    cachify_instance.lock(key='foo')
    _, kwargs_default = mocked_lock.call_args
    assert kwargs_default['key'] == 'foo'
    assert kwargs_default['nowait'] is True
    assert kwargs_default['timeout'] is None
    assert kwargs_default['exp'] is UNSET


def test_cachify_once_delegates_to__once_impl(cachify_instance: Cachify, mocker: MockerFixture) -> None:
    dummy_once = SimpleNamespace()
    mocked_once_impl = mocker.patch(
        'py_cachify._backend._lock._once_impl',
        return_value=dummy_once,
    )

    result = cachify_instance.once(
        key='once-{z}',
        raise_on_locked=True,
        return_on_locked=42,
    )

    assert result is dummy_once

    call = mocked_once_impl.call_args
    assert call.kwargs['key'] == 'once-{z}'
    assert call.kwargs['raise_on_locked'] is True
    assert call.kwargs['return_on_locked'] == 42

    client_provider = call.kwargs['client_provider']
    client = client_provider()
    assert client is cachify_instance._client

    # defaults path
    cachify_instance.once(key='foo')
    _, kwargs_default = mocked_once_impl.call_args
    assert kwargs_default['key'] == 'foo'
    assert kwargs_default['raise_on_locked'] is False
    assert kwargs_default['return_on_locked'] is None


def test_cachify_internal_client_is_wired_correctly(
    cachify_instance: Cachify, memory_cache: MemoryCache, async_wrapper: AsyncWrapper
) -> None:
    client = cachify_instance._client
    assert client._sync_client is memory_cache
    assert client._async_client is async_wrapper
    assert client._prefix == '_PYC_'
    assert client.default_expiration == 30
    assert client.default_cache_ttl is None


def test_init_cachify_defaults_to_memory_cache_and_asyncwrapper(mocker: MockerFixture) -> None:
    # ensure we start from a clean global
    py_cachify._backend._lib._cachify = None  # type: ignore[attr-defined]

    cachify_instance = init_cachify(sync_client=None, async_client=None, is_global=True)

    # sync client should be MemoryCache
    assert isinstance(cachify_instance._client._sync_client, MemoryCache)

    # async client should be AsyncWrapper and wrap the same MemoryCache instance
    assert isinstance(cachify_instance._client._async_client, AsyncWrapper)
    assert cachify_instance._client._async_client._cache is cachify_instance._client._sync_client


def test_init_cachify_reuses_provided_memory_cache_for_asyncwrapper(mocker: MockerFixture) -> None:
    py_cachify._backend._lib._cachify = None

    sync_client = MemoryCache()
    cachify_instance = init_cachify(sync_client=sync_client, async_client=None, is_global=True)

    # async wrapper should reuse the provided sync_client as its underlying cache
    assert isinstance(cachify_instance._client._async_client, AsyncWrapper)
    assert cachify_instance._client._async_client._cache is sync_client


def test_init_cachify_is_global_flag_controls_global_registration() -> None:
    py_cachify._backend._lib._cachify = None
    cachify_instance = init_cachify(sync_client=None, async_client=None, is_global=False)
    assert cachify_instance is not None
    assert py_cachify._backend._lib._cachify is None

    # when is_global is True, global client should be set
    init_cachify(sync_client=None, async_client=None, is_global=True)
    global_client = get_cachify_client()

    assert isinstance(global_client, CachifyClient)
    assert global_client is not cachify_instance
    assert isinstance(global_client._async_client, AsyncWrapper)


def test_init_cachify_uses_provided_async_client_unchanged() -> None:
    py_cachify._backend._lib._cachify = None

    sync_client = MemoryCache()
    explicit_async = AsyncWrapper(cache=sync_client)

    cachify_instance = init_cachify(
        sync_client=sync_client,
        async_client=explicit_async,
        is_global=False,
    )
    assert cachify_instance._client._sync_client is sync_client

    assert cachify_instance._client._async_client is explicit_async


def test_init_cachify_creates_new_memory_cache_when_sync_not_memorycache(mocker: MockerFixture) -> None:
    py_cachify._backend._lib._cachify = None

    class DummySyncClient:
        def __init__(self) -> None:
            self.set_calls: list[tuple[Any, Any, Any]] = []
            self.get_calls: list[tuple[Any, Any]] = []
            self.delete_calls: list[tuple[Any, ...]] = []

        def set(self, name: Any, value: Any, ex: Any = None, nx: Any = False) -> None:
            self.set_calls.append((name, value, ex))

        def get(self, name: Any, default: Any = None) -> Any:
            self.get_calls.append((name, default))
            return default

        def delete(self, *names: Any) -> None:
            self.delete_calls.append(names)

    sync_client = DummySyncClient()
    cachify_instance = init_cachify(sync_client=sync_client, async_client=None, is_global=False)

    # internal sync client is our dummy
    assert cachify_instance._client._sync_client is sync_client

    # async client must be AsyncWrapper with a fresh MemoryCache, not the dummy
    async_client = cachify_instance._client._async_client
    assert isinstance(async_client, AsyncWrapper)
    assert async_client._cache is not sync_client
    assert isinstance(async_client._cache, MemoryCache)
