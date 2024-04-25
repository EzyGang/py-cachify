import time

import pytest
from pytest_mock import MockerFixture

import py_cachify.backend.lib
from py_cachify.backend.clients import AsyncWrapper, MemoryCache
from py_cachify.backend.exceptions import CachifyInitError
from py_cachify.backend.lib import Cachify, get_cachify


@pytest.fixture
def memory_cache():
    return MemoryCache()


@pytest.fixture
def async_wrapper(memory_cache):
    return AsyncWrapper(memory_cache)


@pytest.fixture
def cachify(memory_cache, async_wrapper):
    return Cachify(sync_client=memory_cache, async_client=async_wrapper, prefix='_PYC_')


def test_memory_cache_set_and_get(memory_cache):
    memory_cache.set('key', 'value', ex=10)
    assert memory_cache.get('key') == 'value'


def test_memory_cache_set_and_get_with_expiry(memory_cache):
    memory_cache.set('key', 'value', ex=-1)
    assert memory_cache.get('key') is None


def test_memory_cache_get_with_default(memory_cache):
    assert memory_cache.get('nonexistent_key') is None


def test_memory_cache_delete(memory_cache):
    memory_cache.set('key', 'value')
    memory_cache.delete('key')
    assert memory_cache.get('key') is None


@pytest.mark.asyncio
async def test_async_wrapper_get(async_wrapper, mocker: MockerFixture):
    mocker.patch.object(time, 'time', return_value=0)
    async_wrapper._cache.set('key', 'value', ex=10)

    result = await async_wrapper.get('key')
    assert result == 'value'


@pytest.mark.asyncio
async def test_async_wrapper_get_with_default(async_wrapper, mocker: MockerFixture):
    mocker.patch.object(time, 'time', return_value=0)
    result = await async_wrapper.get('nonexistent_key')
    assert result is None


@pytest.mark.asyncio
async def test_async_wrapper_delete(async_wrapper, mocker: MockerFixture):
    mocker.patch.object(time, 'time', return_value=0)
    async_wrapper._cache.set('key', 'value')

    await async_wrapper.delete('key', 'nonexistent_key')
    assert async_wrapper._cache.get('key') is None


@pytest.mark.asyncio
async def test_async_wrapper_set(async_wrapper, mocker: MockerFixture):
    mocker.patch.object(time, 'time', return_value=0)
    await async_wrapper.set('key', 'value', ex=10)
    assert async_wrapper._cache.get('key') == 'value'


def test_cachify_set_and_get(cachify):
    cachify.set('key', 'value', ttl=10)
    assert cachify.get('key') == 'value'


def test_cachify_set_and_get_with_ttl(cachify):
    cachify.set('key', 'value', ttl=-1)
    assert cachify.get('key') is None


def test_cachify_get_with_nonexistent_key(cachify):
    assert cachify.get('nonexistent_key') is None


def test_cachify_get(cachify):
    cachify.set('key', 'value')
    result = cachify.get('key')
    assert result == 'value'


def test_cachify_delete(cachify):
    cachify.set('key', 'value')
    cachify.delete('key')
    assert cachify.get('key') is None


@pytest.mark.asyncio
async def test_cachify_a_get(cachify):
    cachify.set('key', 'value')
    result = await cachify.a_get('key')
    assert result == 'value'


@pytest.mark.asyncio
async def test_cachify_a_get_with_nonexistent_key(cachify):
    result = await cachify.a_get('nonexistent_key')
    assert result is None


@pytest.mark.asyncio
async def test_cachify_a_delete(cachify):
    cachify.set('key', 'value')
    await cachify.a_delete('key')
    assert cachify.get('key') is None


@pytest.mark.asyncio
async def test_cachify_a_set(cachify):
    await cachify.a_set('key', 'value')
    assert cachify.get('key') == 'value'


def test_init_cachify(init_cachify_fixture):
    assert py_cachify.backend.lib._cachify is not None


def test_get_cachify_raises_error():
    with pytest.raises(CachifyInitError, match='Cachify is not initialized, did you forget to call `init_cachify`?'):
        get_cachify()
