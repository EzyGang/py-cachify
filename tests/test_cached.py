import asyncio
import sys

import pytest
from pytest_mock import MockerFixture

from py_cachify import CachifyInitError, cached
from py_cachify._backend._cached import async_cached, sync_cached


def sync_function(arg1: int, arg2: int) -> int:
    return arg1 + arg2


async def async_function(arg1: int, arg2: int) -> int:
    return arg1 + arg2


def decoder(val: int) -> int:
    return val - 5


def encoder(val: int) -> int:
    return val + 5


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


def test_async_cached_returns_cached():
    assert async_cached(key='test').__qualname__.split('.')[-1] == '_cached_inner'


def test_sync_cached_returns_cached():
    assert sync_cached(key='test').__qualname__.split('.')[-1] == '_cached_inner'
