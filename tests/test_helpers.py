import inspect

import pytest
from pytest_mock import MockerFixture

from py_cachify.backend.helpers import a_reset, get_full_key_from_signature, reset


def method_with_args_kwargs_args(*args, **kwargs) -> None:
    pass


@pytest.fixture
def args_kwargs_signature():
    return inspect.signature(method_with_args_kwargs_args)


def test_get_full_key_valid_arguments(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind('value1', 'value2', arg3='value3')
    result = get_full_key_from_signature(bound_args, 'key_{}_{}_{arg3}')
    assert result == 'key_value1_value2_value3'


def test_get_full_key_invalid_key_format(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind('value1', 'value2')
    with pytest.raises(ValueError, match='Arguments in a key do not match function signature'):
        get_full_key_from_signature(bound_args, 'key_{}_{}_{}')


def test_get_full_key_empty_key_and_arguments(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind()
    result = get_full_key_from_signature(bound_args, 'key_with_no_args')
    assert result == 'key_with_no_args'


def test_get_full_key_mixed_placeholders(args_kwargs_signature):
    bound_args = args_kwargs_signature.bind('value1', 'value2', arg3='value3')
    with pytest.raises(ValueError, match='Arguments in a key do not match function signature'):
        get_full_key_from_signature(bound_args, 'key_{}_{}_{}_{invalid_arg}')


def test_reset_calls_delete_with_key(init_cachify_fixture, args_kwargs_signature, mocker: MockerFixture):
    mock = mocker.patch('py_cachify.backend.lib.Cachify.delete')

    reset('val1', 'val2', arg3='val3', key='key_{}_{}_{arg3}', signature=args_kwargs_signature)

    mock.assert_called_once_with(key='key_val1_val2_val3')


@pytest.mark.asyncio
async def test_a_reset_calls_delete_with_key(init_cachify_fixture, args_kwargs_signature, mocker: MockerFixture):
    mock = mocker.patch('py_cachify.backend.lib.Cachify.a_delete')

    await a_reset('val1', 'val2', arg3='val3', key='key_{}_{}_{arg3}', signature=args_kwargs_signature)

    mock.assert_called_once_with(key='key_val1_val2_val3')
