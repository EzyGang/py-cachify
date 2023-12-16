import sys

import pytest
from pytest_mock import MockerFixture

from py_cachify.backend.exceptions import CachifyInitError
from py_cachify.cached import cached


def sync_function(arg1, arg2):
    return arg1 + arg2


async def async_function(arg1, arg2):
    return arg1 + arg2


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


def test_cached_decorator_check_cachify_init():
    sync_function_wrapped = cached(key='test_key')(sync_function)
    with pytest.raises(CachifyInitError, match='Cachify is not initialized, did you forget to call `init_cachify`?'):
        sync_function_wrapped(3, 4)

