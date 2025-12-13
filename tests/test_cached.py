import asyncio
import sys

import pytest
from pytest_mock import MockerFixture

from py_cachify import CachifyInitError, cached, init_cachify
from py_cachify._backend._lib import Cachify
from py_cachify._backend._types._common import UNSET


def sync_function(arg1: int, arg2: int) -> int:
    return arg1 + arg2


async def async_function(arg1: int, arg2: int) -> int:
    return arg1 + arg2


def decoder(val: int) -> int:
    return val - 5


def encoder(val: int) -> int:
    return val + 5


def _get_internal_client(cachify_instance: Cachify):
    # helper to access the bound internal client in tests
    return cachify_instance._client


def test_cached_decorator_sync_function(init_cachify_fixture, mocker: MockerFixture):
    spy = mocker.spy(sys.modules[__name__], 'sync_function')
    sync_function_wrapped = cached(key='test_key')(sync_function)

    result = sync_function_wrapped(3, 4)
    result_2 = sync_function_wrapped(3, 4)

    assert result == 7
    assert result_2 == 7
    spy.assert_called_once()


@pytest.mark.asyncio
async def test_cached_decorator_async_function(init_cachify_fixture, mocker: MockerFixture):
    spy = mocker.spy(sys.modules[__name__], 'async_function')
    async_function_wrapped = cached(key='test_key_{arg1}')(async_function)
    result = await async_function_wrapped(3, 4)
    result_2 = await async_function_wrapped(3, 4)

    assert result == 7
    assert result_2 == 7
    spy.assert_called_once()


@pytest.mark.asyncio
async def test_cached_decorator_with_encoder_and_decoder(init_cachify_fixture, mocker: MockerFixture):
    decoder_spy = mocker.spy(sys.modules[__name__], 'decoder')
    encoder_spy = mocker.spy(sys.modules[__name__], 'encoder')
    async_function_wrapped = cached(key='test_key_enc_dec_{arg1}', enc_dec=(encoder, decoder))(async_function)
    result = await async_function_wrapped(3, 4)
    result_2 = await async_function_wrapped(3, 4)

    assert result == 7
    assert result_2 == 7
    encoder_spy.assert_called_once_with(7)
    decoder_spy.assert_called_once_with(12)


def test_cached_decorator_check_cachify_init():
    sync_function_wrapped = cached(key='test_key')(sync_function)
    with pytest.raises(CachifyInitError, match='Cachify is not initialized, did you forget to call `init_cachify`?'):
        _ = sync_function_wrapped(3, 4)


def test_sync_cached_preserves_type_annotations(init_cachify_fixture):
    func = cached(key='test_sync_key_{arg1}')(sync_function)
    for name, clz in [('arg1', int), ('arg2', int), ('return', int)]:
        assert func.__annotations__[name] == clz


def test_async_cached_preserves_type_annotations(init_cachify_fixture):
    func = cached(key='test_key_{arg1}')(async_function)
    for name, clz in [('arg1', int), ('arg2', int), ('return', int)]:
        assert func.__annotations__[name] == clz


def test_cached_wrapped_async_function_has_reset_callable_attached(init_cachify_fixture):
    func = cached(key='test_key_{arg1}')(async_function)

    assert hasattr(func, 'reset')
    assert asyncio.iscoroutinefunction(func.reset)


def test_cached_wrapped_function_has_reset_callable_attached(init_cachify_fixture):
    func = cached(key='teset')(sync_function)

    assert hasattr(func, 'reset')
    assert not asyncio.iscoroutinefunction(func.reset)
    assert callable(func.reset)


def test_cached_works_on_methods(init_cachify_fixture):
    class TestClass:
        t: str = 'test'

        @cached(key='method-{self.t}')
        def method(self, a: int, b: int) -> int:
            return a + b

        @staticmethod
        @cached(key='method-static')
        def method_static(a: int, b: int) -> int:
            return a + b

        @classmethod
        @cached(key='method-class')
        def method_class(cls, a: int, b: int) -> int:
            return a + b

    tc = TestClass()
    assert tc.method(1, 2) == 3
    assert tc.method.reset(tc, 1, 2) is None
    # Fix the type annotation to support
    assert tc.method_static(1, 2) == 3
    assert tc.method_static.reset(1, 2) is None
    # Fix the type annotation to support
    assert tc.method_class(1, 2) == 3
    assert tc.method_class.reset(tc.__class__, 1, 2) is None


