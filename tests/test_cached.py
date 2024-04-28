import sys

import pytest
from pytest_mock import MockerFixture

from py_cachify import cached
from py_cachify.backend.cached import async_cached, sync_cached
from py_cachify.backend.exceptions import CachifyInitError


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
        sync_function_wrapped(3, 4)


def test_sync_cached_preserves_type_annotations(init_cachify_fixture):
    func = sync_cached(key='test_key_{arg1}')(async_function)
    for name, clz in [('arg1', int), ('arg2', int), ('return', int)]:
        assert func.__annotations__[name] == clz


def test_async_cached_preserves_type_annotations(init_cachify_fixture):
    func = async_cached(key='test_key_{arg1}')(async_function)
    for name, clz in [('arg1', int), ('arg2', int), ('return', int)]:
        assert func.__annotations__[name] == clz