@pytest.mark.asyncio
async def test_cached_works_on_async_methods(init_cachify_fixture):
    class TestClass:
        t: str = 'test'

        @cached(key='method-{self.t}')
        async def method(self, a: int, b: int) -> int:
            return a + b

        @staticmethod
        @cached(key='method-static')
        async def method_static(a: int, b: int) -> int:
            return a + b

        @classmethod
        @cached(key='method-class')
        async def method_class(cls, a: int, b: int) -> int:
            return a + b

    tc = TestClass()

    assert await tc.method(1, 2) == 3
    assert await tc.method.reset(tc, 1, 2) is None
    # Fix the type annotation to support
    assert await tc.method_static(1, 2) == 3
    assert await tc.method_static.reset(1, 2) is None
    # Fix the type annotation to support
    assert await tc.method_class(1, 2) == 3
    assert await tc.method_class.reset(tc.__class__, 1, 2) is None


def test_cached_uses_global_and_local_clients_sync(init_cachify_fixture, mocker: MockerFixture):
    spy = mocker.spy(sys.modules[__name__], 'sync_function')

    global_wrapped = cached(key='multi_client_{arg1}_{arg2}')(sync_function)

    local_cachify = init_cachify(prefix='LOCAL-', is_global=False)
    local_wrapped = local_cachify.cached(key='multi_client_{arg1}_{arg2}')(sync_function)

    assert global_wrapped(10, 11) == 21
    assert global_wrapped(10, 11) == 21  # hit global cache

    assert local_wrapped(10, 12) == 22
    assert local_wrapped(10, 12) == 22  # hit local cache

    # One call per client (global + local) with caching working independently
    assert spy.call_count == 2


@pytest.mark.asyncio
async def test_cached_uses_global_and_local_clients_async(init_cachify_fixture, mocker: MockerFixture):
    spy = mocker.spy(sys.modules[__name__], 'async_function')

    global_wrapped = cached(key='multi_client_async_{arg1}_{arg2}')(async_function)

    local_cachify = init_cachify(prefix='LOCAL-ASYNC-', is_global=False)
    local_wrapped = local_cachify.cached(key='multi_client_async_{arg1}_{arg2}')(async_function)

    assert await global_wrapped(10, 11) == 21
    assert await global_wrapped(10, 11) == 21  # hit global cache

    assert await local_wrapped(10, 12) == 22
    assert await local_wrapped(10, 12) == 22  # hit local cache

    # One call per client (global + local) with caching working independently
    assert spy.call_count == 2


def test_local_cachify_wraps_global_cached_sync(init_cachify_fixture, mocker: MockerFixture):
    spy = mocker.spy(sys.modules[__name__], 'sync_function')

    global_wrapped = cached(key='multi_layer_global_{arg1}_{arg2}')(sync_function)
    local_cachify = init_cachify(prefix='LOCAL-MULTI-', is_global=False)
    local_wrapped = local_cachify.cached(key='multi_layer_local_{arg1}_{arg2}')(global_wrapped)

    # First round: local wrapper should compute once and populate both inner (global) and outer (local) caches
    assert local_wrapped(5, 6) == 11
    assert global_wrapped(5, 6) == 11
    assert spy.call_count == 1  # no additional calls

    # Reset via the local wrapper; this should clear both caches for these args
    assert local_wrapped.reset(5, 6) is None

    # After reset, calling through local wrapper should recompute and repopulate both caches
    assert local_wrapped(5, 6) == 11
    assert spy.call_count == 2

    # Global wrapper should again hit its cache
    assert global_wrapped(5, 6) == 11
    assert spy.call_count == 2


@pytest.mark.asyncio
async def test_local_cachify_wraps_global_cached_async(init_cachify_fixture, mocker: MockerFixture):
    spy = mocker.spy(sys.modules[__name__], 'async_function')

    global_wrapped = cached(key='multi_layer_async_{arg1}_{arg2}')(async_function)
    local_cachify = init_cachify(prefix='LOCAL-MULTI-ASYNC-', is_global=False)
    local_wrapped = local_cachify.cached(key='multi_layer_async_{arg1}_{arg2}')(global_wrapped)

    assert await local_wrapped(5, 6) == 11
    assert await global_wrapped(5, 6) == 11
    assert spy.call_count == 1  # no additional calls

    # Reset via the local wrapper; this should clear both caches for these args
    assert await local_wrapped.reset(5, 6) is None

    # After reset, calling through local wrapper should recompute and repopulate both caches
    assert await local_wrapped(5, 6) == 11
    assert spy.call_count == 2

    # Global wrapper should again hit its cache
    assert await global_wrapped(5, 6) == 11
    assert spy.call_count == 2


def test_cached_default_ttl_uses_global_default_cache_ttl(mocker: MockerFixture):
    # global default_cache_ttl=60, ttl left as UNSET on decorator
    cachify_instance = init_cachify(default_cache_ttl=60, is_global=True)
    client = _get_internal_client(cachify_instance)

    spy_set = mocker.spy(client._sync_client, 'set')  # type: ignore[attr-defined]

    wrapped = cached(key='ttl_default_{arg1}_{arg2}')(sync_function)
    assert wrapped(1, 2) == 3

    assert spy_set.call_count == 1
    _, kwargs = spy_set.call_args
    assert kwargs['ex'] == 60


def test_cached_ttl_none_overrides_default_cache_ttl(mocker: MockerFixture):
    # default_cache_ttl=60 but ttl=None should result in ex=None (infinite)
    cachify_instance = init_cachify(default_cache_ttl=60, is_global=True)
    client = _get_internal_client(cachify_instance)

    spy_set = mocker.spy(client._sync_client, 'set')  # type: ignore[attr-defined]

    wrapped = cached(key='ttl_none_{arg1}_{arg2}', ttl=None)(sync_function)
    assert wrapped(2, 3) == 5

    assert spy_set.call_count == 1
    _, kwargs = spy_set.call_args
    assert kwargs['ex'] is None


def test_cached_ttl_explicit_int_overrides_default_cache_ttl(mocker: MockerFixture):
    # default_cache_ttl=60 but explicit ttl=5 wins
    cachify_instance = init_cachify(default_cache_ttl=60, is_global=True)
    client = _get_internal_client(cachify_instance)

    spy_set = mocker.spy(client._sync_client, 'set')  # type: ignore[attr-defined]

    wrapped = cached(key='ttl_int_{arg1}_{arg2}', ttl=5)(sync_function)
    assert wrapped(3, 4) == 7

    assert spy_set.call_count == 1
    _, kwargs = spy_set.call_args
    assert kwargs['ex'] == 5


def test_cached_ttl_unset_with_default_cache_ttl_none_means_infinite(mocker: MockerFixture):
    # default_cache_ttl=None and ttl left as UNSET should lead to ex=None
    cachify_instance = init_cachify(default_cache_ttl=None, is_global=True)
    client = _get_internal_client(cachify_instance)

    spy_set = mocker.spy(client._sync_client, 'set')  # type: ignore[attr-defined]

    wrapped = cached(key='ttl_unset_none_{arg1}_{arg2}')(sync_function)
    assert wrapped(4, 5) == 9

    assert spy_set.call_count == 1
    _, kwargs = spy_set.call_args
    assert kwargs['ex'] is None


def test_cachify_instance_cached_uses_its_own_default_cache_ttl(mocker: MockerFixture):
    global_cachify = init_cachify(default_cache_ttl=10, is_global=True)
    local_cachify = init_cachify(prefix='LOCAL-TTL-', default_cache_ttl=20, is_global=False)

    global_client = _get_internal_client(global_cachify)
    local_client = _get_internal_client(local_cachify)

    spy_global = mocker.spy(global_client._sync_client, 'set')  # type: ignore[attr-defined]
    spy_local = mocker.spy(local_client._sync_client, 'set')  # type: ignore[attr-defined]

    global_wrapped = cached(key='ttl_scope_{arg1}_{arg2}')(sync_function)
    local_wrapped = local_cachify.cached(key='ttl_scope_{arg1}_{arg2}')(sync_function)

    assert global_wrapped(1, 1) == 2
    assert local_wrapped(1, 2) == 3

    _, kwargs_global = spy_global.call_args
    _, kwargs_local = spy_local.call_args

    assert kwargs_global['ex'] == 10
    assert kwargs_local['ex'] == 20


def test_cached_accepts_unset_type_ttl_without_overriding_default(mocker: MockerFixture):
    cachify_instance = init_cachify(default_cache_ttl=33, is_global=True)
    client = _get_internal_client(cachify_instance)

    spy_set = mocker.spy(client._sync_client, 'set')  # type: ignore[attr-defined]

    wrapped = cached(key='ttl_unset_type_{arg1}_{arg2}', ttl=UNSET)(sync_function)
    assert wrapped(6, 7) == 13

    assert spy_set.call_count == 1
    _, kwargs = spy_set.call_args
    assert kwargs['ex'] == 33
